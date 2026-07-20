from __future__ import annotations

import csv
import io

from app.integrations.fund_data.interface import FundDay


def daily_csv(days: list[FundDay]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["日期", "单位净值", "累计净值", "日涨跌幅(%)"])
    for item in sorted(days, key=lambda d: d.day):
        writer.writerow(
            [
                item.day.isoformat(),
                f"{item.nav:.4f}",
                f"{item.cumulative_nav:.4f}",
                f"{item.pct_change:.2f}",
            ]
        )
    return buf.getvalue()


def monthly_csv(items: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
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
    for item in items:
        writer.writerow(
            [
                item["year"],
                item["month"],
                item["startDate"],
                item["endDate"],
                f'{item["startNav"]:.4f}',
                f'{item["endNav"]:.4f}',
                f'{item["cumulativeNav"]:.4f}',
                f'{item["pct"]:.2f}',
                f'{item["cumulativePct"]:.2f}',
                item["tradeDays"],
                "是" if item["partial"] else "否",
            ]
        )
    return buf.getvalue()
