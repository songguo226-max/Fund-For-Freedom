from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests


FUND_CODE = "000218"
FUND_NAME = "国泰黄金ETF联接A"
TODAY = date.today()
OUT_DIR = Path("output")


@dataclass(frozen=True)
class FundDay:
    day: date
    nav: float
    cumulative_nav: float
    pct_change: float


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


def display_range(today: date = TODAY) -> tuple[date, date]:
    current_month = date(today.year, today.month, 1)
    start = add_months(current_month, -3)
    return start, today


def fetch_fund_days(start: date, end: date) -> list[FundDay]:
    rows: list[dict[str, str]] = []
    page_index = 1
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://fundf10.eastmoney.com/",
        "User-Agent": "Mozilla/5.0",
    }

    while True:
        query = urlencode({"fundCode": FUND_CODE, "pageIndex": page_index, "pageSize": 20})
        url = f"https://api.fund.eastmoney.com/f10/lsjz?{query}"
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        payload = json.loads(response.text)

        if payload.get("ErrCode") != 0 or not payload.get("Data"):
            raise RuntimeError(f"接口返回异常：{payload}")

        page_rows = payload["Data"]["LSJZList"]
        rows.extend(page_rows)

        oldest = datetime.strptime(page_rows[-1]["FSRQ"], "%Y-%m-%d").date()
        newest = datetime.strptime(page_rows[0]["FSRQ"], "%Y-%m-%d").date()
        if oldest < start or newest < start:
            break
        page_index += 1

    days = []
    for row in rows:
        day = datetime.strptime(row["FSRQ"], "%Y-%m-%d").date()
        if start <= day <= end:
            days.append(
                FundDay(
                    day=day,
                    nav=float(row["DWJZ"]),
                    cumulative_nav=float(row["LJJZ"]),
                    pct_change=float(row["JZZZL"]),
                )
            )

    return sorted(days, key=lambda item: item.day)


def write_csv(days: list[FundDay], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["日期", "单位净值", "累计净值", "日涨跌幅(%)"])
        for item in days:
            writer.writerow(
                [
                    item.day.isoformat(),
                    f"{item.nav:.4f}",
                    f"{item.cumulative_nav:.4f}",
                    f"{item.pct_change:.2f}",
                ]
            )


def write_html(days: list[FundDay], path: Path, start: date, end: date) -> None:
    from final_calendar_renderer import write_final_calendar_html

    write_final_calendar_html(days, path, start, end, FUND_NAME, FUND_CODE)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    start, end = display_range()
    days = fetch_fund_days(start, end)
    if not days:
        raise RuntimeError("未获取到基金净值数据")

    latest = days[-1].day
    suffix = f"{start.isoformat()}_to_{latest.isoformat()}"
    write_csv(days, OUT_DIR / f"fund_{FUND_CODE}_{suffix}.csv")
    write_html(days, OUT_DIR / "fund_000218_calendar.html", start, latest)

    print(f"records={len(days)}")
    print(f"date_range={days[0].day.isoformat()}..{latest.isoformat()}")
    print(f"latest_nav={days[-1].nav:.4f}")
    print(f"latest_pct={days[-1].pct_change:+.2f}%")


if __name__ == "__main__":
    main()
