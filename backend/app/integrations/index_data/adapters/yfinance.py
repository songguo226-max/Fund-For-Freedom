from __future__ import annotations

from datetime import date, timedelta
from importlib import import_module
from typing import Any

from app.integrations.index_data.interface import IndexDataError, IndexPoint, IndexSpec


class YFinanceIndexProvider:
    name = "yfinance"

    def get_history(self, spec: IndexSpec, start: date, end: date) -> list[IndexPoint]:
        if not spec.yfinance_symbol:
            raise IndexDataError(f"yfinance symbol is not configured for {spec.id}")
        try:
            yf = import_module("yfinance")
        except ImportError as exc:
            raise IndexDataError("yfinance is not installed") from exc

        try:
            ticker = yf.Ticker(spec.yfinance_symbol)
            df = ticker.history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                interval="1d",
                auto_adjust=False,
            )
        except Exception as exc:  # pragma: no cover - network/provider failure
            raise IndexDataError(str(exc)) from exc

        points = _points_from_history(df, start, end)
        if not points:
            raise IndexDataError(f"No yfinance data for {spec.id}")
        if (end - start).days >= 7 and len(points) < 2:
            raise IndexDataError(f"Insufficient yfinance data for {spec.id}")
        return points


def _points_from_history(df: Any, start: date, end: date) -> list[IndexPoint]:
    if df is None or not hasattr(df, "iterrows"):
        return []
    points: list[IndexPoint] = []
    for raw_index, row in df.iterrows():
        try:
            day = raw_index.date() if hasattr(raw_index, "date") else date.fromisoformat(str(raw_index)[:10])
            close = float(row["Close"])
        except (KeyError, TypeError, ValueError):
            continue
        if start <= day <= end and close > 0:
            points.append(IndexPoint(day=day, close=close))
    return sorted(points, key=lambda item: item.day)
