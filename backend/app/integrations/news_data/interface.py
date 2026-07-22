from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class NewsDataError(Exception):
    """Raised when a news source cannot be fetched or parsed."""


class SourceTier(str, Enum):
    OFFICIAL = "official"
    MEDIA = "media"
    OPINION = "opinion"


@dataclass(frozen=True)
class NewsSourceSpec:
    id: str
    name: str
    tier: SourceTier
    reliability_score: int
    homepage: str
    adapter: str
    enabled: bool = True
    cache_minutes: int = 10
    rate_limit_per_minute: int = 12
    requires_login: bool = False
    terms_note: str = ""


@dataclass(frozen=True)
class RawNewsArticle:
    source_id: str
    title: str
    url: str
    summary: str = ""
    published_at: date | datetime | None = None
    author: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()


@runtime_checkable
class NewsDataProvider(Protocol):
    spec: NewsSourceSpec

    def fetch_latest(self, *, limit: int = 50) -> list[RawNewsArticle]: ...
