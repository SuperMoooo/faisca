"""Politeness towards external services: few requests at once, spaced out, per service.

Every search fans out to many catalogues at the same time, so the app must
not become a way to hammer any one of them. Each service gets a semaphore
(at most N requests in flight) and a minimum gap between the start of two
requests. Both are per process, which is all this single-container app runs.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request

from faisca.core.config import Settings


class RequestThrottle:
    """Hands out permission to call one service, keeping to its concurrency and spacing."""

    def __init__(self, max_concurrent: int, min_interval_seconds: float) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._min_interval_seconds = min_interval_seconds
        self._spacing_lock = asyncio.Lock()
        self._last_start = 0.0

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Waits for a free slot and the minimum gap, then lets one request through."""
        async with self._semaphore:
            await self._wait_for_spacing()
            yield

    async def _wait_for_spacing(self) -> None:
        # The lock makes requests take turns measuring the gap; without it two
        # waiting requests would both see the same last start and fire together.
        async with self._spacing_lock:
            wait = self._last_start + self._min_interval_seconds - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_start = time.monotonic()


class ThrottleRegistry:
    """One `RequestThrottle` per external service id, created on first use."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._throttles: dict[str, RequestThrottle] = {}

    def for_service(self, service_id: str) -> RequestThrottle:
        """The throttle for [service_id] (a target or source id from targets.yaml)."""
        if service_id not in self._throttles:
            self._throttles[service_id] = RequestThrottle(
                self._settings.max_concurrent_requests_per_target,
                self._settings.min_seconds_between_requests,
            )
        return self._throttles[service_id]


def get_throttles(request: Request) -> ThrottleRegistry:
    """The app's registry, shared by every request so the limits hold across them."""
    registry: ThrottleRegistry = request.app.state.throttles
    return registry


ThrottlesDep = Annotated[ThrottleRegistry, Depends(get_throttles)]
