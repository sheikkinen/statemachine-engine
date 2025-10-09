"""
Tests for nested field extraction and payload forwarding in send_event action

Tests the enhanced template expansion that supports:
- Nested field access: {event_data.payload.user.id}
- Whole-dict forwarding: payload: "{event_data.payload}"
"""
import pytest
from statemachine_engine.actions.builtin.send_event_action import SendEventAction


@pytest.mark.asyncio
async def test_nested_field_extraction():
    """Template can extract nested fields from payload"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'user_id': '{event_data.payload.user.id}',
            'user_name': '{event_data.payload.user.name}',
            'image': '{event_data.payload.result.image_path}',
            'status': 'pending'  # Static value
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'type': 'completed',
            'payload': {
                'user': {
                    'id': 123,
                    'name': 'Alice'
                },
                'result': {
                    'image_path': '/path/to/image.png',
                    'size': '1024x768'
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['user_id'] == 123
    assert processed['user_name'] == 'Alice'
    assert processed['image'] == '/path/to/image.png'
    assert processed['status'] == 'pending'  # Static value preserved


@pytest.mark.asyncio
async def test_nested_field_deep_nesting():
    """Support deeply nested field access"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'value': '{event_data.payload.level1.level2.level3.field}'
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'level1': {
                    'level2': {
                        'level3': {
                            'field': 'deep_value'
                        }
                    }
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['value'] == 'deep_value'


@pytest.mark.asyncio
async def test_nested_field_missing_path(caplog):
    """Missing nested path returns None with warning"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'value': '{event_data.payload.user.missing.field}'
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'user': {
                    'id': 123
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['value'] is None
    assert any('not found' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_nested_field_non_dict_intermediate():
    """Accessing nested field through non-dict returns None"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'value': '{event_data.payload.user.name.first}'  # user.name is string, not dict
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'user': {
                    'name': 'Alice'  # String, not dict
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['value'] is None


@pytest.mark.asyncio
async def test_entire_payload_forwarding():
    """Can forward entire payload dict using template string"""
    config = {
        'target_machine': 'worker',
        'event_type': 'relay',
        'payload': '{event_data.payload}'  # String, not dict
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'key1': 'value1',
                'key2': 42,
                'nested': {'field': 'data'}
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    # Should return the entire dict
    assert processed == {
        'key1': 'value1',
        'key2': 42,
        'nested': {'field': 'data'}
    }


@pytest.mark.asyncio
async def test_entire_payload_forwarding_empty():
    """Forwarding empty payload returns empty dict"""
    config = {
        'target_machine': 'worker',
        'event_type': 'relay',
        'payload': '{event_data.payload}'
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {}
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed == {}


@pytest.mark.asyncio
async def test_entire_payload_forwarding_missing_event_data():
    """Forwarding when event_data is missing returns empty dict"""
    config = {
        'target_machine': 'worker',
        'event_type': 'relay',
        'payload': '{event_data.payload}'
    }
    
    context = {
        'machine_name': 'controller'
        # No event_data
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed == {}


@pytest.mark.asyncio
async def test_mixed_extraction_and_static():
    """Mix extracted fields with static values"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'input': '{event_data.payload.file}',
            'user': '{event_data.payload.user.id}',
            'machine': '{machine_name}',  # Direct context variable
            'priority': 'high',  # Static
            'version': 1  # Static number
        }
    }
    
    context = {
        'machine_name': 'controller',
        'timestamp': '2025-10-09T12:00:00',
        'event_data': {
            'payload': {
                'file': 'image.png',
                'user': {
                    'id': 456
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['input'] == 'image.png'
    assert processed['user'] == 456
    assert processed['machine'] == 'controller'  # From context
    assert processed['priority'] == 'high'
    assert processed['version'] == 1


@pytest.mark.asyncio
async def test_flat_field_extraction_still_works():
    """Existing flat field extraction continues to work"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'file': '{event_data.payload.filename}',  # Flat field
            'status': '{event_data.payload.status}'
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'filename': 'test.png',
                'status': 'ready'
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['file'] == 'test.png'
    assert processed['status'] == 'ready'


@pytest.mark.asyncio
async def test_recursive_placeholder_substitution():
    """Placeholders in extracted values are recursively substituted"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'output': '{event_data.payload.path_template}'
        }
    }
    
    context = {
        'machine_name': 'controller',
        'current_job': {'id': 'job_123'},
        'event_data': {
            'payload': {
                'path_template': '/output/{id}.png'  # Contains {id} placeholder
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    # The {id} should be substituted
    assert processed['output'] == '/output/job_123.png'


@pytest.mark.asyncio
async def test_nested_extraction_with_list_values():
    """Nested extraction works when values are lists"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'items': '{event_data.payload.data.items}'
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'data': {
                    'items': ['item1', 'item2', 'item3']
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    # List values should be preserved
    assert processed['items'] == ['item1', 'item2', 'item3']


@pytest.mark.asyncio
async def test_nested_extraction_with_number_values():
    """Nested extraction works with numeric values"""
    config = {
        'target_machine': 'worker',
        'event_type': 'process',
        'payload': {
            'count': '{event_data.payload.stats.count}',
            'percentage': '{event_data.payload.stats.percentage}'
        }
    }
    
    context = {
        'machine_name': 'controller',
        'event_data': {
            'payload': {
                'stats': {
                    'count': 42,
                    'percentage': 95.5
                }
            }
        }
    }
    
    action = SendEventAction(config)
    processed = action._process_payload(config['payload'], context)
    
    assert processed['count'] == 42
    assert processed['percentage'] == 95.5
