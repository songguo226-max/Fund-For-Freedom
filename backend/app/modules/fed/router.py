from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from httpx import HTTPError

from app.bootstrap.deps import get_cache
from app.infrastructure.cache import TTLCache
from app.modules.fed.models import FedEconomyOut
from app.modules.fed.service import fetch_economy_at_a_glance

router = APIRouter(prefix="/api/v1/fed", tags=["fed"])


@router.get("/economy-at-a-glance", response_model=FedEconomyOut)
def economy_at_a_glance(cache: TTLCache = Depends(get_cache)) -> FedEconomyOut:
    try:
        return cache.get_or_set(
            ("fed", "economy-at-a-glance"),
            fetch_economy_at_a_glance,
            date.today(),
        )
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail="Federal Reserve data is temporarily unavailable") from exc
