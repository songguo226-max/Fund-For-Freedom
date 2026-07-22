from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.infrastructure.retry import retry_call
from app.integrations.news_data.interface import NewsDataError, NewsSourceSpec, RawNewsArticle


REBANG_GELONGHUI_LATEST_LIST_URL = "https://rebang.today/api/latest-list"
REBANG_GELONGHUI_PAGE_URL = "https://rebang.today/fin?tab=gelonghui&sub_tab=hot-day"
TOPHUB_FINANCE_URL = "https://tophub.today/c/finance"


class GelonghuiHotListProvider:
    def __init__(
        self,
        spec: NewsSourceSpec,
        urls: tuple[str, ...] = (REBANG_GELONGHUI_LATEST_LIST_URL, TOPHUB_FINANCE_URL),
        client: httpx.Client | None = None,
    ) -> None:
        self.spec = spec
        self._urls = urls
        self._client = client or httpx.Client(
            headers={
                "Accept": "application/json, text/html;q=0.9",
                "Referer": REBANG_GELONGHUI_PAGE_URL,
                "User-Agent": "Mozilla/5.0",
            },
            timeout=20,
        )

    def fetch_latest(self, *, limit: int = 50) -> list[RawNewsArticle]:
        errors: list[str] = []
        for url in self._urls:
            try:
                text = retry_call(
                    lambda: self._fetch_text(url, limit=limit),
                    retry_on=(httpx.HTTPError, NewsDataError),
                )
                items = self._parse(url, text)
                if items:
                    return items[:limit]
                errors.append(f"{url}: no hotlist items")
            except NewsDataError as exc:
                errors.append(f"{url}: {exc}")
        raise NewsDataError("格隆汇公开热榜均未解析到条目；" + " | ".join(errors))

    def _fetch_text(self, url: str, *, limit: int) -> str:
        params: dict[str, Any] | None = None
        if url == REBANG_GELONGHUI_LATEST_LIST_URL:
            params = {
                "tab": "gelonghui",
                "sub_tab": "hot-day",
                "page": 1,
                "page_size": max(1, min(limit, 100)),
            }
        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            raise NewsDataError(str(exc)) from exc

    def _parse(self, url: str, text: str) -> list[RawNewsArticle]:
        if _looks_like_json(text):
            return self._parse_rebang_json(url, text)
        return self._parse_tophub_html(url, text)

    def _parse_rebang_json(self, url: str, text: str) -> list[RawNewsArticle]:
        try:
            payload = httpx.Response(200, text=text).json()
        except ValueError as exc:
            raise NewsDataError("invalid gelonghui hotlist json") from exc
        if payload.get("code") != 200:
            raise NewsDataError(str(payload.get("msg") or "gelonghui hotlist request failed"))

        data = payload.get("data")
        rows = data.get("list") if isinstance(data, dict) else None
        if isinstance(data, dict) and data.get("is_ranking") is not True:
            raise NewsDataError("gelonghui hot-day ranking payload was not returned")
        if not isinstance(rows, list):
            return []

        items: list[RawNewsArticle] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            title = _clean_text(str(row.get("title") or ""))
            if not title:
                continue
            article_url = _normalize_gelonghui_url(str(row.get("www_url") or row.get("mobile_url") or ""), base_url=url)
            if not _is_gelonghui_article_url(article_url):
                continue
            items.append(
                RawNewsArticle(
                    source_id=self.spec.id,
                    title=title,
                    url=article_url,
                    summary=f"格隆汇热文日排行第{index}名。",
                    published_at=None,
                    author=None,
                    raw_payload={
                        "providerUrl": url,
                        "rank": index,
                        "item": row,
                    },
                    tags=("hotlist", "gelonghui"),
                )
            )
        return _dedupe(items)

    def _parse_tophub_html(self, url: str, html: str) -> list[RawNewsArticle]:
        block = _extract_tophub_gelonghui_block(html)
        if not block:
            return []

        items: list[RawNewsArticle] = []
        for anchor in _TOPHUB_ANCHOR_RE.finditer(block):
            href = unescape(anchor.group("href"))
            body = anchor.group("body")
            rank_match = re.search(r'<span\s+class="s[^"]*">\s*(?P<rank>[1-9]\d?)\s*</span>', body, re.IGNORECASE)
            title_match = re.search(r'<span\s+class="t">\s*(?P<title>.*?)\s*</span>', body, re.IGNORECASE | re.DOTALL)
            if not rank_match or not title_match:
                continue
            title = _clean_text(re.sub(r"<[^>]+>", " ", unescape(title_match.group("title"))))
            article_url = _normalize_gelonghui_url(href, base_url=url)
            if not title or not _is_gelonghui_article_url(article_url):
                continue
            rank = int(rank_match.group("rank"))
            items.append(
                RawNewsArticle(
                    source_id=self.spec.id,
                    title=title,
                    url=article_url,
                    summary=f"TopHub 财经页格隆汇热文日排行第{rank}名。",
                    published_at=None,
                    author=None,
                    raw_payload={
                        "providerUrl": url,
                        "rank": rank,
                        "title": title,
                        "href": href,
                    },
                    tags=("hotlist", "gelonghui", "tophub"),
                )
            )
        return _dedupe(items)


def build_gelonghui_hot_provider(spec: NewsSourceSpec) -> GelonghuiHotListProvider:
    return GelonghuiHotListProvider(spec)


def _looks_like_json(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _extract_tophub_gelonghui_block(html: str) -> str:
    start = html.find('id="node-2424"')
    if start < 0:
        logo = html.find("gelonghui.com.png")
        start = html.rfind('<div class="cc-cd" id=', 0, logo) if logo >= 0 else -1
    if start < 0:
        return ""
    end = html.find('<div class="cc-cd" id=', start + 1)
    return html[start:end if end > start else len(html)]


def _normalize_gelonghui_url(href: str, *, base_url: str) -> str:
    if not href:
        return ""
    absolute = urljoin(base_url, href)
    if absolute.startswith("http://www.gelonghui.com/"):
        return "https://" + absolute[len("http://") :]
    return absolute


def _is_gelonghui_article_url(article_url: str) -> bool:
    parsed = urlparse(article_url)
    if parsed.scheme != "https" or parsed.netloc != "www.gelonghui.com":
        return False
    parts = [part for part in parsed.path.split("/") if part]
    return len(parts) >= 2 and parts[0] == "p" and parts[1].isdigit()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _dedupe(items: list[RawNewsArticle]) -> list[RawNewsArticle]:
    seen: set[str] = set()
    result: list[RawNewsArticle] = []
    for item in items:
        key = item.url or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


_TOPHUB_ANCHOR_RE = re.compile(r'<a\s+href="(?P<href>[^"]+)"[^>]*>(?P<body>.*?)</a>', re.IGNORECASE | re.DOTALL)
