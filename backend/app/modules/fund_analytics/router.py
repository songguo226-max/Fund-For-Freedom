from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Response

from app.bootstrap.deps import get_cache, get_registry
from app.infrastructure.cache import TTLCache
from app.integrations.fund_data.interface import FundDay
from app.integrations.fund_data.registry import ProviderRegistry, call_with_fallback
from app.modules.fund_analytics import compute, export, models

router = APIRouter(prefix="/api/v1")

_RANGE_DAYS = {"3m": 92, "6m": 183, "1y": 366, "3y": 1096, "all": 4000}


def _today() -> date:
    return date.today()


def _history(
    reg: ProviderRegistry,
    cache: TTLCache,
    source: str | None,
    code: str,
    start: date,
    end: date,
) -> list[FundDay]:
    return cache.get_or_set(
        (source or "auto", code, "history", start.isoformat(), end.isoformat()),
        lambda: call_with_fallback(reg, source, lambda p: p.get_nav_history(code, start, end)),
        _today(),
    )


@router.get("/search", response_model=list[models.SearchHit])
def search(q: str, source: str | None = None, reg: ProviderRegistry = Depends(get_registry)) -> list[models.SearchHit]:
    hits = call_with_fallback(reg, source, lambda p: p.search(q))
    return [models.SearchHit(code=h.code, name=h.name, type=h.type, pinyin=h.pinyin) for h in hits]


@router.get("/fund/{code}/meta", response_model=models.FundMetaOut)
def meta(
    code: str,
    source: str | None = None,
    reg: ProviderRegistry = Depends(get_registry),
    cache: TTLCache = Depends(get_cache),
) -> models.FundMetaOut:
    today = _today()
    meta_item = cache.get_or_set(
        (source or "auto", code, "meta"),
        lambda: call_with_fallback(reg, source, lambda p: p.get_meta(code)),
        today,
    )
    return models.FundMetaOut(
        code=meta_item.code,
        name=meta_item.name,
        type=meta_item.type,
        latestDate=meta_item.latest_date.isoformat(),
        latestNav=meta_item.latest_nav,
        latestCumulativeNav=meta_item.latest_cumulative_nav,
        latestPct=meta_item.latest_pct,
    )


@router.get("/fund/{code}/calendar", response_model=list[models.CalendarMonth])
def calendar(
    code: str,
    months: int = Query(3, ge=1, le=12),
    source: str | None = None,
    reg: ProviderRegistry = Depends(get_registry),
    cache: TTLCache = Depends(get_cache),
) -> list[dict]:
    today = _today()
    start = compute.add_months(date(today.year, today.month, 1), -months)
    days = _history(reg, cache, source, code, start, today)
    return compute.build_calendar(days, start, today)


@router.get("/fund/{code}/monthly", response_model=models.MonthlyOut)
def monthly(
    code: str,
    source: str | None = None,
    reg: ProviderRegistry = Depends(get_registry),
    cache: TTLCache = Depends(get_cache),
) -> dict:
    today = _today()
    years = [today.year - 3, today.year - 2, today.year - 1, today.year]
    start = date(today.year - 3, 1, 1)
    days = _history(reg, cache, source, code, start, today)
    items = compute.build_monthly_returns(days, years)
    latest = max((item["endDate"] for item in items), default=today.isoformat())
    return {
        "previousYears": years[:-1],
        "currentYear": today.year,
        "latestDate": latest,
        "items": items,
    }


@router.get("/fund/{code}/trend", response_model=list[models.TrendPoint])
def trend(
    code: str,
    range: str = "1y",
    source: str | None = None,
    reg: ProviderRegistry = Depends(get_registry),
    cache: TTLCache = Depends(get_cache),
) -> list[dict]:
    today = _today()
    span = _RANGE_DAYS.get(range, 366)
    start = today - timedelta(days=span)
    days = _history(reg, cache, source, code, start, today)
    return compute.build_trend(days)


@router.get("/fund/{code}/export.csv")
def export_csv(
    code: str,
    type: str = "daily",
    source: str | None = None,
    reg: ProviderRegistry = Depends(get_registry),
    cache: TTLCache = Depends(get_cache),
) -> Response:
    today = _today()
    if type == "monthly":
        start = date(today.year - 3, 1, 1)
        days = _history(reg, cache, source, code, start, today)
        years = [today.year - 3, today.year - 2, today.year - 1, today.year]
        text = export.monthly_csv(compute.build_monthly_returns(days, years))
    else:
        start = compute.add_months(date(today.year, today.month, 1), -2)
        days = _history(reg, cache, source, code, start, today)
        text = export.daily_csv(days)

    return Response(
        content="\ufeff" + text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="fund_{code}_{type}.csv"'},
    )
