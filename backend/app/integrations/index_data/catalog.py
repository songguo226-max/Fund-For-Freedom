from __future__ import annotations

from datetime import date

from app.integrations.index_data.interface import IndexNotFound, IndexSpec


SUPPORTED_INDEXES: dict[str, IndexSpec] = {
    "sp500": IndexSpec(
        id="sp500",
        name="标普500指数",
        market="US",
        currency="USD",
        source_priority=("yfinance", "akshare"),
        ak_global_symbol="标普500指数",
        yfinance_symbol="^GSPC",
    ),
    "nasdaq100": IndexSpec(
        id="nasdaq100",
        name="纳斯达克100",
        market="US",
        currency="USD",
        source_priority=("yfinance", "akshare"),
        ak_global_symbol="纳斯达克100指数",
        yfinance_symbol="^NDX",
    ),
    "hang_seng": IndexSpec(
        id="hang_seng",
        name="香港恒生指数",
        market="HK",
        currency="HKD",
        source_priority=("yfinance", "akshare"),
        ak_global_symbol="恒生指数",
        yfinance_symbol="^HSI",
    ),
    "sse_composite": IndexSpec(
        id="sse_composite",
        name="上证指数",
        market="CN",
        currency="CNY",
        source_priority=("akshare", "yfinance"),
        ak_symbol="000001",
        ak_em_symbol="sh000001",
        ak_tx_symbol="sh000001",
        ak_sina_symbol="sh000001",
        yfinance_symbol="000001.SS",
    ),
    "csi300": IndexSpec(
        id="csi300",
        name="沪深300",
        market="CN",
        currency="CNY",
        source_priority=("akshare", "yfinance"),
        ak_symbol="000300",
        ak_em_symbol="sh000300",
        ak_tx_symbol="sh000300",
        ak_sina_symbol="sh000300",
        yfinance_symbol="000300.SS",
    ),
    "csi500": IndexSpec(
        id="csi500",
        name="中证500",
        market="CN",
        currency="CNY",
        source_priority=("akshare", "yfinance"),
        ak_symbol="000905",
        ak_em_symbol="csi000905",
        ak_tx_symbol="sz399905",
        ak_sina_symbol="sh000905",
        yfinance_symbol="000905.SS",
    ),
}

SUPPORTED_RANGES: tuple[str, ...] = ("5y", "3y", "1y", "6m", "3m", "1m", "all")


def list_index_specs() -> list[IndexSpec]:
    return list(SUPPORTED_INDEXES.values())


def get_index_spec(index_id: str) -> IndexSpec:
    try:
        return SUPPORTED_INDEXES[index_id]
    except KeyError as exc:
        raise IndexNotFound(f"Unknown index: {index_id}") from exc


def range_start(range_id: str, end: date) -> date:
    if range_id == "all":
        return date(1900, 1, 1)
    if range_id == "5y":
        return _add_years(end, -5)
    if range_id == "3y":
        return _add_years(end, -3)
    if range_id == "1y":
        return _add_years(end, -1)
    if range_id == "6m":
        return _add_months(end, -6)
    if range_id == "3m":
        return _add_months(end, -3)
    if range_id == "1m":
        return _add_months(end, -1)
    raise IndexNotFound(f"Unsupported range: {range_id}")


def _add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def _add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    day_of_month = min(day.day, _days_in_month(year, month))
    return date(year, month, day_of_month)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days
