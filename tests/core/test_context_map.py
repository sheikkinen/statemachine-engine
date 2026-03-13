"""
NC-120: Tests for event-level context promotion via context_map.

Tests that the engine can:
1. Parse context_map from YAML events config (flat list + dict formats)
2. Promote event payload fields to durable top-level context keys
3. Handle missing/null payload fields gracefully
4. Survive subsequent events overwriting event_data
"""
import pytest

from statemachine_engine.core.engine import StateMachineEngine


@pytest.fixture
def engine():
    """Create a minimal engine instance for testing."""
    engine = StateMachineEngine(machine_name='test_context_map')
    engine.config = {
        'initial_state': 'idle',
        'transitions': [],
        'actions': {},
        'events': [],
    }
    engine.current_state = 'idle'
    engine.context = {}
    return engine


# --- _build_context_map_index tests ---


def test_build_context_map_index_flat_list(engine):
    """Flat list events: → empty index (backward compat)."""
    engine.config['events'] = [
        'transcribed',
        'speak_done',
        'hangup',
    ]
    index = engine._build_context_map_index()
    assert index == {}


def test_build_context_map_index_dict(engine):
    """Dict events with context_map → correct index."""
    engine.config['events'] = {
        'transcribed': {
            'context_map': {
                'user_utterance': 'payload.user_utterance',
            }
        },
        'speak_done': {},
    }
    index = engine._build_context_map_index()
    assert index == {
        'transcribed': {'user_utterance': 'payload.user_utterance'},
    }


def test_build_context_map_index_mixed(engine):
    """Dict events, some with context_map, some without."""
    engine.config['events'] = {
        'incoming_call': {
            'context_map': {
                'call_sid': 'payload.call_sid',
                'caller': 'payload.caller',
            }
        },
        'speak_done': {},
        'transcribed': {
            'context_map': {
                'user_utterance': 'payload.user_utterance',
            }
        },
        'hangup': {},
    }
    index = engine._build_context_map_index()
    assert 'incoming_call' in index
    assert 'transcribed' in index
    assert 'speak_done' not in index
    assert 'hangup' not in index
    assert index['incoming_call'] == {
        'call_sid': 'payload.call_sid',
        'caller': 'payload.caller',
    }


# --- _apply_context_map tests ---


def test_apply_context_map_promotes_field(engine):
    """transcribed event → context['user_utterance'] set."""
    engine._context_map_index = {
        'transcribed': {'user_utterance': 'payload.user_utterance'},
    }
    event = {
        'type': 'transcribed',
        'payload': {'user_utterance': 'Hammas hoito'},
    }
    engine._apply_context_map('transcribed', event)
    assert engine.context['user_utterance'] == 'Hammas hoito'


def test_apply_context_map_survives_overwrite(engine):
    """After speak_done overwrites event_data, user_utterance still in context."""
    engine._context_map_index = {
        'transcribed': {'user_utterance': 'payload.user_utterance'},
    }

    # First event: transcribed with utterance
    transcribed_event = {
        'type': 'transcribed',
        'payload': {'user_utterance': 'Hammas hoito'},
    }
    engine.context['event_data'] = transcribed_event
    engine._apply_context_map('transcribed', transcribed_event)

    # Second event: speak_done with empty payload (overwrites event_data)
    speak_done_event = {
        'type': 'speak_done',
        'payload': {},
    }
    engine.context['event_data'] = speak_done_event
    engine._apply_context_map('speak_done', speak_done_event)

    # user_utterance must survive
    assert engine.context['user_utterance'] == 'Hammas hoito'


def test_apply_context_map_missing_payload_skips(engine):
    """Missing payload field → context unchanged, no error."""
    engine._context_map_index = {
        'transcribed': {'user_utterance': 'payload.user_utterance'},
    }
    event = {
        'type': 'transcribed',
        'payload': {},  # no user_utterance key
    }
    engine._apply_context_map('transcribed', event)
    assert 'user_utterance' not in engine.context


def test_apply_context_map_multiple_fields(engine):
    """incoming_call promotes both call_sid and caller."""
    engine._context_map_index = {
        'incoming_call': {
            'call_sid': 'payload.call_sid',
            'caller': 'payload.caller',
        },
    }
    event = {
        'type': 'incoming_call',
        'payload': {'call_sid': 'CA123', 'caller': '+358401234567'},
    }
    engine._apply_context_map('incoming_call', event)
    assert engine.context['call_sid'] == 'CA123'
    assert engine.context['caller'] == '+358401234567'


def test_apply_context_map_no_mapping(engine):
    """speak_done (no context_map) → nothing promoted, no error."""
    engine._context_map_index = {
        'transcribed': {'user_utterance': 'payload.user_utterance'},
    }
    event = {
        'type': 'speak_done',
        'payload': {},
    }
    engine.context['existing_key'] = 'preserved'
    engine._apply_context_map('speak_done', event)
    # Context unchanged except existing keys
    assert engine.context == {'existing_key': 'preserved'}


def test_apply_context_map_nested_path(engine):
    """Deep path payload.nested.field traversal works."""
    engine._context_map_index = {
        'deep_event': {'deep_value': 'payload.level1.level2.target'},
    }
    event = {
        'type': 'deep_event',
        'payload': {
            'level1': {
                'level2': {
                    'target': 'found_it',
                }
            }
        },
    }
    engine._apply_context_map('deep_event', event)
    assert engine.context['deep_value'] == 'found_it'
