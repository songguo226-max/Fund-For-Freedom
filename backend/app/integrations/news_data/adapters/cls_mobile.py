from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx

from app.infrastructure.retry import retry_call
from app.integrations.news_data.adapters.cls_article import PageFetcher, cls_detail_url, fetch_cls_article_meta
from app.integrations.news_data.interface import NewsDataError, NewsSourceSpec, RawNewsArticle


class ClsHotListProvider:
    def __init__(
        self,
        spec: NewsSourceSpec,
        url: str = "https://www.cls.cn/v2/article/hot/list",
        client: httpx.Client | None = None,
        now_fn: Callable[[], datetime] | None = None,
        article_page_fetcher: PageFetcher | None = None,
    ) -> None:
        self.spec = spec
        self._url = url
        self._now_fn = now_fn or datetime.now
        self._article_page_fetcher = article_page_fetcher
        self._client = client or httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.cls.cn/",
            },
            timeout=20,
        )

    def fetch_latest(self, *, limit: int = 50) -> list[RawNewsArticle]:
        payload = retry_call(lambda: self._fetch_json(), retry_on=(httpx.HTTPError, NewsDataError))
        return self._parse(payload, limit=limit)

    def _fetch_json(self) -> dict[str, Any]:
        try:
            response = self._client.get(self._url, params=_signed_params())
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise NewsDataError(str(exc)) from exc
        except ValueError as exc:
            raise NewsDataError("财联社热门接口返回了非 JSON 内容") from exc

        if not isinstance(data, dict):
            raise NewsDataError("财联社热门接口返回格式异常")
        return data

    def _parse(self, payload: dict[str, Any], *, limit: int) -> list[RawNewsArticle]:
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise NewsDataError("财联社热门接口缺少 data 列表")

        items: list[RawNewsArticle] = []
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict) or row.get("is_ad"):
                continue
            title = str(row.get("title") or row.get("brief") or "").strip()
            if not title:
                continue
            article_id = row.get("id")
            url = cls_detail_url(article_id) or cls_detail_url(row.get("shareurl")) or self._url
            article_meta = self._fetch_article_meta(url)
            if not article_meta:
                continue
            items.append(
                RawNewsArticle(
                    source_id=self.spec.id,
                    title=title,
                    url=url,
                    summary="",
                    published_at=article_meta.published_at,
                    author=article_meta.author,
                    raw_payload={
                        "apiUrl": self._url,
                        "rank": index,
                        "id": article_id,
                        "title": title,
                        "brief": row.get("brief"),
                        "shareurl": row.get("shareurl"),
                        "ctime": row.get("ctime"),
                        "publishedAt": article_meta.published_at.isoformat(),
                        "author": article_meta.author,
                        "subject": article_meta.subject,
                        "editor": article_meta.editor,
                        "articleTitle": article_meta.title,
                        "payload": row,
                    },
                    tags=("hotlist", "cls"),
                )
            )
            if len(items) >= limit:
                break
        return _dedupe(items)

    def _fetch_article_meta(self, article_url: str):
        if not article_url.startswith("https://www.cls.cn/detail/"):
            return None
        try:
            meta = fetch_cls_article_meta(article_url, page_fetcher=self._article_page_fetcher)
        except NewsDataError:
            return None
        if not meta.published_at or not meta.author:
            return None
        return meta


ClsMobileTelegraphProvider = ClsHotListProvider


def build_cls_provider(spec: NewsSourceSpec) -> ClsHotListProvider:
    return ClsHotListProvider(spec)


def _signed_params(extra: dict[str, Any] | None = None) -> dict[str, str]:
    params = {
        "appName": "CailianpressWeb",
        "os": "web",
        "sv": "7.7.5",
    }
    if extra:
        params.update({key: str(value) for key, value in extra.items()})
    base = "&".join(f"{key}={params[key]}" for key in sorted(params))
    params["sign"] = hashlib.md5(hashlib.sha1(base.encode("utf-8")).hexdigest().encode("utf-8")).hexdigest()
    return params


def _dedupe(items: list[RawNewsArticle]) -> list[RawNewsArticle]:
    seen: set[str] = set()
    result: list[RawNewsArticle] = []
    for item in items:
        key = item.url if item.url != "https://www.cls.cn/v2/article/hot/list" else item.title
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
