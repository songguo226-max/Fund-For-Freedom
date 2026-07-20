from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
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


@dataclass(frozen=True)
class MonthlyReturn:
    year: int
    month: int
    start_day: date
    end_day: date
    start_nav: float
    end_nav: float
    cumulative_nav: float
    pct_change: float
    cumulative_pct: float
    trade_days: int
    is_partial: bool


def month_key(day: date) -> tuple[int, int]:
    return day.year, day.month


def fetch_fund_days(start: date, end: date) -> list[FundDay]:
    rows: list[dict[str, str]] = []
    page_index = 1
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://fundf10.eastmoney.com/",
        "User-Agent": "Mozilla/5.0",
    }

    while True:
        query = urlencode({"fundCode": FUND_CODE, "pageIndex": page_index, "pageSize": 100})
        url = f"https://api.fund.eastmoney.com/f10/lsjz?{query}"
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        payload = json.loads(response.text)

        if payload.get("ErrCode") != 0 or not payload.get("Data"):
            raise RuntimeError(f"接口返回异常：{payload}")

        page_rows = payload["Data"].get("LSJZList", [])
        if not page_rows:
            break

        rows.extend(page_rows)
        oldest = datetime.strptime(page_rows[-1]["FSRQ"], "%Y-%m-%d").date()
        if oldest < start:
            break
        page_index += 1

    days: list[FundDay] = []
    for row in rows:
        day = datetime.strptime(row["FSRQ"], "%Y-%m-%d").date()
        if start <= day <= end and row.get("DWJZ") and row.get("LJJZ"):
            pct_text = row.get("JZZZL") or "0"
            days.append(
                FundDay(
                    day=day,
                    nav=float(row["DWJZ"]),
                    cumulative_nav=float(row["LJJZ"]),
                    pct_change=float(pct_text),
                )
            )

    return sorted(days, key=lambda item: item.day)


def build_monthly_returns(days: list[FundDay], years: list[int], today: date = TODAY) -> list[MonthlyReturn]:
    grouped: dict[tuple[int, int], list[FundDay]] = defaultdict(list)
    for item in days:
        grouped[month_key(item.day)].append(item)

    first_nav_by_year: dict[int, float] = {}
    for year in years:
        year_days = [item for item in days if item.day.year == year]
        if year_days:
            first_nav_by_year[year] = year_days[0].nav

    monthly: list[MonthlyReturn] = []
    for year in years:
        for month in range(1, 13):
            items = sorted(grouped.get((year, month), []), key=lambda item: item.day)
            if not items:
                continue

            first = items[0]
            last = items[-1]
            base_nav = first_nav_by_year.get(year, first.nav)
            monthly.append(
                MonthlyReturn(
                    year=year,
                    month=month,
                    start_day=first.day,
                    end_day=last.day,
                    start_nav=first.nav,
                    end_nav=last.nav,
                    cumulative_nav=last.cumulative_nav,
                    pct_change=(last.nav / first.nav - 1) * 100 if first.nav else 0.0,
                    cumulative_pct=(last.nav / base_nav - 1) * 100 if base_nav else 0.0,
                    trade_days=len(items),
                    is_partial=year == today.year and month == today.month,
                )
            )
    return monthly


def previous_years(today: date = TODAY) -> list[int]:
    return [today.year - 3, today.year - 2, today.year - 1]


def data_start(today: date = TODAY) -> date:
    return date(today.year - 3, 1, 1)


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def pct_state(value: float) -> str:
    if value > 0:
        return "rise"
    if value < 0:
        return "fall"
    return "flat"


def monthly_to_dict(item: MonthlyReturn) -> dict[str, int | float | str | bool]:
    return {
        "year": item.year,
        "month": item.month,
        "startDate": item.start_day.isoformat(),
        "endDate": item.end_day.isoformat(),
        "startNav": round(item.start_nav, 4),
        "endNav": round(item.end_nav, 4),
        "cumulativeNav": round(item.cumulative_nav, 4),
        "pct": round(item.pct_change, 4),
        "cumulativePct": round(item.cumulative_pct, 4),
        "tradeDays": item.trade_days,
        "partial": item.is_partial,
    }


def chart_payload(monthly: list[MonthlyReturn], today: date = TODAY) -> dict:
    prev_years = previous_years(today)
    by_year_month = {(item.year, item.month): item for item in monthly}
    previous_series = []
    for year in prev_years:
        previous_series.append(
            {
                "year": year,
                "months": [
                    monthly_to_dict(by_year_month[(year, month)]) if (year, month) in by_year_month else None
                    for month in range(1, 13)
                ],
            }
        )

    current_items = [
        monthly_to_dict(item)
        for item in monthly
        if item.year == today.year and item.end_day <= today
    ]

    latest_item = max(monthly, key=lambda item: item.end_day)
    return {
        "fundName": FUND_NAME,
        "fundCode": FUND_CODE,
        "generatedAt": today.isoformat(),
        "latestDate": latest_item.end_day.isoformat(),
        "previousYears": prev_years,
        "previousSeries": previous_series,
        "currentYear": today.year,
        "currentMonths": current_items,
    }


