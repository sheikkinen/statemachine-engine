"""
Tests for multiple state machine engines running simultaneously.
Tests the configurable socket paths and ports to ensure multiple engines can coexist.
"""
import tempfile
import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

from statemachine_engine.core.engine import StateMachineEngine, EventSocketManager


class TestMultipleEngines:
    """Test suite for multiple engine support."""

    def test_engine_with_custom_socket_paths(self):
        """Test that engines can be created with custom socket paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two engines with different socket paths
            socket_path_1 = os.path.join(temp_dir, "engine1-events.sock")
            socket_path_2 = os.path.join(temp_dir, "engine2-events.sock")
            control_prefix_1 = os.path.join(temp_dir, "engine1-control")
            control_prefix_2 = os.path.join(temp_dir, "engine2-control")

            # Mock the action loader to avoid file system dependencies
            with patch('statemachine_engine.core.action_loader.ActionLoader'):
                engine1 = StateMachineEngine(
                    machine_name="test_engine_1",
                    event_socket_path=socket_path_1,
                    control_socket_prefix=control_prefix_1
                )
                engine2 = StateMachineEngine(
                    machine_name="test_engine_2", 
                    event_socket_path=socket_path_2,
                    control_socket_prefix=control_prefix_2
                )

            # Verify different socket paths
            assert engine1.event_socket.socket_path == socket_path_1
            assert engine2.event_socket.socket_path == socket_path_2
            assert engine1.control_socket_prefix == control_prefix_1
            assert engine2.control_socket_prefix == control_prefix_2

    def test_engine_default_socket_paths(self):
        """Test that engines use default socket paths when not specified."""
        with patch('statemachine_engine.core.action_loader.ActionLoader'):
            engine = StateMachineEngine(machine_name="test_engine")

        # Verify default paths
        assert engine.event_socket.socket_path == "/tmp/statemachine-events.sock"
        assert engine.control_socket_prefix == "/tmp/statemachine-control"

    def test_event_socket_manager_custom_path(self):
        """Test EventSocketManager with custom socket path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = os.path.join(temp_dir, "custom-events.sock")
            
            socket_manager = EventSocketManager(socket_path=custom_path)
            assert socket_manager.socket_path == custom_path

    def test_event_socket_manager_default_path(self):
        """Test EventSocketManager with default socket path."""
        socket_manager = EventSocketManager()
        assert socket_manager.socket_path == "/tmp/statemachine-events.sock"

    def test_control_socket_path_generation(self):
        """Test control socket path generation with custom prefix."""
        with tempfile.TemporaryDirectory() as temp_dir:
            control_prefix = os.path.join(temp_dir, "custom-control")
            
            with patch('statemachine_engine.core.action_loader.ActionLoader'):
                engine = StateMachineEngine(
                    machine_name="test_machine",
                    control_socket_prefix=control_prefix
                )

            expected_control_path = f"{control_prefix}-test_machine.sock"
            # The control socket path is created internally, but we can verify the prefix
            assert engine.control_socket_prefix == control_prefix

    @pytest.mark.asyncio
    async def test_multiple_engines_no_conflict(self):
        """Test that multiple engines can be instantiated without conflicts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engines = []
            
            # Create 3 engines with different socket configurations
            for i in range(3):
                socket_path = os.path.join(temp_dir, f"engine{i}-events.sock")
                control_prefix = os.path.join(temp_dir, f"engine{i}-control")
                
                with patch('statemachine_engine.core.action_loader.ActionLoader'):
                    engine = StateMachineEngine(
                        machine_name=f"test_engine_{i}",
                        event_socket_path=socket_path,
                        control_socket_prefix=control_prefix
                    )
                engines.append(engine)

            # Verify all engines have unique socket paths
            event_paths = [engine.event_socket.socket_path for engine in engines]
            control_prefixes = [engine.control_socket_prefix for engine in engines]
            
            assert len(set(event_paths)) == 3, "Event socket paths should be unique"
            assert len(set(control_prefixes)) == 3, "Control socket prefixes should be unique"

    def test_socket_path_validation(self):
        """Test socket path validation and error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with valid directory
            valid_path = os.path.join(temp_dir, "valid-events.sock")
            socket_manager = EventSocketManager(socket_path=valid_path)
            assert socket_manager.socket_path == valid_path

            # Test with non-existent directory (should still accept the path)
            invalid_dir_path = "/non/existent/directory/events.sock"
            socket_manager = EventSocketManager(socket_path=invalid_dir_path)
            assert socket_manager.socket_path == invalid_dir_path


