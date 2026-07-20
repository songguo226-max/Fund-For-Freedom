from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec


@dataclass(frozen=True)
class DataSourceEntry:
    id: str
    name: str
    status: str
    provider_name: str | None
    python_package: str | None
    install_command: str | None
    homepage: str
    repository: str | None
    license: str | None
    markets: tuple[str, ...]
    asset_classes: tuple[str, ...]
    data_types: tuple[str, ...]
    frequencies: tuple[str, ...]
    strengths: tuple[str, ...]
    limitations: tuple[str, ...]
    terms_note: str

    @property
    def package_installed(self) -> bool | None:
        if not self.python_package:
            return None
        return find_spec(self.python_package) is not None


DATA_SOURCES: tuple[DataSourceEntry, ...] = (
    DataSourceEntry(
        id="eastmoney",
        name="Eastmoney Fund APIs",
        status="active",
        provider_name="eastmoney",
        python_package=None,
        install_command=None,
        homepage="https://fund.eastmoney.com/",
        repository=None,
        license=None,
        markets=("CN",),
        asset_classes=("fund", "etf"),
        data_types=("fund_search", "fund_nav", "fund_metadata"),
        frequencies=("daily",),
        strengths=(
            "Already powers the current fund search and NAV history flow.",
            "Good first source for China mutual fund and ETF-linked fund pages.",
        ),
        limitations=(
            "Public web API, so field shape and anti-scraping behavior can change.",
            "Not a general stock or macro data adapter.",
        ),
        terms_note="Use only within the rights allowed by the public site and downstream data terms.",
    ),
    DataSourceEntry(
        id="morningstar",
        name="Morningstar China",
        status="stub",
        provider_name="morningstar",
        python_package=None,
        install_command=None,
        homepage="https://www.morningstar.cn/",
        repository=None,
        license=None,
        markets=("CN",),
        asset_classes=("fund",),
        data_types=("fund_metadata", "fund_nav"),
        frequencies=("daily",),
        strengths=(
            "Useful as a secondary fund metadata and NAV cross-check source.",
        ),
        limitations=(
            "Provider class exists, but parsing is not implemented yet.",
        ),
        terms_note="Check Morningstar China usage terms before automated collection.",
    ),
    DataSourceEntry(
        id="yfinance",
        name="yfinance",
        status="candidate",
        provider_name=None,
        python_package="yfinance",
        install_command="uv add yfinance",
        homepage="https://ranaroussi.github.io/yfinance/",
        repository="https://github.com/ranaroussi/yfinance",
        license="Apache-2.0",
        markets=("US", "global"),
        asset_classes=("stock", "etf", "index", "fund", "fx", "crypto"),
        data_types=(
            "ohlcv",
            "quote",
            "corporate_actions",
            "fundamentals",
            "news",
            "screening",
        ),
        frequencies=("intraday", "daily", "weekly", "monthly", "streaming"),
        strengths=(
            "Pythonic Yahoo Finance access with Ticker, Tickers, download, Search, Screener, and WebSocket APIs.",
            "Good low-friction source for US equities, ETFs, benchmarks, and quick research datasets.",
        ),
        limitations=(
            "Unofficial Yahoo Finance client; data is intended for personal research and educational use.",
            "Yahoo symbols and adjusted price semantics need normalization before mixing with fund NAV data.",
        ),
        terms_note="Yahoo Finance data rights are governed by Yahoo terms; yfinance states the API is intended for personal use.",
    ),
    DataSourceEntry(
        id="akshare",
        name="AKShare",
        status="candidate",
        provider_name=None,
        python_package="akshare",
        install_command="uv add akshare",
        homepage="https://akshare.akfamily.xyz/",
        repository="https://github.com/akfamily/akshare",
        license=None,
        markets=("CN", "US", "global"),
        asset_classes=(
            "stock",
            "fund",
            "etf",
            "index",
            "bond",
            "futures",
            "macro",
            "commodity",
        ),
        data_types=(
            "ohlcv",
            "quote",
            "fund_nav",
            "macro",
            "fundamentals",
            "industry",
            "calendar",
        ),
        frequencies=("daily", "intraday", "periodic"),
        strengths=(
            "Broad China-market coverage with one-line Python data functions.",
            "Especially promising for A-share, ETF, fund, macro, and exchange datasets.",
        ),
        limitations=(
            "Interfaces can be removed or changed because many upstream sites are outside AKShare control.",
            "Column names are source-specific and usually need Chinese-to-canonical field mapping.",
        ),
        terms_note="AKShare states data is for academic research/reference and asks users to pay attention to data risk.",
    ),
)


def list_data_sources(
    *,
    market: str | None = None,
    asset_class: str | None = None,
    status: str | None = None,
) -> list[DataSourceEntry]:
    entries = list(DATA_SOURCES)
    if market:
        normalized = market.casefold()
        entries = [entry for entry in entries if normalized in (m.casefold() for m in entry.markets)]
    if asset_class:
        normalized = asset_class.casefold()
        entries = [
            entry
            for entry in entries
            if normalized in (item.casefold() for item in entry.asset_classes)
        ]
    if status:
        normalized = status.casefold()
        entries = [entry for entry in entries if entry.status.casefold() == normalized]
    return entries


def get_data_source(source_id: str) -> DataSourceEntry:
    for entry in DATA_SOURCES:
        if entry.id == source_id:
            return entry
    raise KeyError(source_id)
