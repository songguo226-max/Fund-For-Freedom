from __future__ import annotations

import html
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol


class FundDayLike(Protocol):
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


def pct_state(value: float) -> str:
    if value > 0:
        return "rise"
    if value < 0:
        return "fall"
    return "flat"


def pct_class(value: float, max_abs: float) -> str:
    state = pct_state(value)
    if state == "flat" or max_abs <= 0:
        return "flat"
    level = max(1, min(5, round(abs(value) / max_abs * 5)))
    return f"{state} level-{level}"


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def month_days(days: list[FundDayLike], month: date) -> list[FundDayLike]:
    return [item for item in days if item.day.year == month.year and item.day.month == month.month]


def month_summary(days: list[FundDayLike], month: date) -> dict[str, str | int | float]:
    items = month_days(days, month)
    if not items:
        return {
            "trade_days": 0,
            "return": 0.0,
            "start_nav": "",
            "end_nav": "",
            "return_text": "暂无",
            "return_class": "flat",
        }

    start_nav = items[0].nav
    end_nav = items[-1].nav
    month_return = (end_nav / start_nav - 1) * 100 if start_nav else 0
    return {
        "trade_days": len(items),
        "return": month_return,
        "start_nav": f"{start_nav:.4f}",
        "end_nav": f"{end_nav:.4f}",
        "return_text": fmt_pct(month_return),
        "return_class": pct_state(month_return),
    }


def render_calendar(days: list[FundDayLike], month: date, end: date, max_abs: float) -> str:
    by_day = {item.day: item for item in days}
    first_cell = month - timedelta(days=(month.weekday() + 1) % 7)
    last_day = min(month_end(month), end)
    last_cell = last_day + timedelta(days=(6 - ((last_day.weekday() + 1) % 7)))

    cells: list[str] = []
    cursor = first_cell
    while cursor <= last_cell:
        weekday = (cursor.weekday() + 1) % 7
        weekend = " weekend" if weekday in (0, 6) else ""
        item = by_day.get(cursor)
        in_month = cursor.month == month.month and cursor <= end

        if not in_month:
            cells.append('<div class="day-cell blank" aria-hidden="true"></div>')
        elif item is None:
            cells.append(
                f"""
                <div class="day-cell closed{weekend}" data-date="{cursor.isoformat()}">
                  <div class="day-num">{cursor.day}</div>
                  <div class="closed-label">休市</div>
                </div>
                """
            )
        else:
            classes = pct_class(item.pct_change, max_abs)
            cells.append(
                f"""
                <button class="day-cell trading {classes}{weekend}"
                        type="button"
                        data-date="{item.day.isoformat()}"
                        data-nav="{item.nav:.4f}"
                        data-cumulative-nav="{item.cumulative_nav:.4f}"
                        data-pct="{item.pct_change:+.2f}">
                  <span class="day-num">{item.day.day}</span>
                  <span class="pct">{item.pct_change:+.2f}%</span>
                  <span class="nav">净值 {item.nav:.4f}</span>
                </button>
                """
            )
        cursor += timedelta(days=1)

    return "\n".join(cells)


def render_month_card(days: list[FundDayLike], month: date, end: date, max_abs: float) -> str:
    summary = month_summary(days, month)
    return f"""
    <section class="month-card" aria-labelledby="month-{month.year}-{month.month}">
      <div class="month-head">
        <div>
          <h2 id="month-{month.year}-{month.month}">{month.year}年{month.month}月</h2>
          <p>{summary["trade_days"]} 个交易日</p>
        </div>
        <div class="month-return {summary["return_class"]}">
          <span>月内涨跌</span>
          <strong>{summary["return_text"]}</strong>
        </div>
      </div>
      <div class="month-metrics" aria-label="{month.year}年{month.month}月净值摘要">
        <div><span>月初净值</span><strong>{summary["start_nav"]}</strong></div>
        <div><span>月末净值</span><strong>{summary["end_nav"]}</strong></div>
        <div><span>交易日</span><strong>{summary["trade_days"]}</strong></div>
      </div>
      <div class="weekdays" aria-hidden="true">
        <span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span>
      </div>
      <div class="calendar-grid">
        {render_calendar(days, month, end, max_abs)}
      </div>
    </section>
    """


