from __future__ import annotations

from dataclasses import dataclass

from app.modules.news.classifier import NewsRelation


@dataclass(frozen=True)
class NewsScore:
    relevance_score: int
    duration_score: int
    surprise_score: int
    reliability_score: int

    @property
    def total_score(self) -> int:
        return self.relevance_score + self.duration_score + self.surprise_score + self.reliability_score


def score_news(*, title: str, summary: str, source_reliability_score: int, relations: list[NewsRelation]) -> NewsScore:
    text = f"{title} {summary}"
    relevance = _relevance(relations)
    duration = _duration(text)
    surprise = _surprise(text)
    reliability = max(0, min(source_reliability_score, 2))
    return NewsScore(
        relevance_score=relevance,
        duration_score=duration,
        surprise_score=surprise,
        reliability_score=reliability,
    )


def _relevance(relations: list[NewsRelation]) -> int:
    if any(relation.relation_type == "fund" for relation in relations):
        return 3
    if any(relation.relation_type == "theme" for relation in relations):
        return 2
    if relations:
        return 1
    return 0


def _duration(text: str) -> int:
    long_term = ("政策", "规则", "办法", "指引", "利率", "降息", "加息", "FOMC", "监管", "改革")
    medium_term = ("业绩", "订单", "产能", "供给", "需求", "上市", "指数样本", "回购", "增持")
    if any(keyword in text for keyword in long_term):
        return 3
    if any(keyword in text for keyword in medium_term):
        return 2
    if any(keyword in text for keyword in ("公告", "会议", "发布")):
        return 1
    return 0


def _surprise(text: str) -> int:
    high = ("超预期", "意外", "突然", "大幅", "暂停", "终止", "下调", "上调", "降息", "加息")
    medium = ("调整", "修订", "发布", "征求意见", "新规", "创新")
    if any(keyword in text for keyword in high):
        return 2
    if any(keyword in text for keyword in medium):
        return 1
    return 0
