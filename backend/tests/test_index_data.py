from __future__ import annotations

from datetime import date

import pytest

from app.integrations.index_data.catalog import get_index_spec, range_start
from app.integrations.index_data.adapters.akshare import AkshareIndexProvider
from app.integrations.index_data.compute import build_nav_trend
from app.integrations.index_data.interface import IndexDataError, IndexPoint
from app.integrations.index_data.registry import IndexProviderRegistry, call_index_provider


def test_range_start_uses_calendar_boundaries() -> None:
    end = date(2026, 7, 20)

    assert range_start("5y", end) == date(2021, 7, 20)
    assert range_start("3y", end) == date(2023, 7, 20)
    assert range_start("1y", end) == date(2025, 7, 20)
    assert range_start("6m", end) == date(2026, 1, 20)
    assert range_start("3m", end) == date(2026, 4, 20)
    assert range_start("1m", end) == date(2026, 6, 20)
    assert range_start("all", end) == date(1900, 1, 1)


def test_build_nav_trend_normalizes_against_first_close() -> None:
    points = [
        IndexPoint(day=date(2026, 1, 3), close=121),
        IndexPoint(day=date(2026, 1, 1), close=100),
        IndexPoint(day=date(2026, 1, 2), close=110),
    ]

    trend = build_nav_trend(points)

    assert [item["date"] for item in trend] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert trend[0]["nav"] == 1
    assert trend[1]["nav"] == 1.1
    assert trend[2]["nav"] == 1.21
    assert trend[2]["cumulativePct"] == 21
    assert trend[2]["pct"] == 10


class _FailingProvider:
    name = "akshare"

    def get_history(self, *_):
        raise IndexDataError("temporary failure")


class _WorkingProvider:
    name = "yfinance"

    def get_history(self, *_):
        return [IndexPoint(day=date(2026, 1, 1), close=100)]


def test_call_index_provider_falls_back_by_index_priority() -> None:
    registry = IndexProviderRegistry()
    registry.register(_FailingProvider())
    registry.register(_WorkingProvider())
    spec = get_index_spec("sp500")

    points = call_index_provider(registry, spec, None, lambda provider: provider.get_history(spec, date(2026, 1, 1), date(2026, 1, 2)))

    assert points == [IndexPoint(day=date(2026, 1, 1), close=100)]


def test_call_index_provider_respects_explicit_source() -> None:
    registry = IndexProviderRegistry()
    registry.register(_FailingProvider())
    registry.register(_WorkingProvider())
    spec = get_index_spec("sp500")

    with pytest.raises(IndexDataError, match="temporary failure"):
        call_index_provider(
            registry,
            spec,
            "akshare",
            lambda provider: provider.get_history(spec, date(2026, 1, 1), date(2026, 1, 2)),
        )


def test_akshare_global_errors_are_wrapped_for_fallback() -> None:
    class _FakeAk:
        @staticmethod
        def index_global_hist_em(symbol):
            raise RuntimeError(f"upstream failed: {symbol}")

    provider = AkshareIndexProvider()
    spec = get_index_spec("hang_seng")

    with pytest.raises(IndexDataError, match="upstream failed"):
        provider._fetch_global_index(_FakeAk(), spec, date(2026, 1, 1), date(2026, 1, 2))
