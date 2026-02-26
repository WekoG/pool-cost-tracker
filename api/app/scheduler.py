from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

RunOnceCallable = Callable[[], Awaitable[None]]


class SyncScheduler:
    def __init__(self, settings: Any, run_once: RunOnceCallable):
        self.settings = settings
        self._run_once = run_once
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._run_lock: asyncio.Lock | None = None

    @property
    def started(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> bool:
        if not self.settings.SCHEDULER_ENABLED:
            return False
        if self.started:
            return False
        self._stop_event = asyncio.Event()
        self._run_lock = asyncio.Lock()
        self._task = asyncio.create_task(self._loop(), name='pool-cost-sync-scheduler')
        return True

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def run_now(self) -> None:
        if self._run_lock is None:
            return
        async with self._run_lock:
            try:
                await self._run_once()
            except Exception:
                logger.exception('Scheduled sync failed')

    async def _loop(self) -> None:
        if self._stop_event is None:
            return
        if self.settings.SCHEDULER_RUN_ON_STARTUP:
            await self.run_now()

        sleep_seconds = max(1, int(self.settings.SCHEDULER_INTERVAL_MINUTES) * 60)
        try:
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_seconds)
                    break
                except asyncio.TimeoutError:
                    await self.run_now()
        except asyncio.CancelledError:
            raise