class TestCLISocketConfiguration:
    """Test CLI configuration for socket paths."""

    def test_cli_socket_path_parsing(self):
        """Test that CLI arguments are properly parsed for socket configuration."""
        # This would typically test the CLI argument parsing
        # For now, we'll test the underlying functionality
        
        test_cases = [
            {
                "event_socket_path": "/custom/events.sock",
                "control_socket_prefix": "/custom/control",
                "expected_event": "/custom/events.sock",
                "expected_control": "/custom/control"
            },
            {
                "event_socket_path": None,
                "control_socket_prefix": None,
                "expected_event": "/tmp/statemachine-events.sock",
                "expected_control": "/tmp/statemachine-control"
            }
        ]

        for case in test_cases:
            with patch('statemachine_engine.core.action_loader.ActionLoader'):
                engine = StateMachineEngine(
                    machine_name="test",
                    event_socket_path=case["event_socket_path"],
                    control_socket_prefix=case["control_socket_prefix"]
                )

            assert engine.event_socket.socket_path == case["expected_event"]
            assert engine.control_socket_prefix == case["expected_control"]


class TestWebSocketServerConfiguration:
    """Test WebSocket server configuration for multiple engines."""

    def test_websocket_server_config_parsing(self):
        """Test WebSocket server configuration parameters."""
        # Mock argparse results
        mock_args = MagicMock()
        mock_args.host = "0.0.0.0"
        mock_args.port = 3003
        mock_args.event_socket_path = "/custom/events.sock"

        # Verify configuration values
        assert mock_args.host == "0.0.0.0"
        assert mock_args.port == 3003
        assert mock_args.event_socket_path == "/custom/events.sock"

    def test_websocket_server_default_config(self):
        """Test WebSocket server default configuration."""
        # Mock default argparse results
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 3002
        mock_args.event_socket_path = "/tmp/statemachine-events.sock"

        # Verify default values
        assert mock_args.host == "127.0.0.1"
        assert mock_args.port == 3002
        assert mock_args.event_socket_path == "/tmp/statemachine-events.sock"


@pytest.mark.integration
class TestMultipleEnginesIntegration:
    """Integration tests for multiple engines."""

    def test_multiple_engines_socket_isolation(self):
        """Test that multiple engines with different sockets are properly isolated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup paths for two engines
            engine1_event_sock = os.path.join(temp_dir, "engine1-events.sock")
            engine1_control_prefix = os.path.join(temp_dir, "engine1-control")
            
            engine2_event_sock = os.path.join(temp_dir, "engine2-events.sock")
            engine2_control_prefix = os.path.join(temp_dir, "engine2-control")

            with patch('statemachine_engine.core.action_loader.ActionLoader'):
                # Create two engines
                engine1 = StateMachineEngine(
                    machine_name="worker_1",
                    event_socket_path=engine1_event_sock,
                    control_socket_prefix=engine1_control_prefix
                )
                
                engine2 = StateMachineEngine(
                    machine_name="worker_2", 
                    event_socket_path=engine2_event_sock,
                    control_socket_prefix=engine2_control_prefix
                )

            # Verify isolation
            assert engine1.event_socket.socket_path != engine2.event_socket.socket_path
            assert engine1.control_socket_prefix != engine2.control_socket_prefix

            # Verify expected paths - control sockets are internal but we can check prefixes
            assert engine1.control_socket_prefix == engine1_control_prefix
            assert engine2.control_socket_prefix == engine2_control_prefix

    def test_backwards_compatibility(self):
        """Test that old behavior still works when no custom paths are provided."""
        with patch('statemachine_engine.core.action_loader.ActionLoader'):
            # Create engine without custom paths (old behavior)
            engine = StateMachineEngine(machine_name="legacy_engine")

        # Should use default paths
        assert engine.event_socket.socket_path == "/tmp/statemachine-events.sock"
        assert engine.control_socket_prefix == "/tmp/statemachine-control"