def build_dataset(fund_name: str, fund_code: str, months: list[date], days: list[FundDayLike], end: date) -> dict:
    by_day = {item.day: item for item in days}
    month_payloads = []
    for month in months:
        first_cell = month - timedelta(days=(month.weekday() + 1) % 7)
        last_day = min(month_end(month), end)
        last_cell = last_day + timedelta(days=(6 - ((last_day.weekday() + 1) % 7)))
        cells = []
        cursor = first_cell
        while cursor <= last_cell:
            item = by_day.get(cursor)
            if cursor.month != month.month or cursor > end:
                cells.append({"type": "blank", "day": None, "date": None, "nav": None, "cumulative_nav": None, "pct": None})
            elif item is None:
                cells.append({"type": "closed", "day": cursor.day, "date": cursor.isoformat(), "nav": None, "cumulative_nav": None, "pct": None})
            else:
                cells.append(
                    {
                        "type": "trading",
                        "day": item.day.day,
                        "date": item.day.isoformat(),
                        "nav": item.nav,
                        "cumulative_nav": item.cumulative_nav,
                        "pct": item.pct_change,
                    }
                )
            cursor += timedelta(days=1)
        month_payloads.append({"year": month.year, "month": month.month, "cells": cells})
    return {"fundName": fund_name, "fundCode": fund_code, "months": month_payloads}


def render_html(days: list[FundDayLike], start: date, end: date, fund_name: str, fund_code: str) -> str:
    days = sorted(days, key=lambda item: item.day)
    if not days:
        raise RuntimeError("未获取到基金净值数据")

    first = days[0]
    latest = days[-1]
    months = iter_months(start, end)
    visual_months = list(reversed(months))
    max_abs = max(abs(item.pct_change) for item in days)
    max_gain = max(days, key=lambda item: item.pct_change)
    max_loss = min(days, key=lambda item: item.pct_change)
    period_return = (latest.nav / first.nav - 1) * 100 if first.nav else 0
    period_state = pct_state(period_return)
    latest_state = pct_state(latest.pct_change)
    dataset_json = json.dumps(build_dataset(fund_name, fund_code, months, days, end), ensure_ascii=False).replace("</", "<\\/")
    month_cards = "".join(render_month_card(days, month, end, max_abs) for month in visual_months)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(fund_name)} 收益日历</title>
