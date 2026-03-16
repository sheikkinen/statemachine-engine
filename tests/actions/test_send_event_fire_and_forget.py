"""VB-007 tests for send_event fire_and_forget behavior."""

from unittest.mock import AsyncMock

import pytest

from statemachine_engine.actions.builtin.send_event_action import SendEventAction
from statemachine_engine.core.engine import StateMachineEngine


@pytest.fixture
def base_context():
    return {
        "machine_name": "source_machine",
        "current_state": "idle",
        "event_data": {"payload": {}},
    }


@pytest.mark.asyncio
async def test_send_event_default_returns_event_sent(base_context, monkeypatch):
    action = SendEventAction(
        {
            "target_machine": "target",
            "event_type": "user_spoke",
        }
    )

    monkeypatch.setattr(action, "_send_via_socket", lambda payload, job_id, machine_name: True)

    event = await action.execute(base_context)
    assert event == "event_sent"


@pytest.mark.asyncio
async def test_send_event_fire_and_forget_true_returns_none(base_context, monkeypatch):
    action = SendEventAction(
        {
            "target_machine": "target",
            "event_type": "user_spoke",
            "fire_and_forget": True,
        }
    )

    monkeypatch.setattr(action, "_send_via_socket", lambda payload, job_id, machine_name: True)

    event = await action.execute(base_context)
    assert event is None


@pytest.mark.asyncio
async def test_send_event_fire_and_forget_false_string_returns_success_event(
    base_context, monkeypatch
):
    action = SendEventAction(
        {
            "target_machine": "target",
            "event_type": "user_spoke",
            "fire_and_forget": "false",
        }
    )

    monkeypatch.setattr(action, "_send_via_socket", lambda payload, job_id, machine_name: True)

    event = await action.execute(base_context)
    assert event == "event_sent"


@pytest.mark.asyncio
async def test_engine_processes_event_when_fire_and_forget_not_enabled(monkeypatch):
    engine = StateMachineEngine(machine_name="vb007-engine")
    engine.context = {
        "machine_name": "source_machine",
        "current_state": "idle",
        "event_data": {"payload": {}},
    }
    engine.config = {"actions": {}, "transitions": []}

    process_event_mock = AsyncMock(return_value=False)
    engine.process_event = process_event_mock

    monkeypatch.setattr(
        SendEventAction,
        "_send_via_socket",
        lambda self, payload, job_id, machine_name: True,
    )

    await engine._execute_pluggable_action(
        "send_event",
        {
            "target_machine": "target",
            "event_type": "user_spoke",
        },
    )

    process_event_mock.assert_awaited_once_with("event_sent")


@pytest.mark.asyncio
async def test_engine_skips_process_event_with_fire_and_forget_true(monkeypatch):
    engine = StateMachineEngine(machine_name="vb007-engine")
    engine.context = {
        "machine_name": "source_machine",
        "current_state": "idle",
        "event_data": {"payload": {}},
    }
    engine.config = {"actions": {}, "transitions": []}

    process_event_mock = AsyncMock(return_value=False)
    engine.process_event = process_event_mock

    monkeypatch.setattr(
        SendEventAction,
        "_send_via_socket",
        lambda self, payload, job_id, machine_name: True,
    )

    await engine._execute_pluggable_action(
        "send_event",
        {
            "target_machine": "target",
            "event_type": "user_spoke",
            "fire_and_forget": True,
        },
    )

    process_event_mock.assert_not_awaited()
