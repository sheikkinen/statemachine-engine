"""
FR-FSM-019: Idle-detection precedence in the main event loop.

The adaptive sleep in execute_state_machine() must only select the 500ms
idle tick when the machine is parked in ``waiting``. A machine holding a
non-waiting state (e.g. listening for an external event) must keep the
50ms tick regardless of how long it has been quiet, because tick length
bounds control-socket event-pickup latency.
"""
import time

import pytest

import statemachine_engine.core.engine as engine_module
from statemachine_engine.core.engine import StateMachineEngine

IDLE_TICK = 0.5
ACTIVE_TICK = 0.05


def _make_engine(state: str) -> StateMachineEngine:
    eng = StateMachineEngine(machine_name="test_idle_precedence")
    eng.config = {
        "initial_state": state,
        "transitions": [],
        "actions": {},
        "events": [],
    }
    eng.current_state = state
    return eng


async def _run_one_tick(eng: StateMachineEngine, monkeypatch) -> float:
    """Run the main loop for one iteration and return the sleep it selected."""
    recorded: list[float] = []

    async def fake_sleep(duration: float) -> None:
        recorded.append(duration)
        eng.is_running = False

    monkeypatch.setattr(engine_module.asyncio, "sleep", fake_sleep)
    await eng.execute_state_machine({})
    assert len(recorded) == 1, f"expected exactly one tick, got {recorded}"
    return recorded[0]


@pytest.mark.asyncio
async def test_non_waiting_state_keeps_active_tick_when_stale(monkeypatch):
    """RED: quiet >5s in a non-waiting state must NOT drop to the idle tick."""
    eng = _make_engine("listening")
    eng._last_activity_time = time.time() - 10.0

    tick = await _run_one_tick(eng, monkeypatch)

    assert tick == ACTIVE_TICK


@pytest.mark.asyncio
async def test_waiting_state_stale_selects_idle_tick(monkeypatch):
    eng = _make_engine("waiting")
    eng._last_activity_time = time.time() - 10.0

    tick = await _run_one_tick(eng, monkeypatch)

    assert tick == IDLE_TICK


@pytest.mark.asyncio
async def test_waiting_state_with_recent_activity_keeps_active_tick(monkeypatch):
    eng = _make_engine("waiting")
    eng._last_activity_time = time.time()

    tick = await _run_one_tick(eng, monkeypatch)

    assert tick == ACTIVE_TICK


@pytest.mark.asyncio
async def test_waiting_state_without_activity_selects_idle_tick(monkeypatch):
    eng = _make_engine("waiting")
    assert not hasattr(eng, "_last_activity_time")

    tick = await _run_one_tick(eng, monkeypatch)

    assert tick == IDLE_TICK
