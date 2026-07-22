from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NewsRelation:
    fund_code: str | None
    fund_name: str
    relation_type: str
    matched_keywords: tuple[str, ...]
    impact_variables: tuple[str, ...]


TAG_KEYWORDS = {
    "qdii": ("美元", "汇率", "美联储", "FOMC", "纳斯达克", "海外", "全球", "美股"),
    "technology": ("科技", "人工智能", "AI", "云计算", "芯片", "半导体", "互联网"),
    "internet": ("互联网", "平台经济", "游戏", "电商", "广告"),
    "csi300": ("沪深300", "大盘", "蓝筹", "A股", "指数样本"),
    "csi500": ("中证500", "中小盘", "A股", "指数样本"),
    "index-enhanced": ("指数增强", "量化", "因子", "成分股", "样本股"),
    "materials": ("有色", "铜", "铝", "锂", "稀土", "金属"),
    "metals": ("有色", "铜", "铝", "锂", "稀土", "金属"),
    "gold": ("黄金", "金价", "美元", "实际利率", "避险"),
    "new-energy-vehicle": ("新能源车", "电动车", "电池", "锂电", "特斯拉"),
    "robotics": ("机器人", "自动化", "工业母机", "智能制造"),
    "emerging-markets": ("新兴市场", "美元", "汇率", "外资", "全球流动性"),
    "nasdaq100": ("纳斯达克", "美股", "科技股", "美元", "美联储"),
    "semiconductor": ("半导体", "芯片", "晶圆", "AI芯片", "存储"),
}

IMPACT_VARIABLE_KEYWORDS = {
    "利率": ("利率", "降息", "加息", "LPR", "FOMC", "联邦基金", "收益率"),
    "汇率": ("汇率", "人民币", "美元", "外汇", "离岸人民币"),
    "盈利": ("盈利", "业绩", "收入", "利润", "订单", "需求"),
    "估值": ("估值", "市盈率", "风险偏好", "流动性"),
    "政策": ("政策", "监管", "规则", "办法", "指引", "通知", "公告"),
}

MACRO_KEYWORDS = ("央行", "美联储", "利率", "汇率", "流动性", "货币政策", "公开市场", "FOMC")
PRECISE_THEME_KEYWORDS = {
    "半导体",
    "芯片",
    "机器人",
    "黄金",
    "新能源车",
    "电动车",
    "电池",
    "纳斯达克",
    "沪深300",
    "中证500",
    "有色",
    "金属",
    "稀土",
    "铜",
    "铝",
    "锂",
    "互联网",
}


def classify_news(item: dict[str, Any], holdings: list[dict[str, Any]]) -> list[NewsRelation]:
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    normalized = _normalize(text)
    impact_variables = _impact_variables(normalized)
    relations: list[NewsRelation] = []
    for holding in holdings:
        matched: list[str] = []
        code = holding.get("code")
        if code and code in normalized:
            matched.append(code)
        for keyword in _holding_keywords(holding):
            if _normalize(keyword) in normalized:
                matched.append(keyword)

        relation_type = ""
        if matched:
            relation_type = "fund"
        else:
            tag_matches = _tag_matches(holding, normalized)
            if _is_direct_theme_match(tag_matches):
                matched.extend(tag_matches)
                relation_type = "theme"
            elif any(_normalize(keyword) in normalized for keyword in MACRO_KEYWORDS):
                if _macro_applies_to_holding(holding):
                    relation_type = "macro"
                    matched.extend(keyword for keyword in MACRO_KEYWORDS if _normalize(keyword) in normalized)

        if relation_type:
            relations.append(
                NewsRelation(
                    fund_code=holding.get("code"),
                    fund_name=holding["name"],
                    relation_type=relation_type,
                    matched_keywords=tuple(dict.fromkeys(matched)),
                    impact_variables=impact_variables,
                )
            )
    return relations


def _holding_keywords(holding: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = [holding["name"]]
    values.extend(holding.get("aliases", []))
    return tuple(value for value in values if value)


def _tag_matches(holding: dict[str, Any], normalized_text: str) -> list[str]:
    matches: list[str] = []
    for tag in holding.get("tags", []):
        for keyword in TAG_KEYWORDS.get(tag, ()):
            if _normalize(keyword) in normalized_text:
                matches.append(keyword)
    return matches


def _impact_variables(normalized_text: str) -> tuple[str, ...]:
    variables = []
    for variable, keywords in IMPACT_VARIABLE_KEYWORDS.items():
        if any(_normalize(keyword) in normalized_text for keyword in keywords):
            variables.append(variable)
    return tuple(variables)


def _macro_applies_to_holding(holding: dict[str, Any]) -> bool:
    tags = set(holding.get("tags", []))
    return bool(tags & {"qdii", "csi300", "csi500", "index-enhanced", "gold", "nasdaq100", "emerging-markets"})


def _is_direct_theme_match(matches: list[str]) -> bool:
    unique = set(matches)
    return len(unique) >= 2 or bool(unique & PRECISE_THEME_KEYWORDS)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()
