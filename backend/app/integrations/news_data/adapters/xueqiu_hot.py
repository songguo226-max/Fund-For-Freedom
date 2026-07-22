from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.infrastructure.retry import retry_call
from app.integrations.news_data.adapters.article_dates import parse_datetime_value
from app.integrations.news_data.adapters.xueqiu_article import PageFetcher, fetch_xueqiu_article_meta
from app.integrations.news_data.interface import NewsDataError, NewsSourceSpec, RawNewsArticle


class XueqiuHotListProvider:
    def __init__(
        self,
        spec: NewsSourceSpec,
        urls: tuple[str, ...] = (
            "https://api.tcslw.cn/api/hotlist/xueqiu",
            "https://rebang.today/home?tab=xueqiu",
            "https://tophub.today/c/finance",
        ),
        client: httpx.Client | None = None,
        article_page_fetcher: PageFetcher | None = None,
        article_meta_workers: int = 4,
    ) -> None:
        self.spec = spec
        self._urls = urls
        self._client = client or httpx.Client(headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        self._article_page_fetcher = article_page_fetcher
        self._article_meta_workers = max(1, article_meta_workers)

    def fetch_latest(self, *, limit: int = 50) -> list[RawNewsArticle]:
        errors: list[str] = []
        for url in self._urls:
            try:
                text = retry_call(lambda: self._fetch_text(url), retry_on=(httpx.HTTPError, NewsDataError))
                items = self._parse(url, text, limit=limit)
                if items:
                    return items[:limit]
                errors.append(f"{url}: no topic items")
            except NewsDataError as exc:
                errors.append(f"{url}: {exc}")
        raise NewsDataError("雪球话题公开来源均未解析到条目；" + " | ".join(errors))

    def _fetch_text(self, url: str) -> str:
        try:
            response = self._client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            raise NewsDataError(str(exc)) from exc

    def _parse(self, url: str, text: str, *, limit: int | None = None) -> list[RawNewsArticle]:
        if _looks_like_json(text):
            return self._parse_json(url, text, limit=limit)
        return self._parse_html(url, text, limit=limit)

    def _parse_json(self, url: str, text: str, *, limit: int | None = None) -> list[RawNewsArticle]:
        try:
            payload = httpx.Response(200, text=text).json()
        except ValueError as exc:
            raise NewsDataError("invalid xueqiu topic json") from exc

        rows = payload.get("data")
        if not isinstance(rows, list):
            return []

        updated_at = parse_datetime_value(payload.get("update_time") or payload.get("updated_at"))
        subtitle = str(payload.get("subtitle") or "").strip()
        candidates: list[dict[str, Any]] = []
        candidate_limit = limit or len(rows)
        for index, row in enumerate(rows, start=1):
            if len(candidates) >= candidate_limit:
                break
            if not isinstance(row, dict):
                continue
            title = _clean_text(str(row.get("title") or row.get("name") or ""))
            if not title:
                continue
            item_url = _normalize_article_url(str(row.get("url") or "").strip(), base_url=url)
            if not item_url and row.get("id"):
                item_url = f"https://xueqiu.com/s/{row['id']}"
            candidates.append(
                {
                    "rank": index,
                    "row": row,
                    "title": title,
                    "url": item_url or url,
                    "extra": row.get("extra") if isinstance(row.get("extra"), dict) else {},
                }
            )

        article_meta_by_url = self._article_meta_by_url([candidate["url"] for candidate in candidates])
        items: list[RawNewsArticle] = []
        for candidate in candidates:
            article_meta = article_meta_by_url.get(candidate["url"]) or {"published_at": None, "author": None, "title": None}
            published_at = article_meta["published_at"]
            author = article_meta["author"]
            if not published_at or not author:
                continue
            items.append(
                RawNewsArticle(
                    source_id=self.spec.id,
                    title=candidate["title"],
                    url=candidate["url"],
                    summary=_topic_summary(index=candidate["rank"], subtitle=subtitle, extra=candidate["extra"]),
                    published_at=published_at,
                    author=author,
                    raw_payload={
                        "providerUrl": url,
                        "providerName": "雪球话题",
                        "rank": candidate["rank"],
                        "item": candidate["row"],
                        "subtitle": subtitle,
                        "hotlistUpdatedAt": updated_at.isoformat() if updated_at else None,
                        "publishedAt": published_at.isoformat() if published_at else None,
                        "author": author,
                    },
                    tags=("hotlist", "xueqiu"),
                )
            )
        return _dedupe(items)

    def _parse_html(self, url: str, html: str, *, limit: int | None = None) -> list[RawNewsArticle]:
        if "tophub.today" in url:
            tophub_items = self._parse_tophub_xueqiu(url, html, limit=limit)
            if tophub_items:
                return tophub_items

        return []

    def _parse_tophub_xueqiu(self, url: str, html: str, *, limit: int | None = None) -> list[RawNewsArticle]:
        block = _extract_tophub_xueqiu_block(html)
        if not block:
            return []

        candidates: list[dict[str, Any]] = []
        candidate_limit = limit or 50
        for anchor in _TOPHUB_ANCHOR_RE.finditer(block):
            if len(candidates) >= candidate_limit:
                break
            href = unescape(anchor.group("href"))
            body = anchor.group("body")
            rank_match = re.search(r'<span\s+class="s[^"]*">\s*(?P<rank>[1-9]\d?)\s*</span>', body, re.IGNORECASE)
            title_match = re.search(r'<span\s+class="t">\s*(?P<title>.*?)\s*</span>', body, re.IGNORECASE | re.DOTALL)
            if not rank_match or not title_match:
                continue
            title = _clean_text(re.sub(r"<[^>]+>", " ", unescape(title_match.group("title"))))
            if not title:
                continue
            rank = int(rank_match.group("rank"))
            article_url = _normalize_article_url(href, base_url=url)
            candidates.append({"href": href, "rank": rank, "title": title, "url": article_url})

        article_meta_by_url = self._article_meta_by_url([candidate["url"] for candidate in candidates])
        items: list[RawNewsArticle] = []
        for candidate in candidates:
            article_meta = article_meta_by_url.get(candidate["url"]) or {"published_at": None, "author": None, "title": None}
            published_at = article_meta["published_at"]
            author = article_meta["author"]
            if not published_at or not author:
                continue
            items.append(
                RawNewsArticle(
                    source_id=self.spec.id,
                    title=candidate["title"],
                    url=candidate["url"],
                    summary=f"TopHub 财经页雪球今日话题第{candidate['rank']}名。",
                    published_at=published_at,
                    author=author,
                    raw_payload={
                        "providerUrl": url,
                        "providerName": "雪球话题",
                        "rank": candidate["rank"],
                        "title": candidate["title"],
                        "href": candidate["href"],
                        "publishedAt": published_at.isoformat() if published_at else None,
                        "author": author,
                    },
                    tags=("hotlist", "xueqiu", "tophub"),
                )
            )
        return _dedupe(items)

    def _article_meta_by_url(self, urls: list[str]) -> dict[str, dict[str, Any]]:
        unique_urls = list(dict.fromkeys(url for url in urls if url))
        if not unique_urls:
            return {}
        max_workers = min(self._article_meta_workers, len(unique_urls))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            metas = executor.map(self._fetch_article_meta, unique_urls)
        return dict(zip(unique_urls, metas, strict=False))

    def _fetch_article_meta(self, article_url: str) -> dict[str, Any]:
        if not _is_xueqiu_article_url(article_url):
            return {"published_at": None, "author": None, "title": None}
        try:
            meta = fetch_xueqiu_article_meta(article_url, page_fetcher=self._article_page_fetcher)
        except NewsDataError:
            return {"published_at": None, "author": None, "title": None}
        return {"published_at": meta.published_at, "author": meta.author, "title": meta.title}


def build_xueqiu_hot_provider(spec: NewsSourceSpec) -> XueqiuHotListProvider:
    return XueqiuHotListProvider(spec)


def _looks_like_json(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _extract_tophub_xueqiu_block(html: str) -> str:
    start = html.find('id="node-215"')
    if start < 0:
        start = html.find("xueqiu.com.png")
    if start < 0:
        return ""
    end = html.find('<div class="cc-cd" id=', start + 1)
    return html[start:end if end > start else len(html)]


def _normalize_article_url(href: str, *, base_url: str) -> str:
    if not href:
        return ""
    absolute = urljoin(base_url, href)
    if absolute.startswith("http://xueqiu.com/"):
        return "https://" + absolute[len("http://") :]
    return absolute


def _is_xueqiu_article_url(article_url: str) -> bool:
    parsed = urlparse(article_url)
    if parsed.scheme != "https" or parsed.netloc != "xueqiu.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2 and parts[-1].isdigit() and parts[-2].isdigit()


def _topic_summary(*, index: int, subtitle: str, extra: dict[str, Any]) -> str:
    parts = [f"雪球话题第{index}名"]
    percent = _clean_text(str(extra.get("percent") or ""))
    if percent:
        parts.append(f"涨跌幅 {percent}")
    market = _clean_text(str(extra.get("market") or ""))
    exchange = _clean_text(str(extra.get("exchange") or ""))
    if market or exchange:
        parts.append(f"市场 {market or exchange}")
    if subtitle:
        parts.append(subtitle)
    return "；".join(parts) + "。"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _dedupe(items: list[RawNewsArticle]) -> list[RawNewsArticle]:
    seen: set[str] = set()
    result: list[RawNewsArticle] = []
    for item in items:
        key = item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


_TOPHUB_ANCHOR_RE = re.compile(r'<a\s+href="(?P<href>[^"]+)"[^>]*>(?P<body>.*?)</a>', re.IGNORECASE | re.DOTALL)
