from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.4,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            time.sleep(base_delay_seconds * (2 ** attempt))
    assert last_exc is not None
    raise last_exc
