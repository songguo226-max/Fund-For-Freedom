from __future__ import annotations

from pydantic import BaseModel


class FedPoint(BaseModel):
    date: str
    label: str
    value: float
    lower: float | None = None
    upper: float | None = None


class FedIndicator(BaseModel):
    id: str
    title: str
    detailTitle: str
    cardTitle: str
    description: str
    unit: str
    chartType: str
    color: str
    source: str
    sourceUrl: str
    pageUrl: str
    latestLabel: str
    latestValue: float
    latestUpper: float | None = None
    latestDisplay: str
    points: list[FedPoint]


class FedEconomyOut(BaseModel):
    title: str
    updatedAt: str
    indicators: list[FedIndicator]
