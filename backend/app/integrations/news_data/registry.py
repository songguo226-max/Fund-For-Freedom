from __future__ import annotations

from app.config.news_settings import news_settings
from app.integrations.news_data.adapters.cls_mobile import build_cls_provider
from app.integrations.news_data.adapters.eastmoney_hot import build_eastmoney_hot_provider
from app.integrations.news_data.adapters.gelonghui_hot import build_gelonghui_hot_provider
from app.integrations.news_data.adapters.xueqiu_hot import build_xueqiu_hot_provider
from app.integrations.news_data.interface import NewsDataProvider, NewsSourceSpec, SourceTier


class NewsProviderRegistry:
    def __init__(self) -> None:
        self._providers: list[NewsDataProvider] = []
        self._specs: dict[str, NewsSourceSpec] = {}

    def register_provider(self, provider: NewsDataProvider) -> None:
        self._providers.append(provider)
        self._specs[provider.spec.id] = provider.spec

    def register_spec(self, spec: NewsSourceSpec) -> None:
        self._specs[spec.id] = spec

    def get(self, source_id: str) -> NewsDataProvider:
        for provider in self._providers:
            if provider.spec.id == source_id:
                return provider
        raise KeyError(source_id)

    def specs(self) -> list[NewsSourceSpec]:
        return sorted(
            self._specs.values(),
            key=lambda spec: (
                {"official": 0, "media": 1, "opinion": 2}.get(spec.tier.value, 9),
                spec.name,
            ),
        )


def default_news_registry() -> NewsProviderRegistry:
    registry = NewsProviderRegistry()
    cache_minutes = news_settings.refresh_cache_minutes
    specs = (
        NewsSourceSpec(
            id="eastmoney",
            name="东方财富",
            tier=SourceTier.MEDIA,
            reliability_score=1,
            homepage="https://rebang.today/fin?tab=eastmoney",
            adapter="eastmoney_hot",
            cache_minutes=cache_minutes,
            terms_note="Use Rebang.Today public latest-list hotlist endpoint for Eastmoney finance items.",
        ),
        NewsSourceSpec(
            id="cls",
            name="财联社",
            tier=SourceTier.MEDIA,
            reliability_score=1,
            homepage="https://www.cls.cn/",
            adapter="cls_hot",
            cache_minutes=cache_minutes,
            terms_note="Use the public web hot-list JSON endpoint with signed query parameters; skip ads, paid, login, cookie-gated, or anti-bot protected content.",
        ),
        NewsSourceSpec(
            id="xueqiu",
            name="雪球话题",
            tier=SourceTier.OPINION,
            reliability_score=0,
            homepage="https://rebang.today/home?tab=xueqiu",
            adapter="xueqiu_hot",
            cache_minutes=cache_minutes,
            terms_note="Use third-party public hotlist pages/APIs only; do not request xueqiu.com with Cookie.",
        ),
        NewsSourceSpec(
            id="gelonghui",
            name="格隆汇",
            tier=SourceTier.OPINION,
            reliability_score=0,
            homepage="https://rebang.today/fin?tab=gelonghui&sub_tab=hot-day",
            adapter="gelonghui_hot",
            cache_minutes=cache_minutes,
            terms_note="Use Rebang.Today public hot-day list first; fall back to TopHub finance page when the primary source is unavailable.",
        ),
    )
    for spec in specs:
        registry.register_spec(spec)
        if spec.id == "eastmoney":
            registry.register_provider(build_eastmoney_hot_provider(spec))
        elif spec.id == "cls":
            registry.register_provider(build_cls_provider(spec))
        elif spec.id == "xueqiu":
            registry.register_provider(build_xueqiu_hot_provider(spec))
        elif spec.id == "gelonghui":
            registry.register_provider(build_gelonghui_hot_provider(spec))
    return registry
