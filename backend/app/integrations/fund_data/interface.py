from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


class ProviderError(Exception):
    """数据源抓取或解析失败。"""


class FundNotFound(ProviderError):
    """基金代码不存在或无数据。"""


@dataclass(frozen=True)
class FundHit:
    code: str
    name: str
    type: str
    pinyin: str | None = None


@dataclass(frozen=True)
class FundMeta:
    code: str
    name: str
    latest_date: date
    latest_nav: float
    latest_cumulative_nav: float
    latest_pct: float
    type: str = ""


@dataclass(frozen=True)
class FundDay:
    day: date
    nav: float
    cumulative_nav: float
    pct_change: float


@runtime_checkable
class FundDataProvider(Protocol):
    name: str

    def search(self, q: str) -> list[FundHit]: ...
    def get_meta(self, code: str) -> FundMeta: ...
    def get_nav_history(self, code: str, start: date, end: date) -> list[FundDay]: ...
