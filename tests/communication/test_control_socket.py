"""
Test suite for Unix socket control mechanism

Tests control socket creation, event reception, and wake_up triggering
"""
import pytest
import asyncio
import json
import socket
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from statemachine_engine.core.engine import StateMachineEngine


class TestControlSocket:
    """Unit tests for control socket functionality"""
    
    @pytest.mark.asyncio
    async def test_socket_creation(self):
        """Test that control socket is created correctly"""
        engine = StateMachineEngine(machine_name='test_machine')
        
        # Load minimal config
        config = {
            'metadata': {'name': 'Test Machine'},
            'initial_state': 'waiting',
            'actions': {'waiting': []},
            'transitions': {}
        }
        
        with patch.object(engine, '_register_actions', new=AsyncMock()):
            engine.config = config
            engine.current_state = 'waiting'
            engine._create_control_socket()
        
        # Check socket was created
        assert engine.control_socket is not None
        
        # Check socket file exists
        socket_path = Path(f'/tmp/face-changer-control-test_machine.sock')
        assert socket_path.exists()
        
        # Cleanup
        engine._cleanup_sockets()
        assert not socket_path.exists()
    
    @pytest.mark.asyncio
    async def test_stale_socket_cleanup(self):
        """Test that stale socket files are cleaned up on startup"""
        machine_name = 'test_stale_machine'
        socket_path = Path(f'/tmp/face-changer-control-{machine_name}.sock')
        
        # Create a stale socket file
        socket_path.touch()
        assert socket_path.exists()
        
        # Create engine (should clean up stale socket)
        engine = StateMachineEngine(machine_name=machine_name)
        engine.config = {'metadata': {}, 'initial_state': 'waiting', 'actions': {}, 'transitions': {}}
        engine._create_control_socket()
        
        # Socket should still exist but be bound to new socket
        assert socket_path.exists()
        
        # Cleanup
        engine._cleanup_sockets()
    
    @pytest.mark.asyncio
    async def test_new_job_event_triggers_wake_up(self):
        """Test that new_job event triggers wake_up"""
        engine = StateMachineEngine(machine_name='test_wake_machine')
        
        config = {
            'metadata': {},
            'initial_state': 'waiting',
            'actions': {'waiting': [], 'checking': []},
            'transitions': [
                {'from': 'waiting', 'to': 'checking', 'event': 'wake_up'}
            ]
        }
        
        with patch.object(engine, '_register_actions', new=AsyncMock()):
            engine.config = config
            engine.current_state = 'waiting'
            engine._create_control_socket()
        
        # Send new_job event via socket
        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        event = {'type': 'new_job', 'machine': 'test_wake_machine', 'timestamp': int(time.time())}
        
        socket_path = f'/tmp/face-changer-control-test_wake_machine.sock'
        client_sock.sendto(json.dumps(event).encode('utf-8'), socket_path)
        client_sock.close()
        
        # Small delay to ensure socket is ready
        await asyncio.sleep(0.01)
        
        # Check for the event
        await engine._check_control_socket()
        
        # Should have transitioned to 'checking' state
        assert engine.current_state == 'checking'
        
        # Cleanup
        engine._cleanup_sockets()
    
    @pytest.mark.asyncio
    async def test_inter_machine_event_handling(self):
        """Test that inter-machine events are stored in context"""
        engine = StateMachineEngine(machine_name='test_receiver')
        
        config = {
            'metadata': {},
            'initial_state': 'waiting',
            'actions': {'waiting': [], 'processing': []},
            'transitions': [
                {'from': 'waiting', 'to': 'processing', 'event': 'sdxl_job_done'}
            ]
        }
        
        with patch.object(engine, '_register_actions', new=AsyncMock()):
            engine.config = config
            engine.current_state = 'waiting'
            engine._create_control_socket()
        
        # Send inter-machine event
        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        event = {
            'type': 'sdxl_job_done',
            'payload': {'job_id': 'test123', 'status': 'completed'},
            'job_id': 'test123'
        }
        
        socket_path = f'/tmp/face-changer-control-test_receiver.sock'
        client_sock.sendto(json.dumps(event).encode('utf-8'), socket_path)
        client_sock.close()
        
        # Small delay to ensure socket is ready
        await asyncio.sleep(0.01)
        
        # Check for the event
        await engine._check_control_socket()
        
        # Event data should be in context
        assert 'event_data' in engine.context
        assert engine.context['event_data']['type'] == 'sdxl_job_done'
        assert engine.context['event_data']['payload']['job_id'] == 'test123'
        
        # Should have transitioned
        assert engine.current_state == 'processing'
        
        # Cleanup
        engine._cleanup_sockets()
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test that invalid JSON doesn't crash the engine"""
        engine = StateMachineEngine(machine_name='test_invalid')
        
        config = {
            'metadata': {},
            'initial_state': 'waiting',
            'actions': {'waiting': []},
            'transitions': {}
        }
        
        with patch.object(engine, '_register_actions', new=AsyncMock()):
            engine.config = config
            engine.current_state = 'waiting'
            engine._create_control_socket()
        
        # Send invalid JSON
        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        socket_path = f'/tmp/face-changer-control-test_invalid.sock'
        client_sock.sendto(b'{invalid json}', socket_path)
        client_sock.close()
        
        # Should not raise exception
        await engine._check_control_socket()
        
        # State should remain unchanged
        assert engine.current_state == 'waiting'
        
        # Cleanup
        engine._cleanup_sockets()
    
    @pytest.mark.asyncio
    async def test_socket_permission_error(self):
        """Test graceful handling when socket cannot be created"""
        # Try to create socket in restricted directory
        with patch('pathlib.Path.unlink') as mock_unlink:
            mock_unlink.side_effect = PermissionError("Cannot delete socket")
            
            engine = StateMachineEngine(machine_name='test_permission')
            engine.config = {'metadata': {}}
            
            # Should not raise exception
            engine._create_control_socket()
            
            # Socket should be None if creation failed
            # (actual behavior depends on implementation)
    
    @pytest.mark.asyncio
    async def test_multiple_events_in_sequence(self):
        """Test handling multiple events sent rapidly"""
        engine = StateMachineEngine(machine_name='test_multiple')
        
        config = {
            'metadata': {},
            'initial_state': 'waiting',
            'actions': {'waiting': [], 'checking': []},
            'transitions': [
                {'from': 'waiting', 'to': 'checking', 'event': 'wake_up'},
                {'from': 'checking', 'to': 'checking', 'event': 'wake_up'}
            ]
        }
        
        with patch.object(engine, '_register_actions', new=AsyncMock()):
            engine.config = config
            engine.current_state = 'waiting'
            engine._create_control_socket()
        
        socket_path = f'/tmp/face-changer-control-test_multiple.sock'
        
        # Send 5 events rapidly
        for i in range(5):
            client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            event = {'type': 'wake_up', 'timestamp': int(time.time()) + i}  # Use wake_up directly
            client_sock.sendto(json.dumps(event).encode('utf-8'), socket_path)
            client_sock.close()
            await asyncio.sleep(0.01)  # Small delay between sends
        
        # Process all events
        for _ in range(5):
            await engine._check_control_socket()
            await asyncio.sleep(0.01)  # Small delay between checks
        
        # Should be in checking state
        assert engine.current_state == 'checking'
        
        # Cleanup
        engine._cleanup_sockets()


