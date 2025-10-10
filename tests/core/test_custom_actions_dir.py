"""
Tests for custom actions directory (--actions-dir) feature
"""

import pytest
import tempfile
import sys
from pathlib import Path
from statemachine_engine.core.action_loader import ActionLoader


class TestCustomActionsDirectory:
    """Test custom actions directory functionality"""
    
    @pytest.fixture
    def custom_actions_dir(self):
        """Create temporary directory with custom actions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            actions_dir = Path(tmpdir) / "actions"
            actions_dir.mkdir()
            
            # Create a simple custom action
            custom_action = actions_dir / "custom_test_action.py"
            custom_action.write_text("""
from statemachine_engine.actions.base import BaseAction

class CustomTestAction(BaseAction):
    async def execute(self, context):
        return 'custom_success'
""")
            
            # Create a nested custom action
            nested_dir = actions_dir / "nested"
            nested_dir.mkdir()
            nested_action = nested_dir / "nested_test_action.py"
            nested_action.write_text("""
from statemachine_engine.actions.base import BaseAction

class NestedTestAction(BaseAction):
    async def execute(self, context):
        return 'nested_success'
""")
            
            yield str(actions_dir)
    
    def test_custom_actions_directory_discovery(self, custom_actions_dir):
        """Test that custom actions are discovered"""
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        available_actions = loader.get_available_actions()
        assert 'custom_test' in available_actions
        assert 'nested_test' in available_actions
    
    def test_custom_action_loading(self, custom_actions_dir):
        """Test loading a custom action class"""
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        action_class = loader.load_action_class('custom_test')
        assert action_class is not None
        assert action_class.__name__ == 'CustomTestAction'
    
    @pytest.mark.asyncio
    async def test_custom_action_execution(self, custom_actions_dir):
        """Test executing a custom action"""
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        action_class = loader.load_action_class('custom_test')
        action = action_class({})
        result = await action.execute({})
        
        assert result == 'custom_success'
    
    def test_nested_custom_action_loading(self, custom_actions_dir):
        """Test loading nested custom actions"""
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        action_class = loader.load_action_class('nested_test')
        assert action_class is not None
        assert action_class.__name__ == 'NestedTestAction'
    
    def test_invalid_actions_directory(self):
        """Test handling of non-existent actions directory"""
        loader = ActionLoader(actions_root="/nonexistent/path/actions")
        
        # Should not crash, just have no actions
        available_actions = loader.get_available_actions()
        assert len(available_actions) == 0
    
    def test_default_actions_loading(self):
        """Test that default actions still work without custom dir"""
        loader = ActionLoader()  # No custom dir
        
        # Should find built-in actions
        bash_action = loader.load_action_class('bash')
        assert bash_action is not None
        
        log_action = loader.load_action_class('log')
        assert log_action is not None
    
    def test_sys_path_manipulation(self, custom_actions_dir):
        """Test that custom actions dir parent is added to sys.path"""
        parent_path = str(Path(custom_actions_dir).parent.resolve())
        
        # Remove from sys.path if already there (check resolved paths)
        sys.path = [p for p in sys.path if Path(p).resolve() != Path(parent_path).resolve()]
        
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        # Parent should be added to sys.path (check with resolved path)
        assert any(Path(p).resolve() == Path(parent_path).resolve() for p in sys.path)
    
    def test_action_caching(self, custom_actions_dir):
        """Test that loaded actions are cached"""
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        # Load action twice
        action_class1 = loader.load_action_class('custom_test')
        action_class2 = loader.load_action_class('custom_test')
        
        # Should be the same object (cached)
        assert action_class1 is action_class2
    
    def test_absolute_path_resolution(self, custom_actions_dir):
        """Test that absolute paths work"""
        abs_path = Path(custom_actions_dir).resolve()
        loader = ActionLoader(actions_root=str(abs_path))
        
        action_class = loader.load_action_class('custom_test')
        assert action_class is not None
    
    def test_relative_path_resolution(self, custom_actions_dir):
        """Test relative path handling"""
        # Create a relative path from current directory
        import os
        original_cwd = os.getcwd()
        
        try:
            # Change to temp dir parent
            os.chdir(Path(custom_actions_dir).parent)
            
            # Use relative path
            rel_path = "actions"
            loader = ActionLoader(actions_root=rel_path)
            
            action_class = loader.load_action_class('custom_test')
            assert action_class is not None
        finally:
            os.chdir(original_cwd)


class TestCLIPathValidation:
    """Test CLI path validation and resolution"""
    
    def test_home_directory_expansion(self):
        """Test that ~ is expanded in paths"""
        from pathlib import Path
        
        # Test expanduser
        test_path = Path("~/test/actions").expanduser()
        assert str(test_path).startswith(str(Path.home()))
    
    def test_relative_to_absolute_conversion(self):
        """Test relative to absolute path conversion"""
        rel_path = Path("./actions")
        abs_path = rel_path.resolve()
        
        assert abs_path.is_absolute()


class TestMixedActions:
    """Test mixing built-in and custom actions"""
    
    @pytest.fixture
    def mixed_actions_dir(self):
        """Create custom actions that don't conflict with built-ins"""
        with tempfile.TemporaryDirectory() as tmpdir:
            actions_dir = Path(tmpdir) / "actions"
            actions_dir.mkdir()
            
            # Create custom action with unique name
            custom_action = actions_dir / "project_specific_action.py"
            custom_action.write_text("""
from statemachine_engine.actions.base import BaseAction

class ProjectSpecificAction(BaseAction):
    async def execute(self, context):
        return 'project_success'
""")
            
            yield str(actions_dir)
    
    def test_custom_actions_available(self, mixed_actions_dir):
        """Test that custom actions are discovered"""
        loader = ActionLoader(actions_root=mixed_actions_dir)
        
        available = loader.get_available_actions()
        assert 'project_specific' in available
    
    def test_builtin_actions_not_available_in_custom_loader(self, mixed_actions_dir):
        """
        DOCUMENTS CURRENT (BROKEN) BEHAVIOR:
        When using custom actions directory, built-in actions are NOT available.
        
        This is a design flaw - users lose access to bash, log, send_event, etc.
        Expected behavior: Both custom AND built-in actions should be available.
        """
        loader = ActionLoader(actions_root=mixed_actions_dir)
        
        # CURRENT BROKEN BEHAVIOR: Built-in actions are NOT available
        bash_action = loader.load_action_class('bash')
        assert bash_action is None
        
        log_action = loader.load_action_class('log')
        assert log_action is None
        
        send_event_action = loader.load_action_class('send_event')
        assert send_event_action is None
    
    def test_only_custom_actions_in_discovery(self, mixed_actions_dir):
        """
        DOCUMENTS CURRENT (BROKEN) BEHAVIOR:
        Custom actions directory completely replaces built-in discovery.
        
        This breaks workflows that need both custom actions AND built-ins.
        """
        loader = ActionLoader(actions_root=mixed_actions_dir)
        
        available = loader.get_available_actions()
        
        # Only custom action is discovered
        assert 'project_specific' in available
        
        # Built-in actions are NOT discovered (this is the bug)
        assert 'bash' not in available
        assert 'log' not in available
        assert 'send_event' not in available
        assert 'check_database_queue' not in available
        assert 'clear_events' not in available


