from __future__ import annotations

from typing import Callable, TypeVar

from app.integrations.fund_data.adapters.eastmoney import EastmoneyProvider
from app.integrations.fund_data.adapters.morningstar import MorningstarProvider
from app.integrations.fund_data.interface import FundDataProvider, ProviderError

T = TypeVar("T")


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: list[FundDataProvider] = []

    def register(self, provider: FundDataProvider) -> None:
        self._providers.append(provider)

    def get(self, name: str) -> FundDataProvider:
        for p in self._providers:
            if p.name == name:
                return p
        raise KeyError(name)

    def names(self) -> list[str]:
        return [p.name for p in self._providers]

    def ordered(self) -> list[FundDataProvider]:
        return list(self._providers)


def call_with_fallback(registry: ProviderRegistry, source: str | None,
                       fn: Callable[[FundDataProvider], T]) -> T:
    if source is not None:
        return fn(registry.get(source))
    last_exc: Exception | None = None
    for provider in registry.ordered():
        try:
            return fn(provider)
        except ProviderError as exc:
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    raise ProviderError("没有可用的数据源")


def default_registry() -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(EastmoneyProvider())
    reg.register(MorningstarProvider())
    return reg
