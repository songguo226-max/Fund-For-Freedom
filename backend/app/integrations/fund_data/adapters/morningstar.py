from __future__ import annotations

from datetime import date

from app.integrations.fund_data.interface import FundDay, FundHit, FundMeta, ProviderError

_MSG = "morningstar provider 尚未实现，请使用 eastmoney 或等待后续解析支持"


class MorningstarProvider:
    """晨星网数据源骨架。真实网页解析作为后续任务补全。

    TODO: 解析 https://www.morningstar.cn 基金页净值表，映射为标准 FundDay。
    """

    name = "morningstar"

    def search(self, q: str) -> list[FundHit]:
        raise ProviderError(_MSG)

    def get_meta(self, code: str) -> FundMeta:
        raise ProviderError(_MSG)

    def get_nav_history(self, code: str, start: date, end: date) -> list[FundDay]:
        raise ProviderError(_MSG)
