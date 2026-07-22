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

DATETIME_RE = re.compile(r"(?P<published_at>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})(?:\s+(?P<weekday>星期[一二三四五六日天]))?")


@dataclass(frozen=True)
class ClsArticleMeta:
    title: str | None
    subject: str | None
    author: str | None
    editor: str | None
    published_at: PublishedAt


PageFetcher = Callable[[str], Any]


def fetch_cls_article_meta(article_url: str, *, page_fetcher: PageFetcher | None = None) -> ClsArticleMeta:
    fetcher = page_fetcher or _fetch_article_page
    try:
        page = fetcher(article_url)
    except Exception as exc:
        raise NewsDataError(f"财联社文章页抓取失败：{exc}") from exc
    return extract_cls_article_meta(page, article_url)


def cls_detail_url(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    parts = [part for part in parsed.path.split("/") if part]
    article_id = None
    if parts and parts[-1].isdigit():
        article_id = parts[-1]
    elif raw.isdigit():
        article_id = raw

    if article_id:
        return f"https://www.cls.cn/detail/{article_id}"
    if parsed.scheme and parsed.netloc:
        return raw
    return None


def extract_cls_article_meta(page: Any, url: str) -> ClsArticleMeta:
    metadata_texts = [
        text
        for text in (_clean_text(value) for value in _selection_values(page, ".f-l.m-r-10::text"))
        if text
    ]
    metadata_lines = _metadata_lines(page)
    searchable_text = "\n".join(metadata_texts + metadata_lines)

    match = DATETIME_RE.search(searchable_text)
    if not match:
        raise NewsDataError("财联社文章页未找到发布时间")

    published_at_text = match.group("published_at")
    subject = None
    author = None
    editor = None
    for index, line in enumerate(metadata_lines):
        line_match = DATETIME_RE.fullmatch(line)
        if not line_match:
            continue
        published_at_text = line_match.group("published_at")
        if index >= 1 and metadata_lines[index - 1] != "原创":
            subject = metadata_lines[index - 1]
        if index + 1 < len(metadata_lines):
            author = metadata_lines[index + 1]
        if index + 2 < len(metadata_lines) and metadata_lines[index + 2].startswith("责编"):
            editor = metadata_lines[index + 2]
        break

    published_at = parse_datetime_value(published_at_text)
    if not published_at:
        raise NewsDataError("财联社文章页发布时间格式异常")

    return ClsArticleMeta(
        title=_first_text(page, ["title::text", ".detail-title::text", "h1::text"]),
        subject=subject,
        author=author,
        editor=editor,
        published_at=published_at,
    )


def _fetch_article_page(url: str) -> Any:
    try:
        from scrapling.core.utils import set_logger
        from scrapling.fetchers import Fetcher, StealthyFetcher
    except ImportError as exc:
        raise NewsDataError("缺少 Scrapling 依赖，请安装 scrapling、patchright、playwright") from exc

    quiet_logger = logging.getLogger("cailianshe.scrapling")
    quiet_logger.handlers.clear()
    quiet_logger.addHandler(logging.NullHandler())
    quiet_logger.propagate = False
    quiet_logger.setLevel(logging.WARNING)
    set_logger(quiet_logger)

    page = Fetcher.get(url, stealthy_headers=True, timeout=30_000)
    try:
        extract_cls_article_meta(page, url)
        return page
    except NewsDataError:
        return StealthyFetcher.fetch(
            url,
            headless=True,
            real_chrome=True,
            disable_resources=True,
            wait_selector=".detail-content, pre",
            wait_selector_state="attached",
            wait=1_500,
            timeout=60_000,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        )


def _metadata_lines(page: Any) -> list[str]:
    body_text = _page_text(page)
    return [line for line in (_clean_text(line) for line in body_text.splitlines()) if line]


def _first_text(page: Any, selectors: list[str]) -> str | None:
    for selector in selectors:
        text = _clean_text(_selection_value(page, selector))
        if text:
            return text
    return None


def _selection_values(page: Any, selector: str) -> list[Any]:
    selected = page.css(selector)
    if hasattr(selected, "getall"):
        return list(selected.getall())
    value = selected.get() if hasattr(selected, "get") else selected
    return [value] if value else []


def _selection_value(page: Any, selector: str) -> Any:
    selected = page.css(selector)
    return selected.get() if hasattr(selected, "get") else selected


def _page_text(page: Any) -> str:
    if hasattr(page, "get_all_text"):
        text = page.get_all_text() or ""
        if text:
            return str(text)
    return str(getattr(page, "text", "") or "")


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).replace("\xa0", " ").split())
    return text or None
