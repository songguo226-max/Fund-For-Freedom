from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from html import unescape
from typing import Any


PublishedAt = date | datetime


def parse_datetime_value(value: Any) -> PublishedAt | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, int | float):
        return _datetime_from_timestamp(value)

    raw = str(value).strip()
    if not raw:
        return None
    if re.fullmatch(r"\d{10,13}", raw):
        return _datetime_from_timestamp(int(raw))

    normalized = (
        raw.replace("年", "-")
        .replace("月", "-")
        .replace("日", "")
        .replace("/", "-")
        .replace(".", "-")
        .replace("Z", "+00:00")
        .strip()
    )
    normalized = re.sub(r"\s+", " ", normalized)
    if re.fullmatch(r"20\d{2}-\d{1,2}-\d{1,2}", normalized):
        try:
            return datetime.strptime(normalized, "%Y-%m-%d").date()
        except ValueError:
            return None
    if "T" not in normalized and " " in normalized:
        normalized = normalized.replace(" ", "T", 1)

    for candidate in (normalized, normalized.replace("T", " ")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(normalized.replace("T", " ")[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.strptime(normalized[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_article_published_at(html: str, *, source: str = "") -> PublishedAt | None:
    text = unescape(html)
    patterns = _source_patterns(source) + _COMMON_PATTERNS
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            parsed = parse_datetime_value(match.group("date").strip())
            if parsed:
                return parsed
    return None


def _datetime_from_timestamp(value: int | float) -> datetime | None:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    return datetime.fromtimestamp(timestamp, timezone(timedelta(hours=8), name="Asia/Shanghai"))


def _source_patterns(source: str) -> tuple[str, ...]:
    if source == "eastmoney":
        return (
            r'<span[^>]*class=["\'][^"\']*\btime\b[^"\']*["\'][^>]*>\s*(?P<date>20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)\s*</span>',
            r'<span[^>]*class=["\'][^"\']*\bflr\b[^"\']*["\'][^>]*>\s*(?P<date>20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)\s*</span>',
            r"(?:发布时间|时间|日期)\s*[:：]\s*(?P<date>20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)",
        )
    if source == "xueqiu":
        return (
            r'<time\b[^>]*\btitle=["\'](?P<date>[^"\']+)["\']',
            r'<time\b[^>]*\bdatetime=["\'](?P<date>[^"\']+)["\']',
            r"发布于\s*(?P<date>20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)",
            r'"created_at"\s*:\s*"(?P<date>[^"]+)"',
            r'"createdAt"\s*:\s*"(?P<date>[^"]+)"',
            r'"timeBefore"\s*:\s*"发布于(?P<date>[^"]+)"',
            r'data-created_at=["\'](?P<date>\d{10,13})["\']',
        )
    return ()


_COMMON_PATTERNS = (
    r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|pubdate|publishdate|datePublished)["\'][^>]+content=["\'](?P<date>[^"\']+)["\']',
    r'<meta[^>]+content=["\'](?P<date>[^"\']+)["\'][^>]+(?:property|name)=["\'](?:article:published_time|pubdate|publishdate|datePublished)["\']',
)
