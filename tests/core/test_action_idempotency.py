"""
FR-FSM-009: Action Execution Idempotency Guard

Tests that _execute_state_actions():
1. Aborts mid-sequence when an action triggers a state transition
2. Marks transition-triggering actions as completed (skip on next tick)
3. VB-006: Runs non-transition actions once per state entry by default
4. Allows polling actions to repeat only with explicit opt-in
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
    async def test_non_transition_action_runs_once_per_entry_by_default(self, engine):
        """VB-006 default: non-transition action executes once per state entry."""
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
        assert call_count == 1

        await engine._execute_state_actions()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_repeatable_polling_action_repeats_every_tick(self, engine):
        """VB-006 opt-in: repeatable polling action runs on each tick."""
        call_count = 0

        engine.config["actions"]["idle"] = [
            {"type": "check_database_queue", "repeatable": True},
        ]

        async def mock_execute(action_config):
            nonlocal call_count
            call_count += 1

        engine._execute_action = mock_execute

        await engine._execute_state_actions()
        assert call_count == 1

        await engine._execute_state_actions()
        assert call_count == 2

        await engine._execute_state_actions()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_run_policy_repeat_per_tick_repeats_every_tick(self, engine):
        """VB-006 opt-in: run_policy=repeat_per_tick runs on each tick."""
        call_count = 0

        engine.config["actions"]["idle"] = [
            {"type": "check_database_queue", "run_policy": "repeat_per_tick"},
        ]

        async def mock_execute(action_config):
            nonlocal call_count
            call_count += 1

        engine._execute_action = mock_execute

        await engine._execute_state_actions()
        assert call_count == 1

        await engine._execute_state_actions()
        assert call_count == 2

        await engine._execute_state_actions()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_repeatable_string_false_does_not_repeat(self, engine):
        """String 'false' must not opt in to repeat-per-tick behavior."""
        call_count = 0

        engine.config["actions"]["idle"] = [
            {"type": "check_database_queue", "repeatable": "false"},
        ]

        async def mock_execute(action_config):
            nonlocal call_count
            call_count += 1

        engine._execute_action = mock_execute

        await engine._execute_state_actions()
        assert call_count == 1

        await engine._execute_state_actions()
        assert call_count == 1


class TestSelfLoopPreservation:
    """Amendment 3: self-loops do NOT reset _completed_action_indices."""

    @pytest.mark.asyncio
    async def test_self_loop_preserves_completed_no_infinite_alternation(self, engine):
        """Self-loop must NOT cause a one-shot action to re-fire every tick.

        Scenario: state "working" has [A1(one-shot), A2(repeatable poll)].
        A1 triggers a self-loop on first tick. On tick 2, A1 must be
        skipped and A2 must execute.
        """
        call_log = []

        engine.current_state = "working"
        engine.config["actions"]["working"] = [
            {"type": "bash", "command": "one_shot"},
            {"type": "check_queue", "repeatable": True},
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


class TestCrossStateLeak:
    """FR-FSM-011: _completed_action_indices must not leak across states.

    When action[0] in state A triggers a transition to state B,
    state B's action[0] must still execute — the index belongs to the
    old state and must not contaminate the new state's action set.
    """

    @pytest.mark.asyncio
    async def test_cross_state_idx0_not_skipped(self, engine):
        """State B's idx=0 action fires after state A's idx=0 triggered transition.

        Reproduces the ninchat_voice bug: warming_up[0] triggers "warmed",
        transitions to connecting_ninchat, but connecting_ninchat[0] is
        silently skipped because 0 leaked into _completed_action_indices.
        """
        call_log = []

        engine.config["transitions"] = [
            {"from": "idle", "event": "go", "to": "working"},
            {"from": "working", "event": "done", "to": "idle"},
        ]
        engine.config["actions"]["idle"] = [
            {"type": "state_a_action"},  # idx=0: triggers "go"
        ]
        engine.config["actions"]["working"] = [
            {"type": "state_b_action"},  # idx=0: must NOT be skipped
        ]
        engine.current_state = "idle"

        async def mock_execute(action_config):
            action_type = action_config["type"]
            call_log.append(action_type)
            if action_type == "state_a_action":
                await engine.process_event("go")

        engine._execute_action = mock_execute

        # Tick 1: idle's action fires → transitions to working
        await engine._execute_state_actions()
        assert engine.current_state == "working"
        assert "state_a_action" in call_log

        # Critical assertion: _completed_action_indices must be empty
        # for the NEW state after a cross-state transition
        assert engine._completed_action_indices == set(), (
            f"Cross-state leak: _completed_action_indices={engine._completed_action_indices} "
            f"should be empty after transitioning from idle→working"
        )

        # Tick 2: working's action at idx=0 must fire
        call_log.clear()
        await engine._execute_state_actions()
        assert "state_b_action" in call_log, (
            f"State B's idx=0 action was skipped! call_log={call_log}. "
            f"_completed_action_indices={engine._completed_action_indices}"
        )

    @pytest.mark.asyncio
    async def test_three_state_chain_all_idx0_fire(self, engine):
        """Chain A→B→C where each state's idx=0 triggers the next transition.

        All three actions must execute exactly once.
        """
        call_log = []

        engine.config["transitions"] = [
            {"from": "idle", "event": "go", "to": "working"},
            {"from": "working", "event": "done", "to": "finished"},
        ]
        engine.config["actions"]["idle"] = [
            {"type": "action_a"},
        ]
        engine.config["actions"]["working"] = [
            {"type": "action_b"},
        ]
        engine.config["actions"]["finished"] = [
            {"type": "action_c"},
        ]
        engine.current_state = "idle"

        async def mock_execute(action_config):
            action_type = action_config["type"]
            call_log.append(action_type)
            if action_type == "action_a":
                await engine.process_event("go")
            elif action_type == "action_b":
                await engine.process_event("done")

        engine._execute_action = mock_execute

        # Tick 1: A fires → go → working
        await engine._execute_state_actions()
        assert engine.current_state == "working"
        assert call_log == ["action_a"]

        # Tick 2: B fires → done → finished
        call_log.clear()
        await engine._execute_state_actions()
        assert engine.current_state == "finished"
        assert call_log == ["action_b"]

        # Tick 3: C fires (no transition)
        call_log.clear()
        await engine._execute_state_actions()
        assert call_log == ["action_c"]


class TestInitialization:
    """_state_entry_gen and _completed_action_indices must exist on fresh engine."""

    def test_engine_has_idempotency_attributes(self, engine):
        """Engine.__init__ must initialize tracking attributes."""
        assert hasattr(engine, "_state_entry_gen")
        assert hasattr(engine, "_completed_action_indices")
        assert engine._state_entry_gen == 0
        assert engine._completed_action_indices == set()
