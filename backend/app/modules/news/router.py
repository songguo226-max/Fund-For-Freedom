from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.bootstrap.deps import get_news_rate_limiter, get_news_registry, get_news_store
from app.config.news_settings import news_settings
from app.infrastructure.news_store import NewsStore
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.integrations.news_data.registry import NewsProviderRegistry
from app.modules.news import models
from app.modules.news.report_rules import report_bucket
from app.modules.news.service import NewsAggregationService

router = APIRouter(prefix="/api/v1/news", tags=["news"])


@router.get("/bootstrap", response_model=models.NewsBootstrapOut)
def bootstrap(
    store: NewsStore = Depends(get_news_store),
    registry: NewsProviderRegistry = Depends(get_news_registry),
) -> models.NewsBootstrapOut:
    _initialize_news_system(store, registry)
    return models.NewsBootstrapOut(
        holdings=[_holding_out(item) for item in store.list_holdings()],
        watchlist=[_watchlist_out(item) for item in store.list_watchlist()],
        sources=[_source_out(item) for item in store.list_news_sources()],
        refreshCacheMinutes=news_settings.refresh_cache_minutes,
        dailySummaryHour=news_settings.daily_summary_hour,
        timezone=news_settings.timezone,
        defaultAction=news_settings.default_action,
    )


@router.post("/watchlist", response_model=list[models.WatchlistItemOut])
def sync_watchlist(
    payload: models.WatchlistSyncIn,
    store: NewsStore = Depends(get_news_store),
    registry: NewsProviderRegistry = Depends(get_news_registry),
) -> list[models.WatchlistItemOut]:
    _initialize_news_system(store, registry)
    store.replace_watchlist([item.model_dump() for item in payload.favorites], origin="favorite")
    store.replace_watchlist([item.model_dump() for item in payload.recents], origin="recent")
    for item in payload.favorites + payload.recents:
        store.upsert_holding(
            code=item.code,
            name=item.name,
            aliases=item.aliases,
            tags=item.tags,
            source="watchlist",
        )
    return [_watchlist_out(item) for item in store.list_watchlist()]


@router.get("/sources", response_model=list[models.NewsSourceOut])
def sources(
    store: NewsStore = Depends(get_news_store),
    registry: NewsProviderRegistry = Depends(get_news_registry),
) -> list[models.NewsSourceOut]:
    _initialize_news_system(store, registry)
    return [_source_out(item) for item in store.list_news_sources()]


@router.get("/refresh", response_model=models.NewsRefreshOut)
def refresh(
    force: bool = False,
    stale_ok: bool = Query(False, alias="staleOk"),
    limit: int = 30,
    store: NewsStore = Depends(get_news_store),
    registry: NewsProviderRegistry = Depends(get_news_registry),
    rate_limiter: InMemoryRateLimiter = Depends(get_news_rate_limiter),
) -> models.NewsRefreshOut:
    service = NewsAggregationService(store=store, registry=registry, rate_limiter=rate_limiter)
    payload = service.refresh(limit_per_source=max(1, min(limit, 100)), force=force, allow_stale_cache=stale_ok)
    return models.NewsRefreshOut(
        refreshedAt=payload["refreshedAt"],
        sources=[models.NewsSourceRefreshOut(**item) for item in payload["sources"]],
        items=[_news_item_out(item) for item in payload["items"]],
    )


def _initialize_news_system(store: NewsStore, registry: NewsProviderRegistry) -> None:
    store.seed_holdings()
    for spec in registry.specs():
        store.upsert_news_source(spec)
    store.disable_news_sources_except({spec.id for spec in registry.specs()})


def _holding_out(row: dict) -> models.HoldingOut:
    return models.HoldingOut(
        id=row.get("id"),
        code=row.get("code"),
        name=row["name"],
        lookupQuery=row.get("lookup_query"),
        aliases=row.get("aliases", []),
        tags=row.get("tags", []),
        source=row.get("source", "manual"),
    )


def _watchlist_out(row: dict) -> models.WatchlistItemOut:
    return models.WatchlistItemOut(
        code=row.get("code"),
        name=row["name"],
        type=row.get("type") or "",
        origin=row["origin"],
        position=row["position"],
    )


def _source_out(row: dict) -> models.NewsSourceOut:
    return models.NewsSourceOut(
        id=row["id"],
        name=row["name"],
        tier=row["tier"],
        reliabilityScore=row["reliability_score"],
        adapter=row["adapter"],
        enabled=bool(row["enabled"]),
        cacheMinutes=row["cache_minutes"],
        rateLimitPerMinute=row["rate_limit_per_minute"],
        requiresLogin=bool(row["requires_login"]),
        homepage=row["homepage"],
        termsNote=row["terms_note"],
    )


def _news_item_out(row: dict) -> models.NewsItemOut:
    total_score = row.get("total_score") or 0
    relations = row.get("relations", [])
    impact_variables = sorted(
        {
            variable
            for relation in relations
            for variable in relation.get("impact_variables", [])
        }
    )
    return models.NewsItemOut(
        id=row["id"],
        sourceId=row["source_id"],
        sourceName=row["source_name"],
        sourceTier=row["source_tier"],
        title=row["title"],
        summary=row.get("summary") or "",
        url=row["url"],
        publishedAt=row.get("published_at"),
        author=row.get("author"),
        relevanceScore=row.get("relevance_score") or 0,
        durationScore=row.get("duration_score") or 0,
        surpriseScore=row.get("surprise_score") or 0,
        reliabilityScore=row.get("reliability_score") or 0,
        totalScore=total_score,
        reportBucket=report_bucket(row),
        rankSnapshotDate=row.get("rank_snapshot_date"),
        rankSnapshotRank=row.get("rank_snapshot_rank"),
        relatedFunds=[
            {
                "code": relation.get("fund_code"),
                "name": relation["fund_name"],
                "relationType": relation["relation_type"],
                "matchedKeywords": relation.get("matched_keywords", []),
            }
            for relation in relations
        ],
        impactVariables=impact_variables,
        suggestedAction=news_settings.default_action,
    )
