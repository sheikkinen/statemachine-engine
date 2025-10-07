"""
Test ClearEventsAction - Clear pending events from queue

Tests that the action correctly clears stale pending events of specific types.
"""
import pytest
import asyncio
from statemachine_engine.actions.builtin import ClearEventsAction
from statemachine_engine.database.models import get_machine_event_model


class TestClearEventsAction:
    """Test clear_events action"""

    @pytest.mark.asyncio
    async def test_clear_single_event_type(self):
        """Test clearing events of a single type"""

        event_model = get_machine_event_model()

        # Clean up any existing events from previous tests
        existing = event_model.get_pending_events("sdxl_generator")
        for event in existing:
            event_model.mark_event_processed(event['id'])

        # Create test events
        event_model.send_event(
            target_machine="sdxl_generator",
            event_type="ready_for_next_job",
            payload='{"test": "data1"}'
        )
        event_model.send_event(
            target_machine="sdxl_generator",
            event_type="ready_for_next_job",
            payload='{"test": "data2"}'
        )
        event_model.send_event(
            target_machine="sdxl_generator",
            event_type="other_event",
            payload='{"test": "keep_this"}'
        )

        # Verify events exist
        pending = event_model.get_pending_events("sdxl_generator")
        ready_events = [e for e in pending if e['event_type'] == 'ready_for_next_job']
        assert len(ready_events) == 2

        # Clear ready_for_next_job events
        config = {
            "event_types": ["ready_for_next_job"],
            "target_machine": "sdxl_generator",
            "success": "events_cleared"
        }

        action = ClearEventsAction(config)
        result = await action.execute({})

        assert result == "events_cleared"

        # Verify events were cleared
        pending_after = event_model.get_pending_events("sdxl_generator")
        ready_after = [e for e in pending_after if e['event_type'] == 'ready_for_next_job']
        assert len(ready_after) == 0

        # Verify other events remain
        other_after = [e for e in pending_after if e['event_type'] == 'other_event']
        assert len(other_after) == 1

    @pytest.mark.asyncio
    async def test_clear_multiple_event_types(self):
        """Test clearing events of multiple types"""

        event_model = get_machine_event_model()

        # Clean up any existing events from previous tests
        existing = event_model.get_pending_events("test_machine")
        for event in existing:
            event_model.mark_event_processed(event['id'])

        # Create test events
        event_model.send_event(
            target_machine="test_machine",
            event_type="type_a",
            payload='{"test": "a1"}'
        )
        event_model.send_event(
            target_machine="test_machine",
            event_type="type_b",
            payload='{"test": "b1"}'
        )
        event_model.send_event(
            target_machine="test_machine",
            event_type="type_c",
            payload='{"test": "keep"}'
        )

        # Clear multiple types
        config = {
            "event_types": ["type_a", "type_b"],
            "target_machine": "test_machine"
        }

        action = ClearEventsAction(config)
        result = await action.execute({})

        assert result == "events_cleared"

        # Verify cleared
        pending = event_model.get_pending_events("test_machine")
        type_a = [e for e in pending if e['event_type'] == 'type_a']
        type_b = [e for e in pending if e['event_type'] == 'type_b']
        type_c = [e for e in pending if e['event_type'] == 'type_c']

        assert len(type_a) == 0
        assert len(type_b) == 0
        assert len(type_c) == 1

    @pytest.mark.asyncio
    async def test_clear_no_events_found(self):
        """Test clearing when no matching events exist"""

        config = {
            "event_types": ["nonexistent_event"],
            "target_machine": "nonexistent_machine"
        }

        action = ClearEventsAction(config)
        result = await action.execute({})

        assert result == "no_events_to_clear"