<style>
  :root {{
    color-scheme: light;
    --bg: #f3f5f7;
    --surface-raised: #fdfdfc;
    --surface-soft: #f7f8fa;
    --line: #e1e5ea;
    --line-strong: #cfd6df;
    --text: #202328;
    --muted: #65707c;
    --muted-2: #9099a4;
    --rise: #bd2f3c;
    --rise-soft-1: #fff6f6;
    --rise-soft-2: #feecef;
    --rise-soft-3: #fadce1;
    --rise-soft-4: #f4c4cc;
    --rise-soft-5: #eeadb8;
    --fall: #087b63;
    --fall-soft-1: #f2fbf7;
    --fall-soft-2: #e4f6ef;
    --fall-soft-3: #cdeee3;
    --fall-soft-4: #aee0cf;
    --fall-soft-5: #8dcfba;
    --flat: #f0f2f4;
    --weekend: #f8fafb;
    --shadow: 0 10px 28px rgba(25, 34, 45, 0.06);
    --shadow-hover: 0 8px 18px rgba(25, 34, 45, 0.08);
    --radius-lg: 20px;
    --radius-md: 14px;
    --radius-sm: 10px;
  }}

  * {{ box-sizing: border-box; }}
  html {{ min-width: 0; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-variant-numeric: tabular-nums;
    line-height: 1.45;
    text-rendering: geometricPrecision;
  }}
  button {{ font: inherit; }}

  .page {{
    width: min(1480px, 100%);
    margin: 0 auto;
    padding: 34px 30px 56px;
  }}

  .hero {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 384px);
    gap: 18px;
    align-items: stretch;
    margin-bottom: 18px;
  }}

  .hero > div:first-child,
  .latest-card,
  .overview-card,
  .month-card,
  .legend {{
    background: var(--surface-raised);
    border: 1px solid var(--line);
    box-shadow: var(--shadow);
  }}

  .hero > div:first-child {{
    min-height: 176px;
    padding: 26px 28px;
    border-radius: var(--radius-lg);
  }}

  .eyebrow {{
    display: inline-flex;
    width: fit-content;
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
    font-size: 42px;
    font-weight: 850;
    line-height: 1.12;
  }}

  .hero-desc {{
    max-width: 74ch;
    margin: 14px 0 0;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.75;
  }}

  .latest-card {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    border-radius: var(--radius-lg);
    padding: 24px;
  }}

  .label,
  .overview-card span,
  .month-metrics span,
  .month-return span {{
    color: var(--muted);
    font-size: 12px;
    font-weight: 760;
  }}

  .latest-date {{
    margin-top: 4px;
    font-size: 20px;
    font-weight: 820;
  }}

  .latest-main {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-end;
    margin-top: 22px;
  }}

  .latest-main strong {{
    display: block;
    margin-top: 6px;
    font-size: 36px;
    font-weight: 880;
    line-height: 1;
  }}

  .latest-nav {{ text-align: right; }}
  .latest-nav b {{
    display: block;
    margin-top: 4px;
    font-size: 23px;
    font-weight: 820;
  }}

  .overview {{
    display: grid;
    grid-template-columns: 1.25fr repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 22px;
  }}

  .overview-card {{
    min-height: 112px;
    padding: 17px 18px;
    border-radius: 16px;
    box-shadow: 0 8px 22px rgba(25, 34, 45, 0.045);
  }}

  .overview-card strong {{
    display: block;
    margin-top: 11px;
    font-size: 25px;
    font-weight: 850;
    line-height: 1.1;
  }}

  .overview-card:first-child strong {{
    font-size: 19px;
    line-height: 1.35;
  }}

  .overview-card small {{
    display: block;
    margin-top: 9px;
    color: var(--muted-2);
    font-size: 12px;
  }}

  .calendar-board {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 720px), 1fr));
    justify-items: center;
    align-items: start;
    gap: 20px;
  }}

  .month-card {{
    width: 100%;
    max-width: 800px;
    padding: 20px;
    border-radius: var(--radius-lg);
    box-shadow: 0 12px 32px rgba(25, 34, 45, 0.065);
  }}

  .month-head {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--line);
  }}

  .month-head h2 {{
    margin: 0;
    font-size: 22px;
    font-weight: 850;
    line-height: 1.2;
  }}

  .month-head p {{
    margin: 6px 0 0;
    color: var(--muted);
    font-size: 13px;
  }}

  .month-return {{
    min-width: 116px;
    text-align: right;
  }}

  .month-return strong {{
    display: block;
    margin-top: 3px;
    font-size: 23px;
    font-weight: 880;
    line-height: 1.05;
  }}

  .month-metrics {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin: 14px 0 16px;
  }}

  .month-metrics div {{
    border: 1px solid #e7eaee;
    border-radius: var(--radius-sm);
    background: #fafbfc;
    padding: 10px;
  }}

  .month-metrics strong {{
    display: block;
    margin-top: 4px;
    font-size: 16px;
    font-weight: 820;
  }}

  .weekdays,
  .calendar-grid {{
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 7px;
  }}

  .weekdays {{ margin-bottom: 7px; }}
  .weekdays span {{
    color: var(--muted);
    font-size: 12px;
    font-weight: 800;
    text-align: center;
  }}
  .weekdays span:first-child,
  .weekdays span:last-child {{ color: #a0a7b0; }}

  .day-cell {{
    position: relative;
    min-width: 0;
    border: 1px solid transparent;
    border-radius: 11px;
    overflow: hidden;
  }}

  .day-cell.trading {{
    display: grid;
    grid-template-rows: 13px minmax(20px, 1fr) 16px;
    align-items: center;
    width: 100%;
    min-height: 82px;
    aspect-ratio: 1.08 / 1;
    padding: 7px 8px;
    cursor: default;
    text-align: left;
    border-color: rgba(255, 255, 255, 0.68);
    transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
  }}

  .day-cell.trading:hover,
  .day-cell.trading:focus-visible,
  .day-cell.trading.is-active {{
    z-index: 2;
    transform: translateY(-1px);
    border-color: rgba(98, 113, 130, 0.2);
    box-shadow: var(--shadow-hover), 0 0 0 2px rgba(109, 123, 139, 0.08);
    outline: none;
  }}

  .day-cell.trading.rise:hover,
  .day-cell.trading.rise:focus-visible,
  .day-cell.trading.rise.is-active {{
    border-color: rgba(189, 47, 60, 0.22);
    box-shadow: 0 8px 18px rgba(189, 47, 60, 0.08), 0 0 0 2px rgba(189, 47, 60, 0.08);
  }}

  .day-cell.trading.fall:hover,
  .day-cell.trading.fall:focus-visible,
  .day-cell.trading.fall.is-active {{
    border-color: rgba(8, 123, 99, 0.22);
    box-shadow: 0 8px 18px rgba(8, 123, 99, 0.08), 0 0 0 2px rgba(8, 123, 99, 0.08);
  }}

  .day-num {{
    align-self: start;
    color: rgba(32, 35, 40, 0.7);
    font-size: 11px;
    font-weight: 800;
    line-height: 1;
  }}

  .pct {{
    display: block;
    align-self: center;
    width: 100%;
    min-width: 0;
    overflow: visible;
    text-align: center;
    white-space: nowrap;
    font-size: 18px;
    font-weight: 840;
    line-height: 1;
  }}

  .nav {{
    display: block;
    align-self: end;
    width: 100%;
    min-width: 0;
    overflow: hidden;
    color: rgba(32, 35, 40, 0.72);
    font-size: 11px;
    font-weight: 720;
    line-height: 1.1;
    text-align: center;
    white-space: nowrap;
  }}

  .closed {{
    min-height: 82px;
    aspect-ratio: 1.08 / 1;
    padding: 8px;
    background: var(--flat);
    color: var(--muted-2);
    border: 1px solid #eceff2;
  }}

  .closed.weekend {{ background: var(--weekend); }}
  .closed-label {{
    position: absolute;
    left: 8px;
    bottom: 8px;
    color: var(--muted-2);
    font-size: 11px;
    font-weight: 700;
  }}

  .blank {{
    visibility: hidden;
    pointer-events: none;
  }}

  .rise {{ color: var(--rise); }}
  .fall {{ color: var(--fall); }}
  .flat {{ color: var(--muted); }}
  .rise.level-1 {{ background: var(--rise-soft-1); }}
  .rise.level-2 {{ background: var(--rise-soft-2); }}
  .rise.level-3 {{ background: var(--rise-soft-3); }}
  .rise.level-4 {{ background: var(--rise-soft-4); }}
  .rise.level-5 {{ background: var(--rise-soft-5); }}
  .fall.level-1 {{ background: var(--fall-soft-1); }}
  .fall.level-2 {{ background: var(--fall-soft-2); }}
  .fall.level-3 {{ background: var(--fall-soft-3); }}
  .fall.level-4 {{ background: var(--fall-soft-4); }}
  .fall.level-5 {{ background: var(--fall-soft-5); }}
  .day-cell.trading.rise .pct,
  .day-cell.trading.rise .nav {{ color: var(--rise); }}
  .day-cell.trading.fall .pct,
  .day-cell.trading.fall .nav {{ color: var(--fall); }}

  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: center;
    margin: 22px 0 0;
    padding: 16px 18px;
    border-radius: var(--radius-md);
    color: var(--muted);
    font-size: 13px;
    box-shadow: 0 8px 22px rgba(25, 34, 45, 0.045);
  }}
  .legend strong {{ color: var(--text); }}
  .legend-item {{
    display: inline-flex;
    gap: 7px;
    align-items: center;
    white-space: nowrap;
  }}
  .swatch {{
    width: 18px;
    height: 12px;
    border: 1px solid var(--line);
    border-radius: 999px;
  }}
  .swatch.flat-swatch {{ background: var(--flat); }}

  .tooltip {{
    position: fixed;
    z-index: 50;
    width: auto;
    min-width: 176px;
    max-width: 196px;
    padding: 9px 10px;
    border: 1px solid rgba(210, 216, 224, 0.86);
    border-radius: 11px;
    background: #fdfefe;
    box-shadow: 0 10px 24px rgba(31, 41, 55, 0.12);
    opacity: 0;
    transform: translateY(2px);
    pointer-events: none;
    transition: opacity 160ms ease, transform 160ms ease;
  }}
  .tooltip.rise {{
    border-color: rgba(189, 47, 60, 0.2);
    box-shadow: 0 10px 24px rgba(189, 47, 60, 0.10);
  }}
  .tooltip.fall {{
    border-color: rgba(8, 123, 99, 0.2);
    box-shadow: 0 10px 24px rgba(8, 123, 99, 0.10);
  }}
  .tooltip::before,
  .tooltip::after {{
    content: "";
    position: absolute;
    left: var(--arrow-x, 50%);
    width: 0;
    height: 0;
    transform: translateX(-50%);
  }}
  .tooltip[data-placement="top"]::before {{
    bottom: -7px;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-top: 7px solid rgba(210, 216, 224, 0.86);
  }}
  .tooltip[data-placement="top"]::after {{
    bottom: -6px;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid #fdfefe;
  }}
  .tooltip[data-placement="bottom"]::before {{
    top: -7px;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 7px solid rgba(210, 216, 224, 0.86);
  }}
  .tooltip[data-placement="bottom"]::after {{
    top: -6px;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-bottom: 6px solid #fdfefe;
  }}
  .tooltip.visible {{
    opacity: 1;
    transform: translateY(0);
  }}
  .tooltip .tip-date {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(230, 234, 239, 0.88);
    color: var(--text);
    font-size: 13px;
    font-weight: 850;
  }}
  .tooltip .tip-date small {{
    color: #8a94a1;
    font-size: 10px;
    font-weight: 720;
  }}
  .tooltip dl {{
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 14px;
    margin: 0;
    font-size: 11px;
  }}
  .tooltip dt {{
    color: #7a8491;
    font-weight: 620;
    white-space: nowrap;
  }}
  .tooltip dd {{
    margin: 0;
    color: #252a31;
    font-weight: 850;
    text-align: right;
    white-space: nowrap;
  }}
  .tooltip dd.rise,
  .tooltip dd.fall {{ font-size: 12px; }}

  .page-footer {{
    margin-top: 18px;
    color: var(--muted);
    font-size: 13px;
  }}

  @media (min-width: 1540px) {{
    .calendar-board {{ grid-template-columns: repeat(2, minmax(720px, 1fr)); }}
  }}

  @media (max-width: 1120px) {{
    .page {{ padding-inline: 22px; }}
    .hero {{ grid-template-columns: 1fr; }}
    .overview {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .overview-card:first-child {{ grid-column: span 2; }}
    .calendar-board {{ grid-template-columns: minmax(0, 1fr); gap: 16px; }}
    .month-card {{ max-width: 820px; padding: 17px; }}
  }}

  @media (max-width: 920px) {{
    .overview {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .overview-card:first-child,
    .overview-card:last-child {{ grid-column: auto; }}
  }}

  @media (max-width: 560px) {{
    .page {{ padding: 18px 10px 36px; }}
    .hero {{ gap: 12px; }}
    .hero > div:first-child,
    .latest-card {{ border-radius: 17px; padding: 17px; }}
    h1 {{ font-size: 30px; }}
    .hero-desc {{ margin-top: 10px; font-size: 13px; line-height: 1.65; }}
    .latest-main {{ align-items: flex-start; flex-direction: column; }}
    .latest-nav {{ text-align: left; }}
    .latest-main strong {{ font-size: 30px; }}
    .overview {{ grid-template-columns: 1fr; gap: 9px; }}
    .overview-card {{ min-height: 92px; padding: 13px; }}
    .overview-card strong {{ font-size: 20px; }}
    .overview-card:first-child strong {{ font-size: 16px; }}
    .calendar-board {{ gap: 14px; }}
    .month-card {{ max-width: none; padding: 11px; border-radius: 16px; }}
    .month-head {{ align-items: flex-start; padding-bottom: 11px; }}
    .month-head h2 {{ font-size: 19px; }}
    .month-return {{ min-width: 92px; }}
    .month-return strong {{ font-size: 18px; }}
    .month-metrics {{ margin: 11px 0 12px; gap: 5px; }}
    .month-metrics div {{ padding: 7px 5px; }}
    .month-metrics span {{ font-size: 11px; }}
    .month-metrics strong {{ font-size: 13px; }}
    .weekdays,
    .calendar-grid {{ gap: 4px; }}
    .day-cell.trading,
    .closed {{
      min-height: 48px;
      aspect-ratio: 0.96 / 1;
      padding: 5px 4px;
    }}
    .day-cell.trading {{ grid-template-rows: 10px minmax(16px, 1fr); }}
    .day-num {{ font-size: 10px; }}
    .pct {{ font-size: 8.8px; font-weight: 820; }}
    .nav {{ display: none; }}
    .closed-label {{ left: 5px; bottom: 6px; font-size: 9px; }}
    .legend {{ gap: 8px 12px; padding: 13px 12px; font-size: 12px; }}
  }}
</style>
</head>
<body>
<main class="page">
  <header class="hero">
    <div>
      <p class="eyebrow">基金收益日历</p>
      <h1>收益日历</h1>
      <p class="hero-desc">{html.escape(fund_name)} ({fund_code})，统计区间 {first.day.isoformat()} 至 {latest.day.isoformat()}。红色代表上涨，绿色代表下跌，鼠标悬停可查看每日净值明细。</p>
    </div>
    <aside class="latest-card" aria-label="最新交易日摘要">
      <div class="label">最新交易日</div>
      <div class="latest-date">{latest.day.isoformat()}</div>
      <div class="latest-main">
        <div>
          <div class="label">最新涨跌幅</div>
          <strong class="{latest_state}">{fmt_pct(latest.pct_change)}</strong>
        </div>
        <div class="latest-nav">
          <div class="label">最新单位净值</div>
          <b>{latest.nav:.4f}</b>
        </div>
      </div>
    </aside>
  </header>

  <section class="overview" aria-label="数据概览">
    <div class="overview-card">
      <span>统计区间</span>
      <strong>{first.day.isoformat()}<br>{latest.day.isoformat()}</strong>
      <small>共 {len(days)} 个交易日</small>
    </div>
    <div class="overview-card">
      <span>区间累计涨跌幅</span>
      <strong class="{period_state}">{fmt_pct(period_return)}</strong>
      <small>{first.nav:.4f} → {latest.nav:.4f}</small>
    </div>
    <div class="overview-card">
      <span>区间最高单日涨幅</span>
      <strong class="rise">{fmt_pct(max_gain.pct_change)}</strong>
      <small>{max_gain.day.isoformat()}</small>
    </div>
    <div class="overview-card">
      <span>区间最大单日跌幅</span>
      <strong class="fall">{fmt_pct(max_loss.pct_change)}</strong>
      <small>{max_loss.day.isoformat()}</small>
    </div>
    <div class="overview-card">
      <span>最新单位净值</span>
      <strong>{latest.nav:.4f}</strong>
      <small>累计净值 {latest.cumulative_nav:.4f}</small>
    </div>
  </section>

  <section class="calendar-board" aria-label="月度收益日历">
    {month_cards}
  </section>

  <section class="legend" aria-label="颜色图例">
    <strong>图例</strong>
    <span class="legend-item"><i class="swatch rise level-5"></i>大幅上涨</span>
    <span class="legend-item"><i class="swatch rise level-1"></i>小幅上涨</span>
    <span class="legend-item"><i class="swatch flat-swatch"></i>平盘或休市</span>
    <span class="legend-item"><i class="swatch fall level-1"></i>小幅下跌</span>
    <span class="legend-item"><i class="swatch fall level-5"></i>大幅下跌</span>
    <span>红色代表上涨，绿色代表下跌，颜色越深代表单日涨跌幅越大。</span>
  </section>

  <p class="page-footer">数据来自天天基金/东方财富公开接口，页面按最近已公布净值生成。</p>
</main>

<div class="tooltip" id="tooltip" role="tooltip" aria-hidden="true"></div>
<script type="application/json" id="fund-data">{dataset_json}</script>
<script>
  const tooltip = document.getElementById('tooltip');
  const formatPct = value => `${{Number(value).toFixed(2).replace(/^(-?)/, match => match === '-' ? '-' : '+')}}%`;

  function renderTooltip(cell) {{
    const pct = Number(cell.dataset.pct);
    const state = pct > 0 ? 'rise' : pct < 0 ? 'fall' : 'flat';
    tooltip.classList.remove('rise', 'fall', 'flat');
    tooltip.classList.add(state);
    tooltip.innerHTML = `
      <div class="tip-date"><span>${{cell.dataset.date}}</span><small>交易日</small></div>
      <dl>
        <dt>单位净值</dt><dd>${{cell.dataset.nav}}</dd>
        <dt>累计净值</dt><dd>${{cell.dataset.cumulativeNav}}</dd>
        <dt>当日涨跌幅</dt><dd class="${{state}}">${{formatPct(pct)}}</dd>
      </dl>
    `;
  }}

  function placeTooltip(cell) {{
    const gap = 10;
    const margin = 10;
    const rect = cell.getBoundingClientRect();
    const width = tooltip.offsetWidth || 188;
    const height = tooltip.offsetHeight || 96;
    const anchorX = rect.left + rect.width / 2;
    const hasRoomAbove = rect.top >= height + gap + margin;
    const placement = hasRoomAbove ? 'top' : 'bottom';

    let left = anchorX - width / 2;
    left = Math.min(Math.max(margin, left), window.innerWidth - width - margin);

    const top = placement === 'top'
      ? rect.top - height - gap
      : rect.bottom + gap;

    const arrowX = anchorX - left;
    tooltip.dataset.placement = placement;
    tooltip.style.setProperty('--arrow-x', `${{Math.min(Math.max(14, arrowX), width - 14)}}px`);
    tooltip.style.left = `${{left}}px`;
    tooltip.style.top = `${{Math.max(margin, top)}}px`;
  }}

  function showTooltip(cell) {{
    renderTooltip(cell);
    tooltip.classList.add('visible');
    tooltip.setAttribute('aria-hidden', 'false');
    placeTooltip(cell);
  }}

  function hideTooltip() {{
    tooltip.classList.remove('visible');
    tooltip.setAttribute('aria-hidden', 'true');
  }}

  document.querySelectorAll('.day-cell.trading').forEach(cell => {{
    cell.addEventListener('mouseenter', () => showTooltip(cell));
    cell.addEventListener('mouseleave', hideTooltip);
    cell.addEventListener('focus', () => showTooltip(cell));
    cell.addEventListener('click', () => {{
      document.querySelectorAll('.day-cell.trading.is-active').forEach(activeCell => {{
        activeCell.classList.remove('is-active');
      }});
      cell.classList.add('is-active');
      showTooltip(cell);
    }});
    cell.addEventListener('blur', hideTooltip);
  }});
</script>
</body>
</html>
"""


def write_final_calendar_html(
    days: list[FundDayLike],
    path: Path,
    start: date,
    end: date,
    fund_name: str,
    fund_code: str,
) -> None:
    path.write_text(render_html(days, start, end, fund_name, fund_code), encoding="utf-8")
