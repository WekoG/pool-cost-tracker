import asyncio
from types import SimpleNamespace

from api.app.scheduler import SyncScheduler


def make_settings(**kwargs):
    base = {
        'SCHEDULER_ENABLED': False,
        'SCHEDULER_INTERVAL_MINUTES': 360,
        'SCHEDULER_RUN_ON_STARTUP': True,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_scheduler_disabled_starts_no_task():
    runs = []

    async def run_once():
        runs.append('run')

    scheduler = SyncScheduler(make_settings(SCHEDULER_ENABLED=False), run_once)

    async def scenario():
        started = await scheduler.start()
        assert started is False
        assert scheduler.started is False
        assert runs == []

    asyncio.run(scenario())


def test_scheduler_enabled_initializes_and_stops_without_waiting():
    runs = []

    async def run_once():
        runs.append('run')

    scheduler = SyncScheduler(
        make_settings(SCHEDULER_ENABLED=True, SCHEDULER_RUN_ON_STARTUP=False, SCHEDULER_INTERVAL_MINUTES=9999),
        run_once,
    )

    async def scenario():
        started = await scheduler.start()
        assert started is True
        assert scheduler.started is True
        started_again = await scheduler.start()
        assert started_again is False
        await scheduler.stop()
        assert scheduler.started is False
        assert runs == []

    asyncio.run(scenario())


def test_scheduler_run_on_startup_executes_once_quickly():
    runs = []

    async def scenario():
        gate = asyncio.Event()

        async def run_once():
            runs.append('run')
            gate.set()

        scheduler = SyncScheduler(
            make_settings(SCHEDULER_ENABLED=True, SCHEDULER_RUN_ON_STARTUP=True, SCHEDULER_INTERVAL_MINUTES=9999),
            run_once,
        )
        await scheduler.start()
        await asyncio.wait_for(gate.wait(), timeout=1.0)
        await scheduler.stop()
        assert runs == ['run']

    asyncio.run(scenario())
