from __future__ import annotations

from app.integrations.index_data.interface import IndexPoint


def build_nav_trend(points: list[IndexPoint]) -> list[dict]:
    sorted_points = [p for p in sorted(points, key=lambda item: item.day) if p.close > 0]
    if not sorted_points:
        return []

    base = sorted_points[0].close
    previous_close: float | None = None
    trend: list[dict] = []
    for point in sorted_points:
        pct = point.pct
        if pct is None:
            pct = 0.0 if previous_close is None else (point.close / previous_close - 1) * 100
        nav = point.close / base
        trend.append(
            {
                "date": point.day.isoformat(),
                "close": round(point.close, 4),
                "nav": round(nav, 6),
                "pct": round(pct, 4),
                "cumulativePct": round((nav - 1) * 100, 4),
            }
        )
        previous_close = point.close
    return trend