class TestExpectedBehavior:
    """
    Tests for EXPECTED behavior - these should FAIL until the bug is fixed.
    Tests document what the correct behavior should be.
    """
    
    @pytest.fixture
    def custom_actions_dir(self):
        """Create custom actions directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            actions_dir = Path(tmpdir) / "actions"
            actions_dir.mkdir()
            
            # Create custom action
            custom_action = actions_dir / "custom_action.py"
            custom_action.write_text("""
from statemachine_engine.actions.base import BaseAction

class CustomAction(BaseAction):
    async def execute(self, context):
        return 'custom_success'
""")
            
            yield str(actions_dir)
    
    @pytest.mark.xfail(reason="BUG: Custom actions dir should supplement, not replace built-ins")
    def test_builtin_actions_should_be_available_with_custom_dir(self, custom_actions_dir):
        """
        EXPECTED BEHAVIOR (currently fails):
        When using --actions-dir, built-in actions should STILL be available.
        Custom actions should SUPPLEMENT built-ins, not REPLACE them.
        """
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        # Built-in actions SHOULD be available
        bash_action = loader.load_action_class('bash')
        assert bash_action is not None, "bash action should be available"
        
        log_action = loader.load_action_class('log')
        assert log_action is not None, "log action should be available"
        
        send_event_action = loader.load_action_class('send_event')
        assert send_event_action is not None, "send_event action should be available"
    
    @pytest.mark.xfail(reason="BUG: Custom actions dir should supplement, not replace built-ins")
    def test_both_custom_and_builtin_actions_in_discovery(self, custom_actions_dir):
        """
        EXPECTED BEHAVIOR (currently fails):
        Discovery should include BOTH custom and built-in actions.
        """
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        available = loader.get_available_actions()
        
        # Custom action should be discovered
        assert 'custom' in available, "Custom action should be discovered"
        
        # Built-in actions should ALSO be discovered
        assert 'bash' in available, "bash should be available"
        assert 'log' in available, "log should be available"
        assert 'send_event' in available, "send_event should be available"
    
    @pytest.mark.xfail(reason="BUG: Custom actions dir should supplement, not replace built-ins")
    def test_custom_actions_can_use_builtin_actions(self, custom_actions_dir):
        """
        EXPECTED BEHAVIOR (currently fails):
        A workflow should be able to use both custom actions AND built-in actions
        in the same state machine configuration.
        """
        loader = ActionLoader(actions_root=custom_actions_dir)
        
        # Should be able to load custom action
        custom = loader.load_action_class('custom')
        assert custom is not None
        
        # Should ALSO be able to load built-in bash action
        bash = loader.load_action_class('bash')
        assert bash is not None
        
        # Both should be usable in the same workflow
        assert custom is not None and bash is not None


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_missing_action_in_custom_dir(self, tmp_path):
        """Test loading non-existent action from custom directory"""
        actions_dir = tmp_path / "actions"
        actions_dir.mkdir()
        
        loader = ActionLoader(actions_root=str(actions_dir))
        
        action_class = loader.load_action_class('nonexistent')
        assert action_class is None
    
    def test_invalid_action_file(self, tmp_path):
        """Test handling of invalid Python file in actions directory"""
        actions_dir = tmp_path / "actions"
        actions_dir.mkdir()
        
        # Create invalid Python file
        invalid_action = actions_dir / "invalid_action.py"
        invalid_action.write_text("this is not valid python code {{{")
        
        loader = ActionLoader(actions_root=str(actions_dir))
        
        # Should not crash during discovery
        available = loader.get_available_actions()
        assert 'invalid' in available
        
        # Should fail gracefully when trying to load
        action_class = loader.load_action_class('invalid')
        assert action_class is None
    
    def test_action_without_required_class(self, tmp_path):
        """Test action file that doesn't have the expected class"""
        actions_dir = tmp_path / "actions"
        actions_dir.mkdir()
        
        # Create action file with wrong class name
        wrong_class = actions_dir / "test_action.py"
        wrong_class.write_text("""
class WrongClassName:
    pass
""")
        
        loader = ActionLoader(actions_root=str(actions_dir))
        
        # Should fail gracefully
        action_class = loader.load_action_class('test')
        assert action_class is None
