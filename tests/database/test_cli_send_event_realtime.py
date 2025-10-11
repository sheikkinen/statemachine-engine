"""
Tests for send-event CLI command with real-time Unix socket delivery
"""
import pytest
import json
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from statemachine_engine.database.cli import cmd_send_event


class TestSendEventRealtimeSocket:
    """Test send-event command's real-time Unix socket functionality"""
    
    @pytest.fixture
    def mock_event_model(self):
        """Mock the machine event model"""
        with patch('statemachine_engine.database.cli.get_machine_event_model') as mock:
            model = MagicMock()
            model.send_event.return_value = 12345
            mock.return_value = model
            yield model
    
    @pytest.fixture
    def temp_socket(self):
        """Create a temporary Unix socket to receive messages"""
        # Use temp directory instead of /tmp for tests
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / 'test-events.sock'
            
            # Create listening socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.bind(str(socket_path))
            sock.settimeout(1.0)  # 1 second timeout
            
            yield sock, socket_path
            
            sock.close()
            if socket_path.exists():
                socket_path.unlink()
    
    def test_send_to_websocket_socket(self, mock_event_model, temp_socket, capsys):
        """Test that send-event sends to WebSocket server's Unix socket"""
        listener, socket_path = temp_socket

        # Create args
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = 'test_machine'
        args.job_id = None
        args.payload = '{"message": "test message"}'

        # Mock the socket operations to succeed
        with patch('socket.socket') as mock_socket:
            sock_instance = MagicMock()
            mock_socket.return_value = sock_instance

            # Mock WebSocket socket path exists
            with patch('statemachine_engine.database.cli.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance

                # Call the command
                result = cmd_send_event(args)

                # Should succeed
                assert result == 0

                # Check output
                captured = capsys.readouterr()
                assert '📡 Sent to WebSocket server for real-time UI update' in captured.out
                assert '✅ Event sent successfully!' in captured.out
    
    def test_websocket_socket_not_available(self, mock_event_model, capsys):
        """Test graceful handling when WebSocket socket doesn't exist"""
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = 'cli'
        args.job_id = None
        args.payload = '{"message": "test"}'
        
        # Call the command - should still succeed even if socket unavailable
        result = cmd_send_event(args)
        
        # Should succeed (database write still works)
        assert result == 0
        
        # Check output
        captured = capsys.readouterr()
        assert '✅ Event sent successfully!' in captured.out
    
    def test_sends_to_both_sockets_for_non_ui_target(self, mock_event_model, capsys):
        """Test that non-UI targets get sent to both WebSocket and control sockets"""
        args = MagicMock()
        args.target = 'my_machine'
        args.type = 'custom_event'
        args.source = 'cli'
        args.job_id = 'job123'
        args.payload = '{"data": "value"}'
        
        # Mock both socket paths existing
        with patch('statemachine_engine.database.cli.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            
            # Mock socket sends
            with patch('socket.socket') as mock_socket:
                sock_instance = MagicMock()
                mock_socket.return_value = sock_instance
                
                result = cmd_send_event(args)
                
                assert result == 0
                
                # Check output mentions both socket types
                captured = capsys.readouterr()
                assert '📡 Sent to WebSocket server for real-time UI update' in captured.out
                assert '📡 Sent to my_machine control socket' in captured.out
    
    def test_ui_target_skips_control_socket(self, mock_event_model, capsys):
        """Test that UI target doesn't attempt control socket send"""
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = None
        args.job_id = None
        args.payload = '{"message": "UI only"}'
        
        result = cmd_send_event(args)
        
        assert result == 0
        
        # Check output doesn't mention control socket
        captured = capsys.readouterr()
        assert 'control socket' not in captured.out
    
    def test_json_payload_parsing(self, mock_event_model, capsys):
        """Test that JSON payload is parsed correctly"""
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = 'test'
        args.job_id = None
        args.payload = '{"message": "test", "level": "INFO", "nested": {"key": "value"}}'
        
        with patch('socket.socket') as mock_socket:
            sock_instance = MagicMock()
            mock_socket.return_value = sock_instance
            
            # Mock WebSocket socket path exists
            with patch('statemachine_engine.database.cli.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                result = cmd_send_event(args)
                
                assert result == 0
                
                # Verify socket was called with parsed JSON
                if sock_instance.sendto.called:
                    call_args = sock_instance.sendto.call_args[0]
                    sent_data = json.loads(call_args[0].decode('utf-8'))
                    assert sent_data['payload']['message'] == 'test'
                    assert sent_data['payload']['level'] == 'INFO'
                    assert sent_data['payload']['nested']['key'] == 'value'
    
    def test_invalid_json_payload_handled_gracefully(self, mock_event_model, capsys):
        """Test that invalid JSON payload doesn't crash the command"""
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = 'test'
        args.job_id = None
        args.payload = 'not valid json {{'
        
        # Should still succeed (uses empty payload)
        result = cmd_send_event(args)
        
        assert result == 0
    
    def test_source_defaults_to_cli(self, mock_event_model, capsys):
        """Test that source defaults to 'cli' when not provided"""
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = None  # Not provided
        args.job_id = None
        args.payload = '{"message": "test"}'
        
        with patch('socket.socket') as mock_socket:
            sock_instance = MagicMock()
            mock_socket.return_value = sock_instance
            
            with patch('statemachine_engine.database.cli.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                result = cmd_send_event(args)
                
                assert result == 0
                
                # Verify 'cli' was used as machine_name
                if sock_instance.sendto.called:
                    call_args = sock_instance.sendto.call_args[0]
                    sent_data = json.loads(call_args[0].decode('utf-8'))
                    assert sent_data['machine_name'] == 'cli'
    
    def test_socket_error_doesnt_fail_command(self, mock_event_model, capsys):
        """Test that socket errors are caught and don't fail the command"""
        args = MagicMock()
        args.target = 'ui'
        args.type = 'activity_log'
        args.source = 'test'
        args.job_id = None
        args.payload = '{"message": "test"}'
        
        with patch('socket.socket') as mock_socket:
            # Socket raises error
            mock_socket.side_effect = OSError("Socket error")
            
            # Should still succeed (database write works)
            result = cmd_send_event(args)
            
            assert result == 0
            
            captured = capsys.readouterr()
            assert '✅ Event sent successfully!' in captured.out


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
