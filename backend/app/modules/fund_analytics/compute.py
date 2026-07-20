from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.integrations.fund_data.interface import FundDay


def add_months(day: date, months: int) -> date:
    year = day.year + (day.month - 1 + months) // 12
    month = (day.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def month_end(month: date) -> date:
    return add_months(month, 1) - timedelta(days=1)


def iter_months(start: date, end: date) -> list[date]:
    months: list[date] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        months.append(cursor)
        cursor = add_months(cursor, 1)
    return months


def pct_state(value: float) -> str:
    if value > 0:
        return "rise"
    if value < 0:
        return "fall"
    return "flat"


def build_calendar(days: list[FundDay], start: date, end: date) -> list[dict]:
    sorted_days = sorted(days, key=lambda d: d.day)
    by_day = {d.day: d for d in sorted_days}
    result: list[dict] = []

    for month in iter_months(start, end):
        items = [d for d in sorted_days if d.day.year == month.year and d.day.month == month.month]
        first_cell = month - timedelta(days=(month.weekday() + 1) % 7)
        last_day = min(month_end(month), end)
        last_cell = last_day + timedelta(days=(6 - ((last_day.weekday() + 1) % 7)))
        cells: list[dict] = []
        cursor = first_cell

        while cursor <= last_cell:
            item = by_day.get(cursor)
            if cursor.month != month.month or cursor > end:
                cells.append(
                    {
                        "type": "blank",
                        "day": None,
                        "date": None,
                        "nav": None,
                        "cumulativeNav": None,
                        "pct": None,
                    }
                )
            elif item is None:
                cells.append(
                    {
                        "type": "closed",
                        "day": cursor.day,
                        "date": cursor.isoformat(),
                        "nav": None,
                        "cumulativeNav": None,
                        "pct": None,
                    }
                )
            else:
                cells.append(
                    {
                        "type": "trading",
                        "day": item.day.day,
                        "date": item.day.isoformat(),
                        "nav": round(item.nav, 4),
                        "cumulativeNav": round(item.cumulative_nav, 4),
                        "pct": round(item.pct_change, 4),
                    }
                )
            cursor += timedelta(days=1)

        month_return = (items[-1].nav / items[0].nav - 1) * 100 if items and items[0].nav else 0.0
        result.append(
            {
                "year": month.year,
                "month": month.month,
                "tradeDays": len(items),
                "monthReturn": round(month_return, 4),
                "startNav": round(items[0].nav, 4) if items else None,
                "endNav": round(items[-1].nav, 4) if items else None,
                "cells": cells,
            }
        )

    return list(reversed(result))


def build_monthly_returns(days: list[FundDay], years: list[int]) -> list[dict]:
    sorted_days = sorted(days, key=lambda d: d.day)
    grouped: dict[tuple[int, int], list[FundDay]] = defaultdict(list)
    for item in sorted_days:
        grouped[(item.day.year, item.day.month)].append(item)

    first_nav_by_year: dict[int, float] = {}
    for year in years:
        year_days = [d for d in sorted_days if d.day.year == year]
        if year_days:
            first_nav_by_year[year] = year_days[0].nav

    today = max((d.day for d in sorted_days), default=date.today())
    monthly: list[dict] = []
    for year in years:
        for month in range(1, 13):
            items = sorted(grouped.get((year, month), []), key=lambda d: d.day)
            if not items:
                continue
            first, last = items[0], items[-1]
            base_nav = first_nav_by_year.get(year, first.nav)
            monthly.append(
                {
                    "year": year,
                    "month": month,
                    "startDate": first.day.isoformat(),
                    "endDate": last.day.isoformat(),
                    "startNav": round(first.nav, 4),
                    "endNav": round(last.nav, 4),
                    "cumulativeNav": round(last.cumulative_nav, 4),
                    "pct": round((last.nav / first.nav - 1) * 100 if first.nav else 0.0, 4),
                    "cumulativePct": round((last.nav / base_nav - 1) * 100 if base_nav else 0.0, 4),
                    "tradeDays": len(items),
                    "partial": year == today.year and month == today.month,
                }
            )
    return monthly


def build_trend(days: list[FundDay]) -> list[dict]:
    return [
        {
            "date": d.day.isoformat(),
            "nav": round(d.nav, 4),
            "cumulativeNav": round(d.cumulative_nav, 4),
            "pct": round(d.pct_change, 4),
        }
        for d in sorted(days, key=lambda d: d.day)
    ]
