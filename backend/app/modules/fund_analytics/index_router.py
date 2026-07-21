from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from app.bootstrap.deps import get_cache, get_index_registry
from app.infrastructure.cache import TTLCache
from app.integrations.index_data import compute
from app.integrations.index_data.catalog import (
    SUPPORTED_RANGES,
    get_index_spec,
    list_index_specs,
    range_start,
)
from app.integrations.index_data.interface import IndexPoint, IndexSpec
from app.integrations.index_data.interface import IndexDataError
from app.integrations.index_data.registry import IndexProviderRegistry, call_index_provider
from app.modules.fund_analytics import models

router = APIRouter(prefix="/api/v1", tags=["indexes"])


def _today() -> date:
    return date.today()


def _split_csv(value: str | None, default: tuple[str, ...]) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _history(
    reg: IndexProviderRegistry,
    cache: TTLCache,
    spec: IndexSpec,
    source: str | None,
    start: date,
    end: date,
) -> tuple[str, list[IndexPoint]]:
    def fetch() -> tuple[str, list[IndexPoint]]:
        used_source = {"name": source or ""}

        def call(provider):
            used_source["name"] = provider.name
            return provider.get_history(spec, start, end)

        points = call_index_provider(reg, spec, source, call)
        return used_source["name"], points

    return cache.get_or_set(
        (source or "auto", spec.id, "index-history", start.isoformat(), end.isoformat()),
        fetch,
        _today(),
    )


@router.get("/indexes", response_model=list[models.IndexOut])
def indexes() -> list[models.IndexOut]:
    return [
        models.IndexOut(
            id=spec.id,
            name=spec.name,
            market=spec.market,
            currency=spec.currency,
            sources=list(spec.source_priority),
            akSymbol=spec.ak_symbol or spec.ak_em_symbol or spec.ak_global_symbol,
            yfinanceSymbol=spec.yfinance_symbol,
        )
        for spec in list_index_specs()
    ]


@router.get("/index-trends", response_model=list[models.IndexTrendOut])
def index_trends(
    indexes: str | None = None,
    ranges: str | None = None,
    source: str | None = None,
    reg: IndexProviderRegistry = Depends(get_index_registry),
    cache: TTLCache = Depends(get_cache),
) -> list[models.IndexTrendOut]:
    today = _today()
    index_ids = _split_csv(indexes, tuple(spec.id for spec in list_index_specs()))
    range_ids = _split_csv(ranges, SUPPORTED_RANGES)
    result: list[models.IndexTrendOut] = []

    for index_id in index_ids:
        spec = get_index_spec(index_id)
        start_for_fetch = min(range_start(range_id, today) for range_id in range_ids)
        try:
            used_source, points = _history(reg, cache, spec, source, start_for_fetch, today)
        except IndexDataError as exc:
            result.append(
                models.IndexTrendOut(
                    id=spec.id,
                    name=spec.name,
                    market=spec.market,
                    currency=spec.currency,
                    source=source or "unavailable",
                    ranges=[],
                    error=str(exc),
                )
            )
            continue

        trend_ranges: list[models.IndexRangeTrend] = []
        for range_id in range_ids:
            start = range_start(range_id, today)
            range_points = [point for point in points if start <= point.day <= today]
            trend_ranges.append(
                models.IndexRangeTrend(
                    range=range_id,
                    startDate=start.isoformat(),
                    endDate=today.isoformat(),
                    points=compute.build_nav_trend(range_points),
                )
            )

        result.append(
            models.IndexTrendOut(
                id=spec.id,
                name=spec.name,
                market=spec.market,
                currency=spec.currency,
                source=used_source,
                ranges=trend_ranges,
            )
        )

    return result
