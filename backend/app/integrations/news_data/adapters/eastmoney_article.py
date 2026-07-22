from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.integrations.news_data.adapters.article_dates import PublishedAt, parse_datetime_value
from app.integrations.news_data.interface import NewsDataError


os.environ.setdefault("SCRAPLING_LOG_LEVEL", "WARNING")
logging.getLogger("scrapling").setLevel(logging.WARNING)

DATETIME_RE = re.compile(r"(?P<published_at>\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2})")


@dataclass(frozen=True)
class EastmoneyArticleMeta:
    title: str | None
    author: str | None
    source: str | None
    published_at: PublishedAt


PageFetcher = Callable[[str], Any]


def fetch_eastmoney_article_meta(
    article_url: str,
    *,
    page_fetcher: PageFetcher | None = None,
) -> EastmoneyArticleMeta:
    fetcher = page_fetcher or _fetch_article_page
    try:
        page = fetcher(article_url)
    except Exception as exc:
        raise NewsDataError(f"东方财富文章页抓取失败：{exc}") from exc
    return extract_eastmoney_article_meta(page, article_url)


def extract_eastmoney_article_meta(page: Any, url: str) -> EastmoneyArticleMeta:
    info_lines = _info_lines(page)
    searchable_text = "\n".join(info_lines)

    match = DATETIME_RE.search(searchable_text)
    if not match:
        match = DATETIME_RE.search(_page_text(page))
    if not match:
        raise NewsDataError("东方财富文章页未找到发布时间")

    published_at = parse_datetime_value(match.group("published_at"))
    if not published_at:
        raise NewsDataError("东方财富文章页发布时间格式异常")

    author = None
    source = None
    for line in info_lines:
        author = author or _prefixed_value(line, ("作者：", "作者:"))
        source = source or _prefixed_value(line, ("来源：", "来源:"))

    title = _first_text(
        page,
        [
            "#topbox .title::text",
            ".topbox .title::text",
            "h1::text",
            "title::text",
        ],
        adaptive=True,
    )
    if title and title.endswith("_ 东方财富网"):
        title = _clean_text(title.removesuffix("_ 东方财富网"))

    return EastmoneyArticleMeta(
        title=title,
        author=author,
        source=source,
        published_at=published_at,
    )


def _fetch_article_page(url: str) -> Any:
    try:
        from scrapling.core.utils import set_logger
        from scrapling.fetchers import Fetcher, StealthyFetcher
    except ImportError as exc:
        raise NewsDataError("缺少 Scrapling 依赖，请安装 scrapling、patchright、playwright") from exc

    quiet_logger = logging.getLogger("eastmoney.scrapling")
    quiet_logger.handlers.clear()
    quiet_logger.addHandler(logging.NullHandler())
    quiet_logger.propagate = False
    quiet_logger.setLevel(logging.WARNING)
    set_logger(quiet_logger)

    headers = {"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    try:
        page = Fetcher.get(url, stealthy_headers=True, timeout=30_000, headers=headers)
        extract_eastmoney_article_meta(page, url)
        return page
    except NewsDataError:
        return StealthyFetcher.fetch(
            url,
            headless=True,
            real_chrome=True,
            disable_resources=True,
            wait_selector=".tipbox .infos, #topbox",
            wait_selector_state="attached",
            wait=1_500,
            timeout=60_000,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_headers=headers,
        )


def _info_lines(page: Any) -> list[str]:
    texts: list[Any] = []
    for selector in [
        ".tipbox .infos .item::text",
        "#topbox .infos .item::text",
        ".infos .item::text",
    ]:
        texts.extend(_selection_values(page, selector, auto_save=True))
    return [line for line in (_clean_text(text) for text in texts) if line]


def _first_text(page: Any, selectors: list[str], *, adaptive: bool = False) -> str | None:
    for selector in selectors:
        text = _clean_text(_selection_value(page, selector, adaptive=adaptive))
        if text:
            return text
    return None


def _selection_values(page: Any, selector: str, **kwargs: Any) -> list[Any]:
    selected = _css(page, selector, **kwargs)
    if hasattr(selected, "getall"):
        return list(selected.getall())
    value = selected.get() if hasattr(selected, "get") else selected
    return [value] if value else []


def _selection_value(page: Any, selector: str, **kwargs: Any) -> Any:
    selected = _css(page, selector, **kwargs)
    return selected.get() if hasattr(selected, "get") else selected


def _css(page: Any, selector: str, **kwargs: Any) -> Any:
    try:
        return page.css(selector, **kwargs)
    except TypeError:
        return page.css(selector)


def _page_text(page: Any) -> str:
    if hasattr(page, "get_all_text"):
        text = page.get_all_text() or ""
        if text:
            return str(text)
    return str(getattr(page, "text", "") or "")


def _prefixed_value(line: str, prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
        if line.startswith(prefix):
            return _clean_text(line.removeprefix(prefix))
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).replace("\xa0", " ").split())
    return text or None
