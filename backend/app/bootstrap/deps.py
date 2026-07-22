from __future__ import annotations

from functools import lru_cache

from app.infrastructure.cache import TTLCache
from app.infrastructure.news_store import NewsStore
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.integrations.index_data.registry import IndexProviderRegistry, default_index_registry
from app.integrations.fund_data.registry import ProviderRegistry, default_registry
from app.integrations.news_data.registry import NewsProviderRegistry, default_news_registry


@lru_cache
def get_registry() -> ProviderRegistry:
    return default_registry()


@lru_cache
def get_cache() -> TTLCache:
    return TTLCache()


@lru_cache
def get_index_registry() -> IndexProviderRegistry:
    return default_index_registry()


@lru_cache
def get_news_registry() -> NewsProviderRegistry:
    return default_news_registry()


@lru_cache
def get_news_store() -> NewsStore:
    return NewsStore()


@lru_cache
def get_news_rate_limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter()
