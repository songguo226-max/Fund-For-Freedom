from __future__ import annotations

import json
import logging
import re
from html import unescape
from datetime import date, datetime

import httpx

from app.integrations.fund_data.interface import FundDay, FundHit, FundMeta, FundNotFound, ProviderError

logger = logging.getLogger(__name__)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://fundf10.eastmoney.com/",
    "User-Agent": "Mozilla/5.0",
}

LSJZ_URL = "https://api.fund.eastmoney.com/f10/lsjz"
SEARCH_URL = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
FUND_PAGE_URL = "https://fund.eastmoney.com/{code}.html"


class EastmoneyProvider:
    """Primary fund data source backed by Eastmoney's public APIs."""

    name = "eastmoney"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(headers=HEADERS, timeout=20)

    # ---------- pure parsing (unit-testable, no network) ----------
    @staticmethod
    def _parse_lsjz(payload: dict) -> list[FundDay]:
        if payload.get("ErrCode") != 0:
            raise ProviderError(f"接口返回异常：{payload.get('ErrMsg')}")
        data = payload.get("Data") or {}
        rows = data.get("LSJZList", [])
        days: list[FundDay] = []
        for row in rows:
            if not row.get("DWJZ") or not row.get("LJJZ"):
                continue
            days.append(
                FundDay(
                    day=datetime.strptime(row["FSRQ"], "%Y-%m-%d").date(),
                    nav=float(row["DWJZ"]),
                    cumulative_nav=float(row["LJJZ"]),
                    pct_change=float(row.get("JZZZL") or 0),
                )
            )
        return sorted(days, key=lambda d: d.day)

    @staticmethod
    def _parse_search(text: str) -> list[FundHit]:
        data = json.loads(text)
        if data.get("ErrCode") != 0:
            raise ProviderError(f"接口返回异常：{data.get('ErrMsg')}")
        rows = data.get("Datas", [])
        hits: list[FundHit] = []
        for row in rows:
            code = row.get("CODE")
            name = row.get("NAME")
            if not code or not name:
                continue
            hits.append(
                FundHit(
                    code=str(code),
                    name=str(name),
                    type=str(row.get("CATEGORYDESC") or ""),
                )
            )
        return hits

    # ---------- network ----------
    @staticmethod
    def _parse_detail_type(text: str) -> str:
        match = re.search(r"类型：\s*<a[^>]*>\s*([^<|]+?)\s*</a>", text)
        if not match:
            match = re.search(r"类型：\s*([^<|\s]+)", text)
        return unescape(match.group(1)).strip() if match else ""

    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

    def search(self, q: str) -> list[FundHit]:
        resp = self._get(SEARCH_URL, {"m": 1, "key": q})
        return self._parse_search(resp.content.decode("utf-8"))

    def get_nav_history(self, code: str, start: date, end: date) -> list[FundDay]:
        rows: list[FundDay] = []
        page = 1
        while True:
            resp = self._get(LSJZ_URL, {"fundCode": code, "pageIndex": page, "pageSize": 100})
            payload = json.loads(resp.text)
            page_days = self._parse_lsjz(payload)
            if not page_days:
                # end of data (server returns an empty LSJZList past the last page)
                break
            rows.extend(page_days)
            if min(d.day for d in page_days) < start:
                # already reached rows earlier than the requested window
                break
            page += 1
        if not rows:
            raise FundNotFound(f"基金 {code} 无净值数据")
        filtered = [d for d in rows if start <= d.day <= end]
        return sorted(filtered, key=lambda d: d.day)

    def get_meta(self, code: str) -> FundMeta:
        resp = self._get(LSJZ_URL, {"fundCode": code, "pageIndex": 1, "pageSize": 1})
        payload = json.loads(resp.text)
        days = self._parse_lsjz(payload)
        if not days:
            raise FundNotFound(f"基金 {code} 无净值数据")
        latest = days[-1]
        hit = self._resolve_hit(code)
        detail_type = self._resolve_detail_type(code)
        return FundMeta(
            code=code,
            name=hit.name,
            latest_date=latest.day,
            latest_nav=latest.nav,
            latest_cumulative_nav=latest.cumulative_nav,
            latest_pct=latest.pct_change,
            type=detail_type or hit.type,
        )

    def _resolve_hit(self, code: str) -> FundHit:
        """`lsjz`'s Data has no fund name/type fields, so resolve them via
        the search endpoint, matching the hit whose CODE equals the requested
        code exactly. Falls back to the code itself if no exact match."""
        try:
            hits = self.search(code)
        except ProviderError:
            logger.warning(
                "Failed to resolve fund metadata for code %s via search; "
                "falling back to using the code as the name",
                code,
                exc_info=True,
            )
            return FundHit(code=code, name=code, type="")
        for hit in hits:
            if hit.code == code:
                return hit
        return FundHit(code=code, name=code, type="")

    def _resolve_detail_type(self, code: str) -> str:
        try:
            resp = self._get(FUND_PAGE_URL.format(code=code))
        except ProviderError:
            logger.warning(
                "Failed to resolve fund detail type for code %s via fund page; "
                "falling back to search category",
                code,
                exc_info=True,
            )
            return ""
        return self._parse_detail_type(resp.text)
