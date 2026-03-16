"""
FR-FSM-009: Action Execution Idempotency Guard

Tests that _execute_state_actions():
1. Aborts mid-sequence when an action triggers a state transition
2. Marks transition-triggering actions as completed (skip on next tick)
3. Lets polling actions (no transition) repeat every tick
4. Preserves completed set on self-loops (no infinite alternation)
5. Resets completed set on transitions to a different state
"""
import pytest

from statemachine_engine.core.engine import StateMachineEngine


@pytest.fixture
def engine():
    """Create a minimal engine with idempotency tracking."""
    eng = StateMachineEngine(machine_name="test_idempotency")
    eng.config = {
        "initial_state": "idle",
        "transitions": [
            {"from": "idle", "event": "go", "to": "working"},
            {"from": "working", "event": "done", "to": "idle"},
            {"from": "working", "event": "retry", "to": "working"},  # self-loop
        ],
        "actions": {},
        "events": [],
    }
    eng.current_state = "idle"
    eng.context = {}
    return eng


class TestMidSequenceAbort:
    """Amendment 1: mid-sequence abort is the primary guard."""

    @pytest.mark.asyncio
    async def test_mid_sequence_transition_aborts_remaining_actions(self, engine):
        """When action[0] triggers a transition, action[1] must NOT execute."""
        call_log = []

        engine.config["actions"]["idle"] = [
            {"type": "bash", "command": "echo first"},
            {"type": "bash", "command": "echo second"},
        ]

        original_execute = engine._execute_action

        async def mock_execute(action_config):
            call_log.append(action_config["command"])
            if action_config["command"] == "echo first":
                # Simulate: this action triggers a state transition
                await engine.process_event("go")

        engine._execute_action = mock_execute
        await engine._execute_state_actions()

        assert call_log == ["echo first"], (
            f"Expected only first action, got: {call_log}"
        )

    @pytest.mark.asyncio
    async def test_all_actions_run_when_no_transition(self, engine):
        """When no action triggers a transition, all actions execute."""
        call_log = []

        engine.config["actions"]["idle"] = [
            {"type": "log", "message": "a"},
            {"type": "log", "message": "b"},
            {"type": "log", "message": "c"},
        ]

        async def mock_execute(action_config):
            call_log.append(action_config["message"])

        engine._execute_action = mock_execute
        await engine._execute_state_actions()

        assert call_log == ["a", "b", "c"]


class TestRuntimeOneShot:
    """Amendment 2: runtime detection — actions that triggered transitions
    are marked completed and skipped on subsequent ticks."""

    @pytest.mark.asyncio
    async def test_transition_action_runs_once_per_state_entry(self, engine):
        """A bash action that triggers transition runs once, then is skipped."""
        call_count = 0

        engine.current_state = "working"
        engine.config["actions"]["working"] = [
            {"type": "bash", "command": "echo side_effect"},
        ]
        # Add a transition back to working (self-loop via "retry")
        # so the engine stays in "working" after the action fires

        async def mock_execute(action_config):
            nonlocal call_count
            call_count += 1
            # Simulate: bash triggers a self-loop transition
            await engine.process_event("retry")

        engine._execute_action = mock_execute

        # Tick 1: action runs and triggers transition
        await engine._execute_state_actions()
        assert call_count == 1

        # Tick 2: same state, action should be skipped (self-loop preserved completed set)
        await engine._execute_state_actions()
        assert call_count == 1, "Action should not re-fire after self-loop"

    @pytest.mark.asyncio
    async def test_polling_action_repeats_every_tick(self, engine):
        """An action that does NOT trigger a transition repeats every tick."""
        call_count = 0

        engine.config["actions"]["idle"] = [
            {"type": "check_database_queue"},
        ]

        async def mock_execute(action_config):
            nonlocal call_count
            call_count += 1
            # No transition triggered — polling action

        engine._execute_action = mock_execute

        await engine._execute_state_actions()
        assert call_count == 1

        await engine._execute_state_actions()
        assert call_count == 2

        await engine._execute_state_actions()
        assert call_count == 3


class TestSelfLoopPreservation:
    """Amendment 3: self-loops do NOT reset _completed_action_indices."""

    @pytest.mark.asyncio
    async def test_self_loop_preserves_completed_no_infinite_alternation(self, engine):
        """Self-loop must NOT cause a one-shot action to re-fire every tick.

        Scenario: state "working" has [A1(one-shot), A2(poll)].
        A1 triggers a self-loop on first tick. On tick 2, A1 must be
        skipped and A2 must execute.
        """
        call_log = []

        engine.current_state = "working"
        engine.config["actions"]["working"] = [
            {"type": "bash", "command": "one_shot"},
            {"type": "check_queue"},
        ]

        first_tick = True

        async def mock_execute(action_config):
            nonlocal first_tick
            action_type = action_config.get("type")
            call_log.append(action_type)
            if action_type == "bash" and first_tick:
                first_tick = False
                # Triggers self-loop
                await engine.process_event("retry")

        engine._execute_action = mock_execute

        # Tick 1: bash runs → self-loop → mid-sequence abort (check_queue skipped)
        await engine._execute_state_actions()
        assert call_log == ["bash"], f"Tick 1: {call_log}"

        # Tick 2: bash is completed (skipped), check_queue runs
        call_log.clear()
        await engine._execute_state_actions()
        assert call_log == ["check_queue"], f"Tick 2: {call_log}"

        # Tick 3: same — bash still skipped, check_queue repeats
        call_log.clear()
        await engine._execute_state_actions()
        assert call_log == ["check_queue"], f"Tick 3: {call_log}"


class TestDifferentStateResets:
    """Entering a genuinely different state must reset completed actions."""

    @pytest.mark.asyncio
    async def test_reentry_from_different_state_resets_completed(self, engine):
        """After transitioning away and back, all actions run fresh."""
        call_count = 0

        engine.current_state = "working"
        engine.config["actions"]["working"] = [
            {"type": "bash", "command": "side_effect"},
        ]

        async def mock_execute(action_config):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First time: trigger transition to idle
                await engine.process_event("done")

        engine._execute_action = mock_execute

        # Tick 1 in "working": bash runs, transitions to "idle"
        await engine._execute_state_actions()
        assert call_count == 1
        assert engine.current_state == "idle"

        # Manually return to "working" (simulating an external event)
        await engine.process_event("go")
        assert engine.current_state == "working"

        # Tick 2 in "working": bash should run again (fresh state entry)
        await engine._execute_state_actions()
        assert call_count == 2, "Action should re-fire after re-entry from different state"


class TestInitialization:
    """_state_entry_gen and _completed_action_indices must exist on fresh engine."""

    def test_engine_has_idempotency_attributes(self, engine):
        """Engine.__init__ must initialize tracking attributes."""
        assert hasattr(engine, "_state_entry_gen")
        assert hasattr(engine, "_completed_action_indices")
        assert engine._state_entry_gen == 0
        assert engine._completed_action_indices == set()