def write_csv(monthly: list[MonthlyReturn], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "年份",
                "月份",
                "月初日期",
                "月末日期",
                "月初单位净值",
                "月末单位净值",
                "月末累计净值",
                "月涨跌幅(%)",
                "年内累计涨跌幅(%)",
                "交易日数量",
                "是否未完整月份",
            ]
        )
        for item in monthly:
            writer.writerow(
                [
                    item.year,
                    item.month,
                    item.start_day.isoformat(),
                    item.end_day.isoformat(),
                    f"{item.start_nav:.4f}",
                    f"{item.end_nav:.4f}",
                    f"{item.cumulative_nav:.4f}",
                    f"{item.pct_change:.2f}",
                    f"{item.cumulative_pct:.2f}",
                    item.trade_days,
                    "是" if item.is_partial else "否",
                ]
            )


def heatmap_level(value: float, scale: float) -> int:
    if abs(value) < 0.005 or scale <= 0:
        return 0
    return max(1, min(5, math.ceil(abs(value) / scale * 5)))


def render_heatmap_cell(item: dict | None, year: int, month: int, scale: float) -> str:
    if item is None:
        return '<div class="heat-cell empty" aria-label="暂无数据">—</div>'

    value = float(item["pct"])
    state = "rise" if value > 0 else "fall" if value < 0 else "flat"
    level = heatmap_level(value, scale)
    partial = bool(item.get("partial"))
    partial_class = " partial" if partial else ""
    suffix = "*" if partial else ""
    label = f"{year}年{month}月"
    class_name = f"heat-cell has-value {state} level-{level}{partial_class}"
    partial_attr = "true" if partial else "false"
    return f"""
      <button class="{class_name}"
              type="button"
              data-label="{html.escape(label)}"
              data-pct="{value:.4f}"
              data-cumulative-pct="{float(item["cumulativePct"]):.4f}"
              data-start-nav="{float(item["startNav"]):.4f}"
              data-end-nav="{float(item["endNav"]):.4f}"
              data-trade-days="{int(item["tradeDays"])}"
              data-partial="{partial_attr}">
        {value:+.2f}%{suffix}
      </button>
    """


def render_monthly_heatmap(payload: dict) -> str:
    years = list(payload["previousYears"]) + [payload["currentYear"]]
    rows_by_year: dict[int, dict[int, dict]] = {}
    all_values: list[float] = []

    for series in payload["previousSeries"]:
        year = int(series["year"])
        rows_by_year[year] = {}
        for index, item in enumerate(series["months"], start=1):
            if item is not None:
                rows_by_year[year][index] = item
                all_values.append(float(item["pct"]))

    current_year = int(payload["currentYear"])
    rows_by_year[current_year] = {}
    for item in payload["currentMonths"]:
        rows_by_year[current_year][int(item["month"])] = item
        all_values.append(float(item["pct"]))

    max_abs = max((abs(value) for value in all_values), default=1.0)
    scale = max(3, math.ceil(max_abs / 3) * 3)
    month_headers = "".join(f'<div class="heat-month">{month}月</div>' for month in range(1, 13))
    body_rows: list[str] = []

    for year in years:
        cells = "".join(
            render_heatmap_cell(rows_by_year.get(int(year), {}).get(month), int(year), month, scale)
            for month in range(1, 13)
        )
        body_rows.append(f'<div class="heat-year">{year}年</div>{cells}')

    return f"""
      <div class="heatmap-shell">
        <div class="heatmap-grid" role="grid" aria-label="基金月度涨跌幅热力图">
          <div class="heat-corner" aria-hidden="true"></div>
          {month_headers}
          {"".join(body_rows)}
        </div>
      </div>
      <div class="heat-scale" aria-label="热力图色阶">
        <div class="heat-gradient"></div>
        <div class="heat-scale-labels">
          <span>-{scale:.0f}%</span>
          <span>-{scale / 2:.0f}%</span>
          <span>+0%</span>
          <span>+{scale / 2:.0f}%</span>
          <span>+{scale:.0f}%</span>
        </div>
        <div class="heat-scale-title">月涨跌幅</div>
      </div>
      <p class="heat-note">* 表示该月份尚未完整；“—”表示暂无数据。色阶按全表最大绝对涨跌幅对称设置，避免视觉误导。</p>
    """


