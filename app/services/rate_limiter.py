from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

AsyncSleep = Callable[[float], Awaitable[None]]
MonotonicClock = Callable[[], float]


class HostRateLimiter:
    """Serialize request starts to a configured per-host maximum rate."""

    def __init__(
        self,
        requests_per_second: float,
        *,
        sleep: AsyncSleep = asyncio.sleep,
        clock: MonotonicClock = time.monotonic,
    ) -> None:
        self._interval = 1 / requests_per_second
        self._sleep = sleep
        self._clock = clock
        self._next_request_at = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            delay = max(0.0, self._next_request_at - now)
            if delay:
                await self._sleep(delay)
            observed = self._clock()
            self._next_request_at = (
                max(observed, self._next_request_at) + self._interval
            )
