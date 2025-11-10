"""
Test suite for the shared variable interpolation utility module.

This module provides comprehensive test coverage for the interpolation
functionality that will be extracted from engine.py and shared across
all actions that need variable substitution.

Tests follow TDD approach - written before implementation.
"""
import pytest


@pytest.fixture
def sample_context():
    """Standard context for testing"""
    return {
        'job_id': 'test_123',
        'status': 'pending',
        'user': 'alice',
        'priority': 5,
        'timeout': 30.5,
        'enabled': True
    }


@pytest.fixture
def nested_context():
    """Context with nested structures for testing dot notation"""
    return {
        'job_id': 'nested_456',
        'event_data': {
            'event_name': 'start_job',
            'payload': {
                'job_id': 'nested_job_789',
                'pony_prompt': 'A beautiful portrait',
                'input_image': '/path/to/image.jpg',
                'settings': {
                    'format': 'png',
                    'quality': 95
                }
            }
        },
        'metadata': {
            'timestamp': '2025-11-10T10:00:00Z',
            'version': '1.0'
        }
    }


# ==============================================================================
# Tests for interpolate_value() - Single string interpolation
# ==============================================================================

def test_interpolate_value_simple_variable(sample_context):
    """Test simple variable substitution like {job_id}"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Processing job {job_id} with status {status}"
    result = interpolate_value(template, sample_context)
    
    assert result == "Processing job test_123 with status pending"


def test_interpolate_value_nested_variable(nested_context):
    """Test nested variable substitution like {event_data.payload.job_id}"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Job {event_data.payload.job_id}: {event_data.payload.pony_prompt}"
    result = interpolate_value(template, nested_context)
    
    assert result == "Job nested_job_789: A beautiful portrait"


def test_interpolate_value_deeply_nested(nested_context):
    """Test deeply nested paths like {event_data.payload.settings.format}"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Format: {event_data.payload.settings.format}, Quality: {event_data.payload.settings.quality}"
    result = interpolate_value(template, nested_context)
    
    assert result == "Format: png, Quality: 95"


def test_interpolate_value_missing_variable_keeps_placeholder(sample_context):
    """Test that missing variables are left as placeholders"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Job {job_id} has {nonexistent_var}"
    result = interpolate_value(template, sample_context)
    
    assert result == "Job test_123 has {nonexistent_var}"


def test_interpolate_value_missing_nested_keeps_placeholder(nested_context):
    """Test that missing nested paths are left as placeholders"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Missing: {event_data.nonexistent.path}"
    result = interpolate_value(template, nested_context)
    
    assert result == "Missing: {event_data.nonexistent.path}"


def test_interpolate_value_partial_nested_keeps_placeholder(nested_context):
    """Test that partially valid nested paths keep placeholder"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    # event_data.payload exists, but settings.nonexistent does not
    template = "Value: {event_data.payload.settings.nonexistent}"
    result = interpolate_value(template, nested_context)
    
    assert result == "Value: {event_data.payload.settings.nonexistent}"


def test_interpolate_value_numeric_to_string(sample_context):
    """Test that numeric values in context are converted to strings when mixed with text"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Priority={priority}, Timeout={timeout}, Enabled={enabled}"
    result = interpolate_value(template, sample_context)
    
    assert result == "Priority=5, Timeout=30.5, Enabled=True"


def test_interpolate_value_only_placeholder():
    """Test string that is only a placeholder preserves original type"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    # When template is ONLY a placeholder, preserve original type
    assert interpolate_value("{job_id}", {'job_id': 'test_123'}) == 'test_123'
    assert interpolate_value("{count}", {'count': 42}) == 42
    assert interpolate_value("{enabled}", {'enabled': True}) is True
    assert interpolate_value("{items}", {'items': [1, 2, 3]}) == [1, 2, 3]
    assert interpolate_value("{data}", {'data': {'key': 'val'}}) == {'key': 'val'}