class TestIntegration:
    """Integration tests for end-to-end socket communication"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_job_submission(self):
        """Test complete flow: job insert → socket notify → wake up → process"""
        # This is a placeholder for integration test
        # Would require full database and state machine setup
        pass
    
    @pytest.mark.asyncio
    async def test_inter_machine_coordination(self):
        """Test two machines communicating via sockets"""
        # This is a placeholder for integration test
        # Would require running multiple state machines
        pass
    
    @pytest.mark.asyncio  
    async def test_latency_measurement(self):
        """Measure socket event latency"""
        engine = StateMachineEngine(machine_name='test_latency')
        
        config = {
            'metadata': {},
            'initial_state': 'waiting',
            'actions': {'waiting': []},
            'transitions': {'waiting': {'wake_up': 'checking'}}
        }
        
        with patch.object(engine, '_register_actions', new=AsyncMock()):
            engine.config = config
            engine.current_state = 'waiting'
            engine._create_control_socket()
        
        socket_path = f'/tmp/face-changer-control-test_latency.sock'
        
        # Measure latency over 100 iterations
        latencies = []
        
        for _ in range(100):
            start = time.perf_counter()
            
            # Send event
            client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            event = {'type': 'new_job', 'timestamp': int(time.time())}
            client_sock.sendto(json.dumps(event).encode('utf-8'), socket_path)
            client_sock.close()
            
            # Process event
            await engine._check_control_socket()
            
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
            
            # Reset state
            engine.current_state = 'waiting'
        
        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[94]  # 95th percentile
        
        print(f"\n=== Socket Latency Test ===")
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"P95 latency: {p95_latency:.2f}ms")
        print(f"Min latency: {min(latencies):.2f}ms")
        print(f"Max latency: {max(latencies):.2f}ms")
        
        # Assert latency is reasonable (<10ms for local Unix sockets)
        assert avg_latency < 10, f"Average latency too high: {avg_latency}ms"
        assert p95_latency < 20, f"P95 latency too high: {p95_latency}ms"
        
        # Cleanup
        engine._cleanup_sockets()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