def render_html(payload: dict) -> str:
    latest_month = payload["currentMonths"][-1] if payload["currentMonths"] else None
    latest_pct = latest_month["pct"] if latest_month else 0
    latest_nav = latest_month["endNav"] if latest_month else 0
    prev_year_text = "、".join(str(year) for year in payload["previousYears"])
    current_month_count = len(payload["currentMonths"])
    heatmap_html = render_monthly_heatmap(payload)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(FUND_NAME)} 月度涨跌幅图表</title>
<style>
  :root {{
    color-scheme: light;
    --bg: oklch(96.5% 0.006 250);
    --surface: oklch(99.1% 0.004 250);
    --surface-soft: oklch(97.4% 0.006 250);
    --line: oklch(89.6% 0.012 250);
    --line-strong: oklch(82.4% 0.018 250);
    --text: oklch(24% 0.018 250);
    --muted: oklch(48% 0.022 250);
    --muted-2: oklch(63% 0.018 250);
    --rise: oklch(49% 0.17 24);
    --rise-soft: oklch(95.8% 0.028 24);
    --fall: oklch(46% 0.12 172);
    --fall-soft: oklch(94.6% 0.034 172);
    --accent: oklch(45% 0.13 255);
    --accent-soft: oklch(94.6% 0.026 255);
    --gold: oklch(63% 0.11 82);
    --shadow: 0 12px 30px rgba(30, 39, 52, 0.07);
    --radius-lg: 20px;
    --radius-md: 14px;
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-variant-numeric: tabular-nums;
    line-height: 1.45;
  }}
  .page {{
    width: min(1440px, 100%);
    margin: 0 auto;
    padding: 34px 30px 56px;
  }}
  .hero {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
    gap: 18px;
    margin-bottom: 18px;
  }}
  .panel,
  .metric,
  .chart-card,
  .note {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow);
  }}
  .panel {{
    padding: 26px 28px;
  }}
  .eyebrow {{
    display: inline-flex;
    margin: 0 0 13px;
    padding: 5px 10px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-soft);
    color: var(--muted);
    font-size: 12px;
    font-weight: 760;
  }}
  h1 {{
    margin: 0;
    font-size: 38px;
    font-weight: 850;
    line-height: 1.12;
    letter-spacing: 0;
  }}
  .hero p {{
    max-width: 76ch;
    margin: 14px 0 0;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.75;
  }}
  .metric {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 24px;
  }}
  .label {{
    color: var(--muted);
    font-size: 12px;
    font-weight: 760;
  }}
  .metric-date {{
    margin-top: 5px;
    font-size: 20px;
    font-weight: 820;
  }}
  .metric-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 16px;
    margin-top: 22px;
  }}
  .metric-row strong {{
    display: block;
    margin-top: 6px;
    font-size: 34px;
    font-weight: 880;
    line-height: 1;
  }}
  .metric-row b {{
    display: block;
    margin-top: 4px;
    font-size: 23px;
    font-weight: 820;
    text-align: right;
  }}
  .overview {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }}
  .overview .metric {{
    min-height: 112px;
    padding: 17px 18px;
    box-shadow: 0 8px 22px rgba(30, 39, 52, 0.045);
  }}
  .overview strong {{
    display: block;
    margin-top: 10px;
    font-size: 23px;
    font-weight: 850;
    line-height: 1.15;
  }}
  .overview small {{
    display: block;
    margin-top: 8px;
    color: var(--muted-2);
    font-size: 12px;
  }}
  .chart-grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
  }}
  .chart-card {{
    position: relative;
    overflow: hidden;
    padding: 24px 24px 20px;
  }}
  .chart-head {{
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: flex-start;
    margin-bottom: 16px;
  }}
  .chart-title h2 {{
    margin: 0;
    font-size: 22px;
    font-weight: 850;
    line-height: 1.15;
  }}
  .chart-title p {{
    margin: 7px 0 0;
    color: var(--muted);
    font-size: 13px;
  }}
  .heatmap-card {{
    padding: 30px 34px 26px;
  }}
  .heatmap-card .chart-head {{
    margin-bottom: 28px;
  }}
  .heatmap-card .chart-title h2 {{
    font-size: 30px;
    letter-spacing: 0;
  }}
  .heatmap-card .chart-title p {{
    margin-top: 8px;
    color: var(--muted);
    font-size: 15px;
  }}
  .heatmap-shell {{
    overflow-x: auto;
    padding: 2px 0 4px;
  }}
  .heatmap-grid {{
    display: grid;
    grid-template-columns: 88px repeat(12, minmax(88px, 1fr));
    gap: 4px;
    min-width: 1180px;
    align-items: stretch;
  }}
  .heat-corner,
  .heat-month {{
    min-height: 30px;
  }}
  .heat-month {{
    display: grid;
    place-items: center;
    color: var(--text);
    font-size: 15px;
    font-weight: 760;
  }}
  .heat-year {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 12px;
    color: var(--text);
    font-size: 18px;
    font-weight: 850;
    white-space: nowrap;
  }}
  .heat-cell {{
    display: grid;
    place-items: center;
    min-height: 60px;
    border: 1px solid rgba(253, 253, 252, 0.82);
    border-radius: 4px;
    background: oklch(96.7% 0.006 250);
    color: #334155;
    font: inherit;
    font-size: 15px;
    font-weight: 780;
    letter-spacing: 0;
    text-align: center;
  }}
  button.heat-cell {{
    cursor: default;
    transition: box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease;
  }}
  button.heat-cell:hover,
  button.heat-cell:focus-visible {{
    z-index: 2;
    border-color: rgba(47, 57, 74, 0.34);
    box-shadow: 0 10px 22px rgba(30, 39, 52, 0.12);
    outline: none;
    transform: translateY(-1px);
  }}
  .heat-cell.empty {{
    color: #98a4b3;
    background: oklch(95.2% 0.006 250);
  }}
  .heat-cell.partial {{
    outline: 2px dashed #667085;
    outline-offset: -6px;
  }}
  .heat-cell.rise.level-1 {{ background: oklch(97.2% 0.012 24); color: #374151; }}
  .heat-cell.rise.level-2 {{ background: oklch(94.8% 0.032 24); color: #374151; }}
  .heat-cell.rise.level-3 {{ background: oklch(90.4% 0.063 24); color: #263244; }}
  .heat-cell.rise.level-4 {{ background: oklch(82.5% 0.105 24); color: #fdfdfc; }}
  .heat-cell.rise.level-5 {{ background: oklch(58.5% 0.19 24); color: #fdfdfc; }}
  .heat-cell.fall.level-1 {{ background: oklch(96.4% 0.012 172); color: #374151; }}
  .heat-cell.fall.level-2 {{ background: oklch(92.6% 0.033 172); color: #374151; }}
  .heat-cell.fall.level-3 {{ background: oklch(84.8% 0.061 172); color: #263244; }}
  .heat-cell.fall.level-4 {{ background: oklch(72.5% 0.095 172); color: #fdfdfc; }}
  .heat-cell.fall.level-5 {{ background: oklch(54% 0.12 172); color: #fdfdfc; }}
  .heat-cell.flat {{ background: oklch(96% 0.004 250); color: var(--muted); }}
  .heat-scale {{
    width: min(760px, 72%);
    margin: 28px auto 0;
  }}
  .heat-gradient {{
    height: 22px;
    border-radius: 2px;
    background: linear-gradient(90deg,
      oklch(54% 0.12 172),
      oklch(84.8% 0.061 172),
      oklch(96.4% 0.006 250),
      oklch(90.4% 0.063 24),
      oklch(58.5% 0.19 24)
    );
  }}
  .heat-scale-labels {{
    display: flex;
    justify-content: space-between;
    margin-top: 7px;
    color: var(--text);
    font-size: 13px;
    font-weight: 720;
  }}
  .heat-scale-title {{
    margin-top: 5px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 760;
    text-align: center;
  }}
  .heat-note {{
    margin: 22px 0 0;
    color: var(--muted);
    font-size: 13px;
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px 14px;
    color: var(--muted);
    font-size: 12px;
    font-weight: 680;
  }}
  .legend span {{
    display: inline-flex;
    gap: 7px;
    align-items: center;
    white-space: nowrap;
  }}
  .legend i {{
    width: 20px;
    height: 3px;
    border-radius: 999px;
    background: currentColor;
  }}
  .legend .bar-key {{
    width: 13px;
    height: 13px;
    border-radius: 4px;
    border: 1px solid currentColor;
    background: var(--rise-soft);
  }}
  .canvas-wrap {{
    position: relative;
    width: 100%;
    height: 450px;
  }}
  .canvas-wrap.combo-wrap {{
    height: 520px;
  }}
  canvas {{
    display: block;
    width: 100%;
    height: 100%;
  }}
  .tooltip {{
    position: fixed;
    z-index: 20;
    width: 210px;
    padding: 10px 12px;
    border: 1px solid rgba(210, 216, 224, 0.92);
    border-radius: 11px;
    background: rgba(253, 253, 252, 0.98);
    box-shadow: 0 14px 30px rgba(25, 34, 45, 0.16);
    opacity: 0;
    pointer-events: none;
    transform: translateY(3px);
    transition: opacity 160ms ease, transform 160ms ease;
  }}
  .tooltip.visible {{
    opacity: 1;
    transform: translateY(0);
  }}
  .tooltip strong {{
    display: block;
    margin-bottom: 7px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--line);
    font-size: 13px;
    font-weight: 850;
  }}
  .tooltip dl {{
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 5px 14px;
    margin: 0;
    font-size: 12px;
  }}
  .tooltip dt {{
    color: var(--muted);
    white-space: nowrap;
  }}
  .tooltip dd {{
    margin: 0;
    font-weight: 820;
    text-align: right;
    white-space: nowrap;
  }}
  .rise {{ color: var(--rise); }}
  .fall {{ color: var(--fall); }}
  .flat {{ color: var(--muted); }}
  .note {{
    margin-top: 18px;
    padding: 14px 16px;
    color: var(--muted);
    font-size: 13px;
    box-shadow: none;
  }}

  @media (max-width: 980px) {{
    .page {{ padding: 24px 18px 42px; }}
    .hero,
    .overview {{ grid-template-columns: 1fr; }}
    .chart-head {{ flex-direction: column; }}
    .legend {{ justify-content: flex-start; }}
    .canvas-wrap {{ height: 380px; }}
    .canvas-wrap.combo-wrap {{ height: 470px; }}
    .heatmap-card {{ padding: 22px 18px 20px; }}
    .heatmap-card .chart-title h2 {{ font-size: 25px; }}
    .heat-scale {{ width: min(820px, 92%); }}
  }}
  @media (max-width: 560px) {{
    .page {{ padding: 18px 10px 34px; }}
    .panel,
    .metric,
    .chart-card {{ border-radius: 16px; padding: 16px; }}
    h1 {{ font-size: 28px; }}
    .metric-row {{ align-items: flex-start; flex-direction: column; }}
    .metric-row b {{ text-align: left; }}
    .overview strong {{ font-size: 20px; }}
    .canvas-wrap {{ height: 340px; }}
    .canvas-wrap.combo-wrap {{ height: 420px; }}
    .heatmap-card .chart-title h2 {{ font-size: 22px; }}
    .heatmap-grid {{ min-width: 980px; grid-template-columns: 76px repeat(12, 74px); }}
    .heat-cell {{ min-height: 54px; font-size: 13px; }}
    .heat-year {{ font-size: 15px; }}
    .heat-scale {{ width: 100%; }}
  }}
</style>
</head>
<body>
<main class="page">
  <header class="hero">
    <section class="panel">
      <p class="eyebrow">基金月度表现</p>
      <h1>月涨跌幅对比</h1>
      <p>{html.escape(FUND_NAME)} ({FUND_CODE})，前三年按 1 到 12 月绘制三条月涨跌幅折线。今年已公布净值的月份单独绘制为双折线图，两条线分别表示月涨跌幅和年内累计涨跌幅。</p>
    </section>
    <aside class="metric">
      <div>
        <div class="label">最新月度数据</div>
        <div class="metric-date">{payload["latestDate"]}</div>
      </div>
      <div class="metric-row">
        <div>
          <div class="label">最新月涨跌幅</div>
          <strong class="{pct_state(float(latest_pct))}">{fmt_pct(float(latest_pct))}</strong>
        </div>
        <div>
          <div class="label">最新单位净值</div>
          <b>{float(latest_nav):.4f}</b>
        </div>
      </div>
    </aside>
  </header>

  <section class="overview" aria-label="数据概览">
    <div class="metric">
      <span class="label">前三年</span>
      <strong>{html.escape(prev_year_text)}</strong>
      <small>每年 12 个月横向对比</small>
    </div>
    <div class="metric">
      <span class="label">今年已公布月份</span>
      <strong>{current_month_count} 个月</strong>
      <small>{payload["currentYear"]} 年截至 {payload["latestDate"]}</small>
    </div>
    <div class="metric">
      <span class="label">月涨跌幅口径</span>
      <strong>月末 / 月初 - 1</strong>
      <small>使用该月首个与最后一个已公布净值</small>
    </div>
    <div class="metric">
      <span class="label">颜色规则</span>
      <strong><span class="rise">红涨</span> <span class="fall">绿跌</span></strong>
      <small>符合国内基金行情习惯</small>
    </div>
  </section>

  <section class="chart-grid">
    <article class="chart-card heatmap-card">
      <div class="chart-head">
        <div class="chart-title">
          <h2>基金 {FUND_CODE} 月度涨跌幅热力图</h2>
          <p>横向比较同一月份的不同年份；红色代表上涨，绿色代表下跌，颜色越深表示幅度越大。</p>
        </div>
      </div>
      {heatmap_html}
    </article>

    <article class="chart-card">
      <div class="chart-head">
        <div class="chart-title">
          <h2>{payload["currentYear"]} 年分层组合图</h2>
          <p>上层用柱状图显示月涨跌幅，下层用折线显示年内累计涨跌幅，共用月份刻度。</p>
        </div>
        <div class="legend">
          <span style="color: var(--rise);"><i class="bar-key"></i>月涨跌幅</span>
          <span style="color: var(--accent);"><i></i>年内累计涨跌幅</span>
        </div>
      </div>
      <div class="canvas-wrap combo-wrap">
        <canvas id="comboChart" aria-label="今年月涨跌幅柱状图与年内累计涨跌幅折线图"></canvas>
      </div>
    </article>
  </section>

  <p class="note">数据来自天天基金/东方财富公开历史净值接口。当前月份若尚未结束，图中按已公布的最新净值计算，页面不会虚构未公布月份的数据。</p>
</main>

<div class="tooltip" id="tooltip"></div>
<script type="application/json" id="chart-data">{data_json}</script>
<script>
  const payload = JSON.parse(document.getElementById('chart-data').textContent);
  const tooltip = document.getElementById('tooltip');
  const chartHits = new WeakMap();

  function cssVar(name) {{
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }}

  function formatPct(value) {{
    return `${{Number(value).toFixed(2).replace(/^(-?)/, match => match === '-' ? '-' : '+')}}%`;
  }}

  function money(value) {{
    return Number(value).toFixed(4);
  }}

  function resizeCanvas(canvas) {{
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * ratio));
    canvas.height = Math.max(1, Math.round(rect.height * ratio));
    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return {{ ctx, width: rect.width, height: rect.height }};
  }}

  function yDomain(values) {{
    const valid = values.filter(value => Number.isFinite(value));
    const minValue = Math.min(...valid);
    const maxValue = Math.max(...valid);
    const magnitude = Math.max(1, Math.abs(minValue), Math.abs(maxValue));
    const padding = Math.max(0.8, magnitude * 0.18);
    if (minValue >= 0) return [0, maxValue + padding];
    if (maxValue <= 0) return [minValue - padding, 0];
    return [minValue - padding, maxValue + padding];
  }}

  function barYDomain(values) {{
    const valid = values.filter(value => Number.isFinite(value));
    const minValue = Math.min(0, ...valid);
    const maxValue = Math.max(0, ...valid);
    const magnitude = Math.max(1, Math.abs(minValue), Math.abs(maxValue));
    const padding = Math.max(1.8, magnitude * 0.32);
    return [minValue - padding, maxValue + padding];
  }}

  function niceTicks(min, max, count = 6) {{
    const span = max - min || 1;
    const raw = span / count;
    const power = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 5, 10].find(item => item * power >= raw) * power;
    const first = Math.ceil(min / step) * step;
    const ticks = [];
    for (let value = first; value <= max + step * 0.5; value += step) {{
      ticks.push(Number(value.toFixed(6)));
    }}
    return ticks;
  }}

  function drawComboChart() {{
    const canvas = document.getElementById('comboChart');
    const {{ ctx, width, height }} = resizeCanvas(canvas);
    const items = payload.currentMonths;
    const labels = items.map(item => item.month);
    const outer = {{ left: 64, right: width - 28, top: 38, bottom: height - 62 }};
    const gap = 50;
    const panelHeight = (outer.bottom - outer.top - gap) / 2;
    const monthBox = {{ left: outer.left, right: outer.right, top: outer.top, bottom: outer.top + panelHeight }};
    const cumulativeBox = {{ left: outer.left, right: outer.right, top: monthBox.bottom + gap, bottom: outer.bottom }};
    [monthBox, cumulativeBox].forEach(box => {{
      box.width = box.right - box.left;
      box.height = box.bottom - box.top;
    }});

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = cssVar('--surface');
    ctx.fillRect(0, 0, width, height);

    const [monthYMin, monthYMax] = barYDomain(items.map(item => item.pct));
    const [cumulativeYMin, cumulativeYMax] = yDomain(items.map(item => item.cumulativePct));
    const xFor = (box, index) => box.left + (index + 0.5) * (box.width / Math.max(1, items.length));
    const yFor = (box, value, yMin, yMax) => box.bottom - ((value - yMin) / (yMax - yMin)) * box.height;

    const hits = [];

    function drawPanelAxes(box, yMin, yMax, title, color, showMonthLabels) {{
      ctx.fillStyle = cssVar('--surface-soft');
      ctx.fillRect(box.left, box.top, box.width, box.height);
      ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'left';
      ctx.fillStyle = color;
      ctx.fillText(title, box.left, box.top - 14);

      const ticks = niceTicks(yMin, yMax, 4);
      ticks.forEach(tick => {{
        const y = yFor(box, tick, yMin, yMax);
        ctx.strokeStyle = cssVar('--line');
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(box.left, y);
        ctx.lineTo(box.right, y);
        ctx.stroke();

        ctx.fillStyle = cssVar('--muted');
        ctx.textAlign = 'right';
        ctx.fillText(`${{tick.toFixed(0)}}%`, box.left - 10, y);
      }});

      const zeroY = yFor(box, 0, yMin, yMax);
      ctx.strokeStyle = cssVar('--line-strong');
      ctx.lineWidth = 1.25;
      ctx.beginPath();
      ctx.moveTo(box.left, box.top);
      ctx.lineTo(box.left, box.bottom);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(box.left, zeroY);
      ctx.lineTo(box.right, zeroY);
      ctx.stroke();

      if (showMonthLabels) {{
        ctx.fillStyle = cssVar('--muted');
        ctx.textAlign = 'center';
        labels.forEach((label, index) => {{
          ctx.fillText(`${{label}}月`, xFor(box, index), box.bottom + 34);
        }});
      }}
    }}

    function drawSeries(box, yMin, yMax, key, color, kind) {{
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.6;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.beginPath();
      items.forEach((item, index) => {{
        const x = xFor(box, index);
        const y = yFor(box, item[key], yMin, yMax);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }});
      ctx.stroke();

      items.forEach((item, index) => {{
        const x = xFor(box, index);
        const y = yFor(box, item[key], yMin, yMax);
        ctx.fillStyle = cssVar('--surface');
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        hits.push({{ x, y, radius: 11, kind, item, label: `${{item.year}}年${{item.month}}月` }});
      }});

      const latest = items[items.length - 1];
      if (latest) {{
        const x = xFor(box, items.length - 1);
        const y = yFor(box, latest[key], yMin, yMax);
        ctx.fillStyle = color;
        ctx.textAlign = 'right';
        ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
        const labelY = Math.max(box.top + 14, Math.min(box.bottom - 12, y - 12));
        ctx.fillText(formatPct(latest[key]), box.right, labelY);
      }}
    }}

    function drawBars(box, yMin, yMax, key, kind) {{
      const zeroY = yFor(box, 0, yMin, yMax);
      const slot = box.width / Math.max(1, items.length);
      const barWidth = Math.min(48, Math.max(18, slot * 0.42));

      items.forEach((item, index) => {{
        const value = item[key];
        const x = xFor(box, index);
        const y = yFor(box, value, yMin, yMax);
        const top = Math.min(y, zeroY);
        const height = Math.max(3, Math.abs(zeroY - y));
        const color = value >= 0 ? cssVar('--rise') : cssVar('--fall');
        const fill = value >= 0 ? cssVar('--rise-soft') : cssVar('--fall-soft');

        ctx.fillStyle = fill;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.1;
        roundRect(ctx, x - barWidth / 2, top, barWidth, height, 7);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = color;
        ctx.textAlign = 'center';
        ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
        const labelGap = 18;
        const rawLabelY = value >= 0 ? top - labelGap : top + height + labelGap;
        const labelY = Math.max(box.top + 15, Math.min(box.bottom - 12, rawLabelY));
        ctx.fillText(formatPct(value), x, labelY);

        hits.push({{ x, y: value >= 0 ? top : top + height, radius: barWidth / 2 + 10, kind, item, label: `${{item.year}}年${{item.month}}月` }});
      }});
    }}

    function roundRect(ctx, x, y, width, height, radius) {{
      const r = Math.min(radius, width / 2, height / 2);
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + width, y, x + width, y + height, r);
      ctx.arcTo(x + width, y + height, x, y + height, r);
      ctx.arcTo(x, y + height, x, y, r);
      ctx.arcTo(x, y, x + width, y, r);
      ctx.closePath();
    }}

    drawPanelAxes(monthBox, monthYMin, monthYMax, '月涨跌幅', cssVar('--rise'), false);
    drawBars(monthBox, monthYMin, monthYMax, 'pct', 'month-bar');
    drawPanelAxes(cumulativeBox, cumulativeYMin, cumulativeYMax, '年内累计涨跌幅', cssVar('--accent'), true);
    drawSeries(cumulativeBox, cumulativeYMin, cumulativeYMax, 'cumulativePct', cssVar('--accent'), 'combo-line');

    chartHits.set(canvas, hits);
  }}

  function showTooltip(canvas, hit, event) {{
    const item = hit.item;
    const pctClass = item.pct > 0 ? 'rise' : item.pct < 0 ? 'fall' : 'flat';
    const cumulativeClass = item.cumulativePct > 0 ? 'rise' : item.cumulativePct < 0 ? 'fall' : 'flat';
    tooltip.innerHTML = `
      <strong>${{hit.label}}${{item.partial ? '，截至最新净值' : ''}}</strong>
      <dl>
        <dt>月涨跌幅</dt><dd class="${{pctClass}}">${{formatPct(item.pct)}}</dd>
        <dt>年内累计</dt><dd class="${{cumulativeClass}}">${{formatPct(item.cumulativePct)}}</dd>
        <dt>月初净值</dt><dd>${{money(item.startNav)}}</dd>
        <dt>月末净值</dt><dd>${{money(item.endNav)}}</dd>
        <dt>交易日</dt><dd>${{item.tradeDays}} 个</dd>
      </dl>
    `;
    const rect = canvas.getBoundingClientRect();
    const x = rect.left + hit.x;
    const y = rect.top + hit.y;
    const left = Math.min(window.innerWidth - 224, Math.max(10, x + 14));
    const top = Math.min(window.innerHeight - 156, Math.max(10, y - 52));
    tooltip.style.left = `${{left}}px`;
    tooltip.style.top = `${{top}}px`;
    tooltip.classList.add('visible');
  }}

  function hideTooltip() {{
    tooltip.classList.remove('visible');
  }}

  function nearestHit(canvas, event) {{
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    let best = null;
    let bestDistance = Infinity;
    for (const hit of chartHits.get(canvas) || []) {{
      const distance = Math.hypot(hit.x - x, hit.y - y);
      if (distance < hit.radius && distance < bestDistance) {{
        best = hit;
        bestDistance = distance;
      }}
    }}
    return best;
  }}

  function attachTooltip(canvas) {{
    if (!canvas) return;
    canvas.addEventListener('mousemove', event => {{
      const hit = nearestHit(canvas, event);
      if (hit) showTooltip(canvas, hit, event);
      else hideTooltip();
    }});
    canvas.addEventListener('mouseleave', hideTooltip);
  }}

  function showHeatmapTooltip(cell) {{
    const pct = Number(cell.dataset.pct);
    const cumulativePct = Number(cell.dataset.cumulativePct);
    const pctClass = pct > 0 ? 'rise' : pct < 0 ? 'fall' : 'flat';
    const cumulativeClass = cumulativePct > 0 ? 'rise' : cumulativePct < 0 ? 'fall' : 'flat';
    tooltip.innerHTML = `
      <strong>${{cell.dataset.label}}${{cell.dataset.partial === 'true' ? '，尚未完整' : ''}}</strong>
      <dl>
        <dt>月涨跌幅</dt><dd class="${{pctClass}}">${{formatPct(pct)}}</dd>
        <dt>年内累计</dt><dd class="${{cumulativeClass}}">${{formatPct(cumulativePct)}}</dd>
        <dt>月初净值</dt><dd>${{money(cell.dataset.startNav)}}</dd>
        <dt>月末净值</dt><dd>${{money(cell.dataset.endNav)}}</dd>
        <dt>交易日</dt><dd>${{cell.dataset.tradeDays}} 个</dd>
      </dl>
    `;
    const rect = cell.getBoundingClientRect();
    const left = Math.min(window.innerWidth - 224, Math.max(10, rect.left + rect.width + 12));
    const top = Math.min(window.innerHeight - 156, Math.max(10, rect.top + rect.height / 2 - 58));
    tooltip.style.left = `${{left}}px`;
    tooltip.style.top = `${{top}}px`;
    tooltip.classList.add('visible');
  }}

  function attachHeatmapTooltip() {{
    document.querySelectorAll('.heat-cell.has-value').forEach(cell => {{
      cell.addEventListener('mouseenter', () => showHeatmapTooltip(cell));
      cell.addEventListener('mouseleave', hideTooltip);
      cell.addEventListener('focus', () => showHeatmapTooltip(cell));
      cell.addEventListener('blur', hideTooltip);
    }});
  }}

  function drawAll() {{
    drawComboChart();
  }}

  attachHeatmapTooltip();
  attachTooltip(document.getElementById('comboChart'));
  window.addEventListener('resize', drawAll);
  drawAll();
</script>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    years = previous_years() + [TODAY.year]
    start = data_start()
    days = fetch_fund_days(start, TODAY)
    if not days:
        raise RuntimeError("未获取到基金净值数据")

    monthly = build_monthly_returns(days, years)
    payload = chart_payload(monthly)

    csv_path = OUT_DIR / f"fund_{FUND_CODE}_monthly_returns_{years[0]}_{TODAY.year}.csv"
    html_path = OUT_DIR / f"fund_{FUND_CODE}_monthly_charts.html"
    write_csv(monthly, csv_path)
    html_path.write_text(render_html(payload), encoding="utf-8")

    print(f"previous_years={', '.join(str(year) for year in previous_years())}")
    print(f"current_year={TODAY.year}")
    print(f"monthly_records={len(monthly)}")
    print(f"latest_date={payload['latestDate']}")
    print(f"csv={csv_path}")
    print(f"html={html_path}")


if __name__ == "__main__":
    main()
