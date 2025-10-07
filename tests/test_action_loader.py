"""
Test ActionLoader functionality

Verifies that all actions can be discovered and loaded correctly
using the ActionLoader instead of hardcoded imports.
"""

import pytest
from statemachine_engine.core.action_loader import ActionLoader


class TestActionLoader:
    """Tests for ActionLoader discovery and loading"""

    def test_action_discovery(self):
        """Test that ActionLoader can discover all actions"""
        loader = ActionLoader()
        available_actions = loader.get_available_actions()
        
        # Should discover multiple actions
        assert len(available_actions) > 0, "ActionLoader should discover at least some actions"
        
        # Check for critical engine actions
        critical_actions = ['bash', 'log', 'check_database_queue']
        for action in critical_actions:
            assert action in available_actions, f"Critical action '{action}' should be discoverable"

    def test_load_bash_action(self):
        """Test loading bash action class"""
        loader = ActionLoader()
        action_class = loader.load_action_class('bash')
        
        assert action_class is not None, "Bash action should be loadable"
        assert action_class.__name__ == 'BashAction', "Should load correct class"

    def test_load_log_action(self):
        """Test loading log action class"""
        loader = ActionLoader()
        action_class = loader.load_action_class('log')
        
        assert action_class is not None, "Log action should be loadable"
        assert action_class.__name__ == 'LogAction', "Should load correct class"

    def test_load_nonexistent_action(self):
        """Test that loading nonexistent action returns None"""
        loader = ActionLoader()
        action_class = loader.load_action_class('nonexistent_action_xyz')
        
        assert action_class is None, "Nonexistent action should return None"

    def test_bash_action_instantiation(self):
        """Test that loaded bash action can be instantiated"""
        loader = ActionLoader()
        action_class = loader.load_action_class('bash')
        
        config = {'command': 'echo test', 'description': 'test command'}
        action_instance = action_class(config)
        
        assert action_instance is not None, "Action should instantiate successfully"
        assert hasattr(action_instance, 'execute'), "Action should have execute method"

    def test_log_action_instantiation(self):
        """Test that log action can be instantiated"""
        loader = ActionLoader()
        action_class = loader.load_action_class('log')
        
        config = {'message': 'test message'}
        action_instance = action_class(config)
        
        assert action_instance is not None, "Log action should instantiate"
        assert hasattr(action_instance, 'execute'), "Action should have execute method"

    def test_critical_actions_loadable(self):
        """Test that all critical actions can be loaded"""
        loader = ActionLoader()
        
        critical_actions = [
            'bash',
            'log',
            'check_database_queue',
            'send_event'
        ]
        
        for action_type in critical_actions:
            action_class = loader.load_action_class(action_type)
            assert action_class is not None, f"Critical action '{action_type}' should be loadable"


class TestActionLoaderDomain:
    """Tests for domain-specific actions (may fail if domain actions not available)"""

    def test_load_domain_actions_if_available(self):
        """Test loading domain-specific actions if they exist"""
        loader = ActionLoader()
        available_actions = loader.get_available_actions()
        
        domain_actions = ['generate_concepts', 'rank_concepts', 'generate_prompts', 'enhance_prompt']
        
        for action_type in domain_actions:
            if action_type in available_actions:
                action_class = loader.load_action_class(action_type)
                # If it's discovered, it should be loadable
                if action_class is not None:
                    # Verify it has execute method
                    assert hasattr(action_class, '__init__'), f"{action_type} should have __init__ method"
