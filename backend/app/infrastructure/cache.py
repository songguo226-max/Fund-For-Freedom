from __future__ import annotations

from datetime import date
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[tuple, Any] = {}

    def _key(self, key: tuple, today: date) -> tuple:
        return (today.isoformat(), *key)

    def get(self, key: tuple, today: date | None = None) -> Any | None:
        return self._store.get(self._key(key, today or date.today()))

    def set(self, key: tuple, value: Any, today: date | None = None) -> None:
        self._store[self._key(key, today or date.today())] = value

    def get_or_set(self, key: tuple, factory: Callable[[], T], today: date | None = None) -> T:
        full_key = self._key(key, today or date.today())
        if full_key in self._store:
            return self._store[full_key]
        value = factory()
        self._store[full_key] = value
        return value

    def clear(self) -> None:
        self._store.clear()
