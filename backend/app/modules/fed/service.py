from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from typing import Any

import httpx

from app.modules.fed.models import FedEconomyOut, FedIndicator, FedPoint

FED_BASE = "https://www.federalreserve.gov"
PCE_URL = f"{FED_BASE}/json/pce.json"
UNEMPLOYMENT_URL = f"{FED_BASE}/json/unemployment.json"
GDP_URL = f"{FED_BASE}/json/gdp.json"
POLICY_URL = f"{FED_BASE}/aboutthefed/files/target-funds-2014-2024.csv"
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def fetch_economy_at_a_glance() -> FedEconomyOut:
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        policy_csv = client.get(POLICY_URL).raise_for_status().text
        pce_json = client.get(PCE_URL).raise_for_status().json()
        unemployment_json = client.get(UNEMPLOYMENT_URL).raise_for_status().json()
        gdp_json = client.get(GDP_URL).raise_for_status().json()

    indicators = [
        _policy_indicator(policy_csv),
        _bea_indicator(
            payload=pce_json,
            series_code="BPCERO",
            indicator_id="inflation",
            title="Inflation (PCE)",
            detail_title="Personal Consumption Expenditures Price Index: Percent Change from Year Earlier",
            card_title="Inflation (PCE)",
            description="Personal Consumption Expenditures Price Index",
            unit="Percent",
            chart_type="line",
            color="#005a9c",
            source="Bureau of Economic Analysis",
            source_url="https://www.bea.gov",
            page_url=f"{FED_BASE}/economy-at-a-glance-inflation-pce.htm",
            label_formatter=_month_label,
            date_formatter=_month_date,
            signed=False,
        ),
        _unemployment_indicator(unemployment_json),
        _bea_indicator(
            payload=gdp_json,
            series_code="A191RL",
            indicator_id="gdp",
            title="Gross Domestic Product (GDP)",
            detail_title="Real Gross Domestic Product (GDP): Percent Change from the Previous Quarter",
            card_title="Gross Domestic Product (GDP)",
            description="Real Gross Domestic Product",
            unit="Percent",
            chart_type="bar",
            color="#005a9c",
            source="Bureau of Economic Analysis",
            source_url="https://www.bea.gov",
            page_url=f"{FED_BASE}/economy-at-a-glance-gross-domestic-product.htm",
            label_formatter=_quarter_label,
            date_formatter=_quarter_date,
            signed=True,
        ),
    ]

    return FedEconomyOut(
        title="Economy at a Glance",
        updatedAt=date.today().isoformat(),
        indicators=indicators,
    )


def _policy_indicator(content: str) -> FedIndicator:
    rows = list(csv.reader(StringIO(content.strip())))
    dates, lower_values, upper_values = rows[:3]
    points = [
        FedPoint(
            date=_parse_policy_date(day).isoformat(),
            label=_friendly_full_date(_parse_policy_date(day).isoformat()),
            value=(float(lower) + float(upper)) / 2,
            lower=float(lower),
            upper=float(upper),
        )
        for day, lower, upper in zip(dates, lower_values, upper_values)
    ]
    latest = points[-1]
    latest_display = f"{latest.lower:.2f}% to {latest.upper:.2f}%"

    return FedIndicator(
        id="policy-rate",
        title="Policy Rate",
        detailTitle="Target Range for the Federal Funds Rate",
        cardTitle="Policy Rate",
        description="Federal Funds Rate Target Range",
        unit="Level (Percent)",
        chartType="range",
        color="#73894a",
        source="Federal Reserve",
        sourceUrl=FED_BASE,
        pageUrl=f"{FED_BASE}/economy-at-a-glance-policy-rate.htm",
        latestLabel=_friendly_full_date(latest.date),
        latestValue=latest.lower or latest.value,
        latestUpper=latest.upper,
        latestDisplay=latest_display,
        points=points,
    )


def _bea_indicator(
    *,
    payload: dict[str, Any],
    series_code: str,
    indicator_id: str,
    title: str,
    detail_title: str,
    card_title: str,
    description: str,
    unit: str,
    chart_type: str,
    color: str,
    source: str,
    source_url: str,
    page_url: str,
    label_formatter,
    date_formatter,
    signed: bool,
) -> FedIndicator:
    rows = payload["BEAAPI"]["Results"]["Data"]
    points = [
        FedPoint(
            date=date_formatter(row["TimePeriod"]),
            label=label_formatter(row["TimePeriod"]),
            value=float(row["DataValue"].replace(",", "")),
        )
        for row in rows
        if row.get("SeriesCode") == series_code and _is_number(row.get("DataValue"))
    ]
    points.sort(key=lambda point: point.date)
    latest = points[-1]
    prefix = "+" if signed and latest.value > 0 else ""

    return FedIndicator(
        id=indicator_id,
        title=title,
        detailTitle=detail_title,
        cardTitle=card_title,
        description=description,
        unit=unit,
        chartType=chart_type,
        color=color,
        source=source,
        sourceUrl=source_url,
        pageUrl=page_url,
        latestLabel=latest.label,
        latestValue=latest.value,
        latestDisplay=f"{prefix}{latest.value:.1f}%",
        points=points,
    )


def _unemployment_indicator(payload: dict[str, Any]) -> FedIndicator:
    rows = payload["Results"]["series"][0]["data"]
    points = [
        FedPoint(
            date=f"{row['year']}-{row['period'][1:]}-01",
            label=f"{row['periodName']} {row['year']}",
            value=float(row["value"]),
        )
        for row in rows
        if _is_number(row.get("value"))
    ]
    points.sort(key=lambda point: point.date)
    latest = points[-1]

    return FedIndicator(
        id="unemployment",
        title="Unemployment Rate",
        detailTitle="Civilian Unemployment Rate, Seasonally Adjusted",
        cardTitle="Unemployment Rate",
        description="Civilian Unemployment Rate",
        unit="Percent",
        chartType="line",
        color="#005a9c",
        source="U.S. Bureau of Labor Statistics",
        sourceUrl="https://www.bls.gov",
        pageUrl=f"{FED_BASE}/economy-at-a-glance-unemployment-rate.htm",
        latestLabel=latest.label,
        latestValue=latest.value,
        latestDisplay=f"{latest.value:.1f}%",
        points=points,
    )


def _is_number(value: str | None) -> bool:
    if value is None:
        return False
    try:
        float(value.replace(",", ""))
    except ValueError:
        return False
    return True


def _parse_policy_date(value: str) -> date:
    value = value.strip()
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    return datetime.strptime(value, "%m/%d/%Y").date()


def _month_date(value: str) -> str:
    year, month = value.split("M")
    return f"{year}-{int(month):02d}-01"


def _month_label(value: str) -> str:
    day = datetime.strptime(_month_date(value), "%Y-%m-%d")
    return f"{MONTH_NAMES[day.month - 1]} {day.year}"


def _quarter_date(value: str) -> str:
    year, quarter = value.split("Q")
    month = (int(quarter) - 1) * 3 + 1
    return f"{year}-{month:02d}-01"


def _quarter_label(value: str) -> str:
    year, quarter = value.split("Q")
    return f"Q{quarter} {year}"


def _friendly_full_date(value: str) -> str:
    day = datetime.strptime(value, "%Y-%m-%d")
    return f"{MONTH_NAMES[day.month - 1]} {day.day}, {day.year}"