def test_interpolate_value_type_preservation():
    """Test that single-placeholder templates preserve original types"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    context = {
        'count': 42,
        'percentage': 95.5,
        'enabled': True,
        'disabled': False,
        'items': ['a', 'b', 'c'],
        'data': {'nested': 'value'},
        'none_val': None
    }
    
    # Single placeholders preserve type
    assert interpolate_value("{count}", context) == 42
    assert isinstance(interpolate_value("{count}", context), int)
    
    assert interpolate_value("{percentage}", context) == 95.5
    assert isinstance(interpolate_value("{percentage}", context), float)
    
    assert interpolate_value("{enabled}", context) is True
    assert interpolate_value("{disabled}", context) is False
    
    assert interpolate_value("{items}", context) == ['a', 'b', 'c']
    assert isinstance(interpolate_value("{items}", context), list)
    
    assert interpolate_value("{data}", context) == {'nested': 'value'}
    assert isinstance(interpolate_value("{data}", context), dict)
    
    # Mixed text converts to string
    assert interpolate_value("Count: {count}", context) == "Count: 42"
    assert isinstance(interpolate_value("Count: {count}", context), str)


def test_interpolate_value_nested_type_preservation():
    """Test that nested paths in single-placeholder templates preserve types"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    context = {
        'event_data': {
            'payload': {
                'user': {
                    'id': 123,
                    'name': 'Alice'
                },
                'items': ['item1', 'item2'],
                'count': 42
            }
        }
    }
    
    # Single nested placeholder preserves type
    assert interpolate_value("{event_data.payload.user.id}", context) == 123
    assert isinstance(interpolate_value("{event_data.payload.user.id}", context), int)
    
    assert interpolate_value("{event_data.payload.items}", context) == ['item1', 'item2']
    assert isinstance(interpolate_value("{event_data.payload.items}", context), list)
    
    assert interpolate_value("{event_data.payload.count}", context) == 42
    
    # Mixed text converts to string
    assert interpolate_value("User {event_data.payload.user.id}", context) == "User 123"
    assert isinstance(interpolate_value("User {event_data.payload.user.id}", context), str)


def test_interpolate_value_empty_context():
    """Test interpolation with empty context leaves placeholders"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Job {job_id} status {status}"
    result = interpolate_value(template, {})
    
    assert result == "Job {job_id} status {status}"


def test_interpolate_value_special_characters(sample_context):
    """Test that special characters in values are preserved"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    context = {
        'command': 'echo "Hello World"',
        'path': '/tmp/data with spaces/file.txt',
        'regex': r'\d+\.\d+',
        'json': '{"key": "value"}'
    }
    
    template = "cmd={command}, path={path}, regex={regex}, json={json}"
    result = interpolate_value(template, context)
    
    assert result == 'cmd=echo "Hello World", path=/tmp/data with spaces/file.txt, regex=\\d+\\.\\d+, json={"key": "value"}'


def test_interpolate_value_nested_type_preservation():
    """Test that nested paths in single-placeholder templates preserve types"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    context = {
        'event_data': {
            'payload': {
                'user': {
                    'id': 123,
                    'name': 'Alice'
                },
                'items': ['item1', 'item2'],
                'count': 42
            }
        }
    }
    
    # Single nested placeholder preserves type
    assert interpolate_value("{event_data.payload.user.id}", context) == 123
    assert isinstance(interpolate_value("{event_data.payload.user.id}", context), int)
    
    assert interpolate_value("{event_data.payload.items}", context) == ['item1', 'item2']
    assert isinstance(interpolate_value("{event_data.payload.items}", context), list)
    
    assert interpolate_value("{event_data.payload.count}", context) == 42
    
    # Mixed text converts to string
    assert interpolate_value("User {event_data.payload.user.id}", context) == "User 123"
    assert isinstance(interpolate_value("User {event_data.payload.user.id}", context), str)


def test_interpolate_value_unicode_characters():
    """Test that unicode characters in context values are preserved"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    context = {
        'emoji': '🎨✨',
        'chinese': '你好',
        'arabic': 'مرحبا',
        'special': 'Ñoño'
    }
    
    template = "Emoji: {emoji}, Chinese: {chinese}, Arabic: {arabic}, Special: {special}"
    result = interpolate_value(template, context)
    
    assert result == "Emoji: 🎨✨, Chinese: 你好, Arabic: مرحبا, Special: Ñoño"


