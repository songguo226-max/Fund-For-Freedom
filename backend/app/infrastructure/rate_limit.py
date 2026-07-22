from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    minute: int
    count: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}

    def acquire(self, key: str, *, limit_per_minute: int) -> bool:
        if limit_per_minute <= 0:
            return True
        now_minute = int(time.time() // 60)
        bucket = self._buckets.get(key)
        if bucket is None or bucket.minute != now_minute:
            self._buckets[key] = _Bucket(minute=now_minute, count=1)
            return True
        if bucket.count >= limit_per_minute:
            return False
        bucket.count += 1
        return True
