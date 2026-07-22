from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

from app.integrations.news_data.adapters.article_dates import PublishedAt, parse_datetime_value
from app.integrations.news_data.interface import NewsDataError


os.environ.setdefault("SCRAPLING_LOG_LEVEL", "WARNING")
logging.getLogger("scrapling").setLevel(logging.WARNING)


@dataclass(frozen=True)
class XueqiuArticleMeta:
    author: str | None
    title: str | None
    published_at: PublishedAt


PageFetcher = Callable[[str], Any]


def fetch_xueqiu_article_meta(article_url: str, *, page_fetcher: PageFetcher | None = None) -> XueqiuArticleMeta:
    fetcher = page_fetcher or _fetch_article_page
    try:
        page = fetcher(article_url)
    except Exception as exc:
        raise NewsDataError(f"雪球文章页抓取失败：{exc}") from exc
    return extract_xueqiu_article_meta(page, article_url)


def _fetch_article_page(url: str) -> Any:
    try:
        from scrapling.core.utils import set_logger
        from scrapling.fetchers import StealthyFetcher
    except ImportError as exc:
        raise NewsDataError("缺少 Scrapling StealthyFetcher 依赖，请安装 scrapling、patchright、playwright") from exc

    quiet_logger = logging.getLogger("xueqiu.scrapling")
    quiet_logger.handlers.clear()
    quiet_logger.addHandler(logging.NullHandler())
    quiet_logger.propagate = False
    quiet_logger.setLevel(logging.WARNING)
    set_logger(quiet_logger)

    return StealthyFetcher.fetch(
        url,
        headless=True,
        real_chrome=True,
        disable_resources=True,
        wait_selector='time[itemprop="datePublished"], .avatar__subtitle',
        wait_selector_state="attached",
        wait=1_500,
        timeout=60_000,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    )


def extract_xueqiu_article_meta(page: Any, url: str) -> XueqiuArticleMeta:
    published_at_text = _first_text(
        page,
        [
            'time[itemprop="datePublished"]::text',
            'time[itemprop="datePublished"]::attr(title)',
            ".avatar__subtitle time::text",
        ],
    )

    if not published_at_text:
        body_text = _page_text(page)
        match = re.search(r"发布于\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", body_text)
        if match:
            published_at_text = match.group(1)

    published_at = parse_datetime_value(published_at_text)
    if not published_at:
        raise NewsDataError("雪球文章页未找到发布时间")

    author_selectors = [
        ".article__author .name::text",
        ".article__author a.name::text",
        ".avatar .name::text",
        ".user-name::text",
    ]
    user_href = _user_href_from_url(url)
    if user_href:
        author_selectors.insert(2, f'a[href="{user_href}"]::text')

    return XueqiuArticleMeta(
        author=_first_text(page, author_selectors),
        title=_first_text(page, [".article__bd__title::text", "h1::text"]),
        published_at=published_at,
    )


def _first_text(page: Any, selectors: list[str]) -> str | None:
    for selector in selectors:
        selected = page.css(selector)
        value = selected.get() if hasattr(selected, "get") else selected
        if value:
            return " ".join(str(value).replace("\xa0", " ").split())
    return None


def _page_text(page: Any) -> str:
    if hasattr(page, "get_all_text"):
        text = page.get_all_text() or ""
        if text:
            return str(text)
    return str(getattr(page, "text", "") or "")


def _user_href_from_url(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if not parts:
        return None
    return f"/{parts[0]}"
