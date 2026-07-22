from __future__ import annotations

import hashlib
import re


def event_key(title: str, summary: str = "") -> str:
    text = title or summary
    normalized = re.sub(r"20\d{2}[-年]\d{1,2}[-月]\d{1,2}日?", "", text)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "", normalized).lower()
    normalized = normalized[:80]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def canonical_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()
