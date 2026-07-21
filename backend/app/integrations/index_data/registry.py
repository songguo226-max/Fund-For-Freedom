from __future__ import annotations

from typing import Callable, TypeVar

from app.integrations.index_data.adapters.akshare import AkshareIndexProvider
from app.integrations.index_data.adapters.yfinance import YFinanceIndexProvider
from app.integrations.index_data.interface import IndexDataError, IndexDataProvider, IndexSpec

T = TypeVar("T")


class IndexProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, IndexDataProvider] = {}

    def register(self, provider: IndexDataProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> IndexDataProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise IndexDataError(f"Unknown index data source: {name}") from exc


def call_index_provider(
    registry: IndexProviderRegistry,
    spec: IndexSpec,
    source: str | None,
    fn: Callable[[IndexDataProvider], T],
) -> T:
    names = (source,) if source else spec.source_priority
    last_exc: Exception | None = None
    for name in names:
        try:
            return fn(registry.get(name))
        except IndexDataError as exc:
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    raise IndexDataError(f"No available index data source for {spec.id}")


def default_index_registry() -> IndexProviderRegistry:
    reg = IndexProviderRegistry()
    reg.register(AkshareIndexProvider())
    reg.register(YFinanceIndexProvider())
    return reg
