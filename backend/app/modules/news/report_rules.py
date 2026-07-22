from __future__ import annotations

import re
from typing import Any


HOTLIST_WEEKLY_RANK_LIMIT = 2
RANKED_HOTLIST_SOURCE_IDS = {"cls", "eastmoney", "gelonghui", "xueqiu"}
WEEKLY_SNAPSHOT_SOURCE_IDS = {"cls", "eastmoney", "gelonghui", "xueqiu"}


def weekly_eligible(item: dict[str, Any]) -> bool:
    """Return whether an item should appear in the weekly report.

    Weekly inclusion is rule-based, not score-threshold-based. Ranked hotlist
    feeds are daily topic lists, so only the top topics are promoted.
    """

    if item.get("source_id") not in RANKED_HOTLIST_SOURCE_IDS:
        return True
    rank = hotlist_rank(item)
    return rank is not None and rank <= HOTLIST_WEEKLY_RANK_LIMIT


def report_bucket(item: dict[str, Any]) -> str:
    return "weekly" if weekly_eligible(item) else "daily"


def hotlist_rank(item: dict[str, Any]) -> int | None:
    snapshot_rank = item.get("rank_snapshot_rank")
    if isinstance(snapshot_rank, int):
        return snapshot_rank
    if isinstance(snapshot_rank, str) and snapshot_rank.isdigit():
        return int(snapshot_rank)

    text = f"{item.get('summary') or ''} {item.get('title') or ''}"
    for pattern in (r"第\s*([1-9]\d*)\s*名", r"Ек\s*([1-9]\d*)\s*Ућ"):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None
