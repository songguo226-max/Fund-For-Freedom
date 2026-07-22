from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


class IndexDataError(Exception):
    """Index data could not be fetched or parsed."""


class IndexNotFound(IndexDataError):
    """Requested index is not supported or has no data."""


@dataclass(frozen=True)
class IndexSpec:
    id: str
    name: str
    market: str
    currency: str
    source_priority: tuple[str, ...]
    ak_symbol: str | None = None
    ak_em_symbol: str | None = None
    ak_tx_symbol: str | None = None
    ak_sina_symbol: str | None = None
    ak_global_symbol: str | None = None
    yfinance_symbol: str | None = None


@dataclass(frozen=True)
class IndexPoint:
    day: date
    close: float
    pct: float | None = None


@runtime_checkable
class IndexDataProvider(Protocol):
    name: str

    def get_history(self, spec: IndexSpec, start: date, end: date) -> list[IndexPoint]: ...
