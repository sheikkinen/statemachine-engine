"""
Test engine-level variable interpolation.

Tests that the engine's _interpolate_config and _substitute_variables
methods correctly replace {variable} placeholders with context values
before passing config to actions.
"""
import pytest
from statemachine_engine.core.engine import StateMachineEngine


@pytest.fixture
def engine():
    """Create a minimal engine instance for testing"""
    engine = StateMachineEngine(machine_name='test_machine')
    # Manually set config for testing (normally loaded from YAML)
    engine.config = {
        'initial_state': 'idle',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'idle'
    return engine


def test_substitute_simple_variable(engine):
    """Test simple variable substitution like {job_id}"""
    context = {'job_id': 'test_123', 'status': 'pending'}
    
    template = "Processing job {job_id} with status {status}"
    result = engine._substitute_variables(template, context)
    
    assert result == "Processing job test_123 with status pending"


def test_substitute_nested_variable(engine):
    """Test nested variable substitution like {event_data.payload.job_id}"""
    context = {
        'event_data': {
            'payload': {
                'job_id': 'nested_456',
                'pony_prompt': 'A beautiful portrait'
            }
        }
    }
    
    template = "Job {event_data.payload.job_id}: {event_data.payload.pony_prompt}"
    result = engine._substitute_variables(template, context)
    
    assert result == "Job nested_456: A beautiful portrait"


def test_substitute_missing_variable_keeps_placeholder(engine):
    """Test that missing variables are left as placeholders"""
    context = {'job_id': 'test_123'}
    
    template = "Job {job_id} has {nonexistent_var}"
    result = engine._substitute_variables(template, context)
    
    assert result == "Job test_123 has {nonexistent_var}"


def test_substitute_nested_missing_keeps_placeholder(engine):
    """Test that missing nested paths are left as placeholders"""
    context = {
        'event_data': {
            'payload': {'job_id': 'test_123'}
        }
    }
    
    template = "Missing: {event_data.nonexistent.path}"
    result = engine._substitute_variables(template, context)
    
    assert result == "Missing: {event_data.nonexistent.path}"


def test_interpolate_config_strings(engine):
    """Test interpolating string values in config"""
    context = {'job_id': 'test_789', 'status': 'processing'}
    
    config = {
        'type': 'log',
        'message': 'Job {job_id} is {status}',
        'level': 'info'
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['message'] == 'Job test_789 is processing'
    assert result['level'] == 'info'  # Non-template strings unchanged
    assert result['type'] == 'log'


def test_interpolate_config_nested_dict(engine):
    """Test interpolating nested dictionary values"""
    context = {'job_id': 'test_999', 'user': 'alice'}
    
    config = {
        'type': 'bash',
        'command': 'process {job_id}',
        'params': {
            'user': '{user}',
            'output': '/tmp/{job_id}.txt'
        }
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['command'] == 'process test_999'
    assert result['params']['user'] == 'alice'
    assert result['params']['output'] == '/tmp/test_999.txt'


def test_interpolate_config_list_values(engine):
    """Test interpolating string values in lists"""
    context = {'job_id': 'test_list', 'format': 'png'}
    
    config = {
        'type': 'multi_step',
        'steps': [
            'step1 {job_id}',
            'step2 {format}',
            'step3 literal'
        ]
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['steps'][0] == 'step1 test_list'
    assert result['steps'][1] == 'step2 png'
    assert result['steps'][2] == 'step3 literal'


def test_interpolate_config_mixed_types(engine):
    """Test that non-string types are preserved"""
    context = {'job_id': 'test_mixed'}
    
    config = {
        'type': 'complex',
        'message': 'Job {job_id}',
        'timeout': 30,  # int
        'retry': True,  # bool
        'threshold': 0.95,  # float
        'tags': None  # None
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['message'] == 'Job test_mixed'
    assert result['timeout'] == 30
    assert result['retry'] is True
    assert result['threshold'] == 0.95
    assert result['tags'] is None


def test_interpolate_config_with_event_payload(engine):
    """Test interpolating from event payload data"""
    context = {
        'job_id': 'test_event',
        'event_data': {
            'event_name': 'start_job',
            'payload': {
                'input_image': '/path/to/image.jpg',
                'user_prompt': 'Make it better',
                'padding_factor': 1.5
            }
        }
    }
    
    config = {
        'type': 'bash',
        'command': 'process {job_id} --input {event_data.payload.input_image}',
        'description': 'Processing with prompt: {event_data.payload.user_prompt}'
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['command'] == 'process test_event --input /path/to/image.jpg'
    assert result['description'] == 'Processing with prompt: Make it better'


def test_interpolate_config_empty_context(engine):
    """Test that interpolation with empty context leaves placeholders"""
    context = {}
    
    config = {
        'type': 'log',
        'message': 'Job {job_id} status {status}'
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['message'] == 'Job {job_id} status {status}'


def test_interpolate_config_special_characters(engine):
    """Test that special characters in values are handled correctly"""
    context = {
        'job_id': 'test_special',
        'command': 'echo "Hello World"',
        'path': '/tmp/data with spaces/file.txt'
    }
    
    config = {
        'type': 'bash',
        'command': '{command}',
        'output': '{path}'
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['command'] == 'echo "Hello World"'
    assert result['output'] == '/tmp/data with spaces/file.txt'


def test_interpolate_config_numeric_string_values(engine):
    """Test that numeric values in context are converted to strings"""
    context = {
        'job_id': 'test_numeric',
        'priority': 5,
        'timeout': 30.5,
        'enabled': True
    }
    
    config = {
        'type': 'log',
        'message': 'Job {job_id} priority={priority} timeout={timeout} enabled={enabled}'
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['message'] == 'Job test_numeric priority=5 timeout=30.5 enabled=True'


def test_interpolate_preserves_braces_in_non_variable_context(engine):
    """Test that literal braces not matching variable pattern are preserved"""
    context = {'job_id': 'test_braces'}
    
    config = {
        'type': 'bash',
        'command': 'echo {job_id} | jq \'{field: "value"}\''  # JSON with braces
    }
    
    result = engine._interpolate_config(config, context)
    
    # {job_id} should be replaced, but {field: "value"} should remain
    assert 'test_braces' in result['command']
    assert '{field: "value"}' in result['command']


def test_interpolate_deeply_nested_structures(engine):
    """Test interpolation in deeply nested structures"""
    context = {
        'job_id': 'test_deep',
        'user': 'alice',
        'env': 'production'
    }
    
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
                        'command': 'setup {env} for {user}'
                    }
                ]
            }
        }
    }
    
    result = engine._interpolate_config(config, context)
    
    assert result['steps']['prepare']['actions'][0]['message'] == 'Preparing test_deep'
    assert result['steps']['prepare']['actions'][1]['command'] == 'setup production for alice'


def test_context_propagation_from_custom_action(engine):
    """
    Test that custom actions can modify context and subsequent actions
    see those modifications through interpolation.
    
    This is the key use case from the change request.
    """
    # Simulate custom action modifying context
    engine.context = {
        'event_data': {
            'payload': {
                'job_id': 'original_123',
                'pony_prompt': 'A beautiful portrait'
            }
        }
    }
    
    # Custom action would do this:
    payload = engine.context['event_data']['payload']
    engine.context['id'] = payload.get('job_id')
    engine.context['pony_prompt'] = payload.get('pony_prompt')
    
    # Now test that subsequent action config sees the extracted values
    config = {
        'type': 'log',
        'message': 'Extracted id={id}, prompt={pony_prompt}'
    }
    
    result = engine._interpolate_config(config, engine.context)
    
    assert result['message'] == 'Extracted id=original_123, prompt=A beautiful portrait'
    # Placeholders should NOT appear in the result
    assert '{id}' not in result['message']
    assert '{pony_prompt}' not in result['message']