# ==============================================================================
# Tests for interpolate_config() - Recursive structure interpolation
# ==============================================================================

def test_interpolate_config_flat_dict(sample_context):
    """Test interpolating flat dictionary"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'log',
        'message': 'Job {job_id} is {status}',
        'level': 'info'
    }
    
    result = interpolate_config(config, sample_context)
    
    assert result['message'] == 'Job test_123 is pending'
    assert result['level'] == 'info'
    assert result['type'] == 'log'


def test_interpolate_config_nested_dict(sample_context):
    """Test interpolating nested dictionaries"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'bash',
        'command': 'process {job_id}',
        'params': {
            'user': '{user}',
            'output': '/tmp/{job_id}.txt',
            'priority': '{priority}'
        }
    }
    
    result = interpolate_config(config, sample_context)
    
    assert result['command'] == 'process test_123'
    assert result['params']['user'] == 'alice'
    assert result['params']['output'] == '/tmp/test_123.txt'
    assert result['params']['priority'] == 5  # Type preserved for single placeholder


def test_interpolate_config_list_values(sample_context):
    """Test interpolating string values in lists"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'multi_step',
        'steps': [
            'step1 {job_id}',
            'step2 {status}',
            'step3 literal',
            'step4 {user}'
        ]
    }
    
    result = interpolate_config(config, sample_context)
    
    assert result['steps'][0] == 'step1 test_123'
    assert result['steps'][1] == 'step2 pending'
    assert result['steps'][2] == 'step3 literal'
    assert result['steps'][3] == 'step4 alice'


def test_interpolate_config_preserves_non_string_types(sample_context):
    """Test that non-string types are preserved unchanged"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'complex',
        'message': 'Job {job_id}',
        'timeout': 30,
        'retry': True,
        'threshold': 0.95,
        'tags': None,
        'count': 0,
        'enabled': False
    }
    
    result = interpolate_config(config, sample_context)
    
    assert result['message'] == 'Job test_123'
    assert result['timeout'] == 30
    assert result['retry'] is True
    assert result['threshold'] == 0.95
    assert result['tags'] is None
    assert result['count'] == 0
    assert result['enabled'] is False


def test_interpolate_config_deeply_nested_structures(sample_context):
    """Test interpolation in deeply nested structures"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'workflow',
        'steps': {
            'prepare': {
                'actions': [
                    {
                        'type': 'log',
                        'message': 'Preparing {job_id}'
                    },
                    {
                        'type': 'bash',
                        'command': 'setup {status} for {user}',
                        'params': {
                            'priority': '{priority}'
                        }
                    }
                ]
            }
        }
    }
    
    result = interpolate_config(config, sample_context)
    
    assert result['steps']['prepare']['actions'][0]['message'] == 'Preparing test_123'
    assert result['steps']['prepare']['actions'][1]['command'] == 'setup pending for alice'
    assert result['steps']['prepare']['actions'][1]['params']['priority'] == 5  # Type preserved


def test_interpolate_config_list_of_dicts(sample_context):
    """Test interpolating list containing dictionaries"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'actions': [
            {'cmd': 'start {job_id}', 'user': '{user}'},
            {'cmd': 'status {job_id}', 'priority': '{priority}'},
            {'cmd': 'literal command', 'value': 42}
        ]
    }
    
    result = interpolate_config(config, sample_context)
    
    assert result['actions'][0]['cmd'] == 'start test_123'
    assert result['actions'][0]['user'] == 'alice'
    assert result['actions'][1]['cmd'] == 'status test_123'
    assert result['actions'][1]['priority'] == 5  # Type preserved for single placeholder
    assert result['actions'][2]['cmd'] == 'literal command'
    assert result['actions'][2]['value'] == 42


