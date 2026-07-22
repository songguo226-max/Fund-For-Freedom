from __future__ import annotations

from pydantic import BaseModel, Field


class HoldingIn(BaseModel):
    code: str | None = None
    name: str
    type: str = ""
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    origin: str = "favorite"


class HoldingOut(BaseModel):
    id: int | None = None
    code: str | None = None
    name: str
    lookupQuery: str | None = None
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"


class WatchlistSyncIn(BaseModel):
    favorites: list[HoldingIn] = Field(default_factory=list)
    recents: list[HoldingIn] = Field(default_factory=list)


class WatchlistItemOut(BaseModel):
    code: str | None = None
    name: str
    type: str = ""
    origin: str
    position: int


class NewsSourceOut(BaseModel):
    id: str
    name: str
    tier: str
    reliabilityScore: int
    adapter: str
    enabled: bool
    cacheMinutes: int
    rateLimitPerMinute: int
    requiresLogin: bool
    homepage: str
    termsNote: str


class NewsBootstrapOut(BaseModel):
    holdings: list[HoldingOut]
    watchlist: list[WatchlistItemOut]
    sources: list[NewsSourceOut]
    refreshCacheMinutes: int
    dailySummaryHour: int
    timezone: str
    defaultAction: str


class NewsSourceRefreshOut(BaseModel):
    sourceId: str
    sourceName: str
    status: str
    reason: str = ""
    fetched: int
    articleIds: list[str] = Field(default_factory=list)
    fetchedAt: str | None = None


class NewsItemOut(BaseModel):
    id: str
    sourceId: str
    sourceName: str
    sourceTier: str
    title: str
    summary: str = ""
    url: str
    publishedAt: str | None = None
    author: str | None = None
    relevanceScore: int = 0
    durationScore: int = 0
    surpriseScore: int = 0
    reliabilityScore: int = 0
    totalScore: int = 0
    reportBucket: str = "filtered"
    rankSnapshotDate: str | None = None
    rankSnapshotRank: int | None = None
    relatedFunds: list[dict] = Field(default_factory=list)
    impactVariables: list[str] = Field(default_factory=list)
    suggestedAction: str = "不操作"


class NewsRefreshOut(BaseModel):
    refreshedAt: str
    sources: list[NewsSourceRefreshOut]
    items: list[NewsItemOut]
