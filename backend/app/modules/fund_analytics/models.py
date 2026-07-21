from __future__ import annotations

from pydantic import BaseModel


class SearchHit(BaseModel):
    code: str
    name: str
    type: str
    pinyin: str | None = None


class FundMetaOut(BaseModel):
    code: str
    name: str
    type: str = ""
    latestDate: str
    latestNav: float
    latestCumulativeNav: float
    latestPct: float


class CalendarCell(BaseModel):
    type: str
    day: int | None = None
    date: str | None = None
    nav: float | None = None
    cumulativeNav: float | None = None
    pct: float | None = None


class CalendarMonth(BaseModel):
    year: int
    month: int
    tradeDays: int
    monthReturn: float
    startNav: float | None = None
    endNav: float | None = None
    cells: list[CalendarCell]


class MonthlyItem(BaseModel):
    year: int
    month: int
    startDate: str
    endDate: str
    startNav: float
    endNav: float
    cumulativeNav: float
    pct: float
    cumulativePct: float
    tradeDays: int
    partial: bool


class MonthlyOut(BaseModel):
    previousYears: list[int]
    currentYear: int
    latestDate: str
    items: list[MonthlyItem]


class TrendPoint(BaseModel):
    date: str
    nav: float
    cumulativeNav: float
    pct: float


class IndexOut(BaseModel):
    id: str
    name: str
    market: str
    currency: str
    sources: list[str]
    akSymbol: str | None = None
    yfinanceSymbol: str | None = None


class IndexTrendPoint(BaseModel):
    date: str
    close: float
    nav: float
    pct: float
    cumulativePct: float


class IndexRangeTrend(BaseModel):
    range: str
    startDate: str
    endDate: str
    points: list[IndexTrendPoint]


class IndexTrendOut(BaseModel):
    id: str
    name: str
    market: str
    currency: str
    source: str
    ranges: list[IndexRangeTrend]
    error: str | None = None


class DataSourceOut(BaseModel):
    id: str
    name: str
    status: str
    providerName: str | None = None
    pythonPackage: str | None = None
    packageInstalled: bool | None = None
    installCommand: str | None = None
    homepage: str
    repository: str | None = None
    license: str | None = None
    markets: list[str]
    assetClasses: list[str]
    dataTypes: list[str]
    frequencies: list[str]
    strengths: list[str]
    limitations: list[str]
    termsNote: str
