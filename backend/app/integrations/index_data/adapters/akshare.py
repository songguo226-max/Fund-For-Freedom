from __future__ import annotations

import contextlib
import io
from datetime import date
from importlib import import_module
from typing import Any

from app.integrations.index_data.interface import IndexDataError, IndexPoint, IndexSpec


class AkshareIndexProvider:
    name = "akshare"

    def get_history(self, spec: IndexSpec, start: date, end: date) -> list[IndexPoint]:
        if not any((spec.ak_symbol, spec.ak_em_symbol, spec.ak_tx_symbol, spec.ak_sina_symbol, spec.ak_global_symbol)):
            raise IndexDataError(f"AKShare symbol is not configured for {spec.id}")
        try:
            ak = import_module("akshare")
        except ImportError as exc:
            raise IndexDataError("AKShare is not installed") from exc

        rows = self._fetch_a_index(ak, spec, start, end)
        if not rows and spec.ak_global_symbol:
            rows = self._fetch_global_index(ak, spec, start, end)
        if not rows:
            raise IndexDataError(f"No AKShare data for {spec.id}")
        return rows

    def _fetch_a_index(self, ak: Any, spec: IndexSpec, start: date, end: date) -> list[IndexPoint]:
        start_text = start.strftime("%Y%m%d")
        end_text = end.strftime("%Y%m%d")
        errors: list[str] = []

        if start <= date(1900, 1, 1) and spec.ak_sina_symbol and hasattr(ak, "stock_zh_index_daily"):
            try:
                points = self._fetch_sina_index(ak, spec, start, end)
                if points:
                    return points
            except Exception as exc:  # pragma: no cover
                errors.append(str(exc))

        if spec.ak_tx_symbol and hasattr(ak, "stock_zh_index_daily_tx"):
            try:
                df = _quiet_call(
                    ak.stock_zh_index_daily_tx,
                    symbol=spec.ak_tx_symbol,
                    start_date=start_text,
                    end_date=end_text,
                )
                points = _points_from_records(_records(df), date_keys=("date", "日期"), close_keys=("close", "收盘"))
                if points:
                    return _filter_points(points, start, end)
            except Exception as exc:  # pragma: no cover - provider shape can drift
                errors.append(str(exc))

        if spec.ak_symbol and hasattr(ak, "index_zh_a_hist"):
            try:
                df = _quiet_call(
                    ak.index_zh_a_hist,
                    symbol=spec.ak_symbol,
                    period="daily",
                    start_date=start_text,
                    end_date=end_text,
                )
                points = _points_from_records(_records(df), date_keys=("日期", "date"), close_keys=("收盘", "close"))
                if points:
                    return _filter_points(points, start, end)
            except Exception as exc:  # pragma: no cover - provider shape can drift
                errors.append(str(exc))

        if spec.ak_em_symbol and hasattr(ak, "stock_zh_index_daily_em"):
            try:
                df = _quiet_call(
                    ak.stock_zh_index_daily_em,
                    symbol=spec.ak_em_symbol,
                    start_date=start_text,
                    end_date=end_text,
                )
                points = _points_from_records(_records(df), date_keys=("date", "日期"), close_keys=("close", "收盘"))
                if points:
                    return _filter_points(points, start, end)
            except Exception as exc:  # pragma: no cover
                errors.append(str(exc))

        if spec.ak_sina_symbol and hasattr(ak, "stock_zh_index_daily"):
            try:
                points = self._fetch_sina_index(ak, spec, start, end)
                if points:
                    return points
            except Exception as exc:  # pragma: no cover
                errors.append(str(exc))

        if errors and not spec.ak_global_symbol:
            raise IndexDataError("; ".join(errors))
        return []

    def _fetch_sina_index(self, ak: Any, spec: IndexSpec, start: date, end: date) -> list[IndexPoint]:
        df = _quiet_call(ak.stock_zh_index_daily, symbol=spec.ak_sina_symbol)
        points = _points_from_records(_records(df), date_keys=("date", "日期"), close_keys=("close", "收盘"))
        return _filter_points(points, start, end)

    def _fetch_global_index(self, ak: Any, spec: IndexSpec, start: date, end: date) -> list[IndexPoint]:
        if not hasattr(ak, "index_global_hist_em"):
            return []
        try:
            df = _quiet_call(ak.index_global_hist_em, symbol=spec.ak_global_symbol)
        except Exception as exc:  # pragma: no cover - provider/network failure
            raise IndexDataError(str(exc)) from exc
        points = _points_from_records(_records(df), date_keys=("日期", "date"), close_keys=("最新价", "close"))
        return _filter_points(points, start, end)


def _quiet_call(fn: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(**kwargs)


def _records(df: Any) -> list[dict]:
    if df is None:
        return []
    if hasattr(df, "to_dict"):
        return list(df.to_dict("records"))
    if isinstance(df, list):
        return [item for item in df if isinstance(item, dict)]
    return []


def _points_from_records(records: list[dict], *, date_keys: tuple[str, ...], close_keys: tuple[str, ...]) -> list[IndexPoint]:
    points: list[IndexPoint] = []
    for row in records:
        raw_day = _first_value(row, date_keys)
        raw_close = _first_value(row, close_keys)
        if raw_day in (None, "") or raw_close in (None, ""):
            continue
        try:
            points.append(IndexPoint(day=date.fromisoformat(str(raw_day)[:10]), close=float(raw_close)))
        except (TypeError, ValueError):
            continue
    return sorted(points, key=lambda item: item.day)


def _first_value(row: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _filter_points(points: list[IndexPoint], start: date, end: date) -> list[IndexPoint]:
    return [point for point in points if start <= point.day <= end]
