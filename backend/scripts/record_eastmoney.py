"""一次性联网运行，抓取真实响应保存为测试 fixture。"""
from __future__ import annotations

from pathlib import Path
import httpx

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://fundf10.eastmoney.com/",
    "User-Agent": "Mozilla/5.0",
}
OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=HEADERS, timeout=20) as client:
        lsjz = client.get(
            "https://api.fund.eastmoney.com/f10/lsjz",
            params={"fundCode": "000218", "pageIndex": 1, "pageSize": 100},
        )
        (OUT / "eastmoney_lsjz_000218.json").write_text(lsjz.text, encoding="utf-8")

        search = client.get(
            "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx",
            params={"m": 1, "key": "黄金"},
        )
        (OUT / "eastmoney_search_huangjin.json").write_text(search.text, encoding="utf-8")

    print("saved fixtures to", OUT)


if __name__ == "__main__":
    main()
