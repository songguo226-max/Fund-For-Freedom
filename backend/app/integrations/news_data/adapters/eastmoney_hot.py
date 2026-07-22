from __future__ import annotations

from typing import Any

import httpx

from app.infrastructure.retry import retry_call
from app.integrations.news_data.adapters.article_dates import parse_datetime_value
from app.integrations.news_data.adapters.eastmoney_article import PageFetcher, fetch_eastmoney_article_meta
from app.integrations.news_data.interface import NewsDataError, NewsSourceSpec, RawNewsArticle


REBANG_EASTMONEY_NODE_ID = "cZoMohzkqp"
REBANG_LATEST_LIST_URL = "https://rebang.today/api/latest-list"


class EastmoneyHotListProvider:
    def __init__(
        self,
        spec: NewsSourceSpec,
        url: str = REBANG_LATEST_LIST_URL,
        node_id: str = REBANG_EASTMONEY_NODE_ID,
        client: httpx.Client | None = None,
        article_page_fetcher: PageFetcher | None = None,
    ) -> None:
        self.spec = spec
        self._url = url
        self._node_id = node_id
        self._article_page_fetcher = article_page_fetcher
        self._client = client or httpx.Client(
            headers={
                "Accept": "application/json",
                "Referer": "https://rebang.today/fin?tab=eastmoney",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=20,
        )

    def fetch_latest(self, *, limit: int = 50) -> list[RawNewsArticle]:
        payload = retry_call(
            lambda: self._fetch_json(limit=limit),
            retry_on=(httpx.HTTPError, NewsDataError),
        )
        items = self._parse(payload)
        if not items:
            raise NewsDataError("东方财富公开热榜未解析到条目")
        return items[:limit]

    def _fetch_json(self, *, limit: int) -> dict[str, Any]:
        try:
            response = self._client.get(
                self._url,
                params={
                    "node_id": self._node_id,
                    "page": 1,
                    "page_size": max(1, min(limit, 100)),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NewsDataError(str(exc)) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise NewsDataError("invalid eastmoney hotlist json") from exc
        if payload.get("code") != 200:
            raise NewsDataError(str(payload.get("msg") or "eastmoney hotlist request failed"))
        return payload

    def _parse(self, payload: dict[str, Any]) -> list[RawNewsArticle]:
        data = payload.get("data")
        rows = data.get("list") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return []

        refreshed_at = parse_datetime_value(data.get("next_refresh_time")) if isinstance(data, dict) else None
        items: list[RawNewsArticle] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                continue
            title = _clean_text(str(row.get("title") or ""))
            if not title:
                continue
            url = _clean_text(str(row.get("www_url") or row.get("mobile_url") or self.spec.homepage))
            desc = _clean_text(str(row.get("desc") or ""))
            labels = _display_labels(row.get("extra_info"))
            summary = _hotlist_summary(index=index, desc=desc, labels=labels)
            article_meta = self._fetch_article_meta(url)
            if not article_meta:
                continue
            published_at = article_meta["published_at"]
            author = article_meta["author"] or article_meta["source"]
            if not published_at or not author:
                continue
            items.append(
                RawNewsArticle(
                    source_id=self.spec.id,
                    title=title,
                    url=url or self.spec.homepage,
                    summary=summary,
                    published_at=published_at,
                    author=author,
                    raw_payload={
                        "providerUrl": self._url,
                        "providerName": "东方财富",
                        "rank": index,
                        "item": row,
                        "articleTitle": article_meta["title"],
                        "articleSource": article_meta["source"],
                        "hotlistRefreshAt": refreshed_at.isoformat() if refreshed_at else None,
                        "publishedAt": published_at.isoformat() if published_at else None,
                        "author": author,
                    },
                    tags=("hotlist", "eastmoney"),
                )
            )
        return _dedupe(items)

    def _fetch_article_meta(self, article_url: str) -> dict[str, Any] | None:
        if not article_url.startswith(("https://finance.eastmoney.com/", "https://wap.eastmoney.com/")):
            return None
        try:
            meta = fetch_eastmoney_article_meta(article_url, page_fetcher=self._article_page_fetcher)
        except NewsDataError:
            return None
        return {
            "published_at": meta.published_at,
            "author": meta.author,
            "source": meta.source,
            "title": meta.title,
        }


def build_eastmoney_hot_provider(spec: NewsSourceSpec) -> EastmoneyHotListProvider:
    return EastmoneyHotListProvider(spec)


def _display_labels(extra_info: Any) -> list[str]:
    if not isinstance(extra_info, dict):
        return []
    rows = extra_info.get("display_text_items")
    if not isinstance(rows, list):
        return []
    labels: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = _clean_text(str(row.get("text") or ""))
        if text:
            labels.append(text)
    return labels


def _hotlist_summary(*, index: int, desc: str, labels: list[str]) -> str:
    parts = [f"东方财富热榜第{index}名"]
    parts.extend(labels)
    if desc:
        parts.append(desc)
    sentence = "；".join(parts)
    return sentence if sentence.endswith(("。", "！", "？", ".", "!", "?")) else sentence + "。"


def _clean_text(value: str) -> str:
    return " ".join(value.split())


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