def test_interpolate_config_mixed_nested_types():
    """Test mixed nesting of dicts, lists, and primitives"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    context = {'id': 'test', 'env': 'prod'}
    
    config = {
        'name': '{id}',
        'settings': {
            'environments': [
                {'name': '{env}', 'active': True},
                {'name': 'dev', 'active': False}
            ],
            'paths': ['/tmp/{id}', '/var/{env}', '/etc/literal']
        },
        'metadata': {
            'tags': ['tag_{id}', 'env_{env}'],
            'count': 5
        }
    }
    
    result = interpolate_config(config, context)
    
    assert result['name'] == 'test'
    assert result['settings']['environments'][0]['name'] == 'prod'
    assert result['settings']['environments'][0]['active'] is True
    assert result['settings']['environments'][1]['name'] == 'dev'
    assert result['settings']['paths'][0] == '/tmp/test'
    assert result['settings']['paths'][1] == '/var/prod'
    assert result['settings']['paths'][2] == '/etc/literal'
    assert result['metadata']['tags'][0] == 'tag_test'
    assert result['metadata']['tags'][1] == 'env_prod'
    assert result['metadata']['count'] == 5


def test_interpolate_config_empty_structures():
    """Test interpolation with empty dict/list structures"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    context = {'id': 'test'}
    
    config = {
        'empty_dict': {},
        'empty_list': [],
        'normal': '{id}'
    }
    
    result = interpolate_config(config, context)
    
    assert result['empty_dict'] == {}
    assert result['empty_list'] == []
    assert result['normal'] == 'test'


def test_interpolate_config_with_nested_context(nested_context):
    """Test using nested context from event payload"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'bash',
        'command': 'process {job_id} --input {event_data.payload.input_image}',
        'description': 'Prompt: {event_data.payload.pony_prompt}',
        'format': '{event_data.payload.settings.format}',
        'timestamp': '{metadata.timestamp}'
    }
    
    result = interpolate_config(config, nested_context)
    
    assert result['command'] == 'process nested_456 --input /path/to/image.jpg'
    assert result['description'] == 'Prompt: A beautiful portrait'
    assert result['format'] == 'png'
    assert result['timestamp'] == '2025-11-10T10:00:00Z'


def test_interpolate_config_immutable_original():
    """Test that original config is not modified"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    context = {'id': 'test'}
    original = {
        'message': '{id}',
        'nested': {'value': '{id}'}
    }
    
    # Make a copy to compare
    import copy
    original_copy = copy.deepcopy(original)
    
    result = interpolate_config(original, context)
    
    # Result should be interpolated
    assert result['message'] == 'test'
    assert result['nested']['value'] == 'test'
    
    # Original should be unchanged
    assert original == original_copy
    assert original['message'] == '{id}'
    assert original['nested']['value'] == '{id}'


def test_interpolate_config_empty_context():
    """Test interpolation with empty context leaves placeholders"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    config = {
        'type': 'log',
        'message': 'Job {job_id} status {status}'
    }
    
    result = interpolate_config(config, {})
    
    assert result['message'] == 'Job {job_id} status {status}'


# ==============================================================================
# Edge cases and error handling
# ==============================================================================

def test_interpolate_value_context_none():
    """Test interpolation with None context"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    template = "Job {job_id}"
    result = interpolate_value(template, None)
    
    # Should handle gracefully, leaving placeholders
    assert result == "Job {job_id}"


def test_interpolate_config_config_none():
    """Test interpolation with None config"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    context = {'id': 'test'}
    result = interpolate_config(None, context)
    
    # Should return None unchanged
    assert result is None


def test_interpolate_value_circular_reference_safe():
    """Test that circular references in context don't cause issues"""
    from statemachine_engine.utils.interpolation import interpolate_value
    
    # Context values are just used for lookup, not traversed infinitely
    context = {'id': 'test', 'ref': '{id}'}
    
    template = "Value: {id}, Ref: {ref}"
    result = interpolate_value(template, context)
    
    # Should interpolate once, not recursively
    assert result == "Value: test, Ref: {id}"


def test_interpolate_config_with_callable_values():
    """Test that callable values in context are handled"""
    from statemachine_engine.utils.interpolation import interpolate_config
    
    def my_function():
        return "result"
    
    context = {
        'id': 'test',
        'func': my_function
    }
    
    config = {
        'message': 'ID: {id}',
        'data': '{func}'
    }
    
    result = interpolate_config(config, context)
    
    assert result['message'] == 'ID: test'
    # Function is returned as-is when it's a single placeholder (type preserved)
    assert result['data'] == my_function or callable(result['data'])
