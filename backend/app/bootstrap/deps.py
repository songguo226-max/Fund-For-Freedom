from __future__ import annotations

from functools import lru_cache

from app.infrastructure.cache import TTLCache
from app.integrations.fund_data.registry import ProviderRegistry, default_registry


@lru_cache
def get_registry() -> ProviderRegistry:
    return default_registry()


@lru_cache
def get_cache() -> TTLCache:
    return TTLCache()
