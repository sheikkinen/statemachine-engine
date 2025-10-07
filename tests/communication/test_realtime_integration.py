#!/usr/bin/env python3
"""
Integration test for Unix socket real-time communication

Tests:
1. WebSocket server can start and bind to Unix socket
2. State machine can emit events via Unix socket
3. WebSocket server receives and broadcasts events
4. Database fallback works when socket is unavailable
"""

import asyncio
import json
import socket
import time
import tempfile
import subprocess
import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from statemachine_engine.core.engine import StateMachineEngine, EventSocketManager
from statemachine_engine.database.models import Database, get_realtime_event_model

@pytest.mark.asyncio
async def test_unix_socket_emission():
    """Test that EventSocketManager can emit events to Unix socket"""
    print("🧪 Testing Unix socket event emission...")
    
    socket_path = '/tmp/test-face-changer-events.sock'
    
    # Remove existing socket
    if Path(socket_path).exists():
        Path(socket_path).unlink()
    
    # Create receiver socket
    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server_sock.bind(socket_path)
    server_sock.settimeout(2.0)  # 2 second timeout
    
    try:
        # Create emitter
        manager = EventSocketManager(socket_path)
        
        # Emit test event
        test_event = {
            'machine_name': 'test_machine',
            'event_type': 'state_change',
            'payload': {'from_state': 'a', 'to_state': 'b'}
        }
        
        success = manager.emit(test_event)
        
        if not success:
            print("❌ Failed to emit event")
            return False
        
        # Receive event
        data = server_sock.recv(4096)
        received_event = json.loads(data.decode())
        
        # Verify event
        if received_event == test_event:
            print("✅ Unix socket emission successful")
            return True
        else:
            print(f"❌ Event mismatch: expected {test_event}, got {received_event}")
            return False
            
    except socket.timeout:
        print("❌ Timeout waiting for event")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        server_sock.close()
        if Path(socket_path).exists():
            Path(socket_path).unlink()

@pytest.mark.asyncio
async def test_database_fallback():
    """Test that events are logged to database when socket fails"""
    print("🧪 Testing database fallback...")
    
    try:
        # Create engine with invalid socket path
        engine = StateMachineEngine(machine_name='test_machine')
        engine.event_socket = EventSocketManager('/invalid/socket/path')
        
        # Set up database context with a mock job model that has the db attribute
        db = Database()
        
        class MockJobModel:
            def __init__(self, db):
                self.db = db
        
        engine.context = {'job_model': MockJobModel(db)}
        
        # Emit event (should fall back to database)
        engine._emit_realtime_event('test_event', {'test': 'data'})
        
        # Check database for our specific test event
        realtime_model = get_realtime_event_model()
        events = realtime_model.get_unconsumed_events(limit=50)  # Get more events
        
        # Find our test event
        test_events = [e for e in events if e['event_type'] == 'test_event' and e['machine_name'] == 'test_machine']
        
        if test_events and test_events[0]['payload']['test'] == 'data':
            print("✅ Database fallback successful")
            return True
        else:
            print(f"❌ Database fallback failed - found {len(test_events)} test events")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

@pytest.mark.asyncio
async def test_websocket_server():
    """Test that WebSocket server can start and handle basic operations"""
    print("🧪 Testing WebSocket server startup...")
    
    # First check if server is already running
    try:
        import urllib.request
        response = urllib.request.urlopen('http://localhost:3002/health', timeout=2)
        if response.status == 200:
            print("✅ WebSocket server already running and accessible")
            return True
    except:
        pass  # Server not running, continue with test
    
    try:
        # Get the correct Python executable
        python_exe = '/Users/sheikki/Documents/src/face-changer/.venv/bin/python'
        if not Path(python_exe).exists():
            python_exe = sys.executable
        
        # Start WebSocket server as subprocess
        process = subprocess.Popen([
            python_exe, 'src/api/websocket_server.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait longer for server to start and retry connection
        for attempt in range(10):  # Try for up to 5 seconds
            await asyncio.sleep(0.5)
            try:
                response = urllib.request.urlopen('http://localhost:3002/health', timeout=2)
                if response.status == 200:
                    print("✅ WebSocket server started successfully")
                    result = True
                    break
            except:
                continue
        else:
            print("❌ WebSocket server failed to start within timeout")
            result = False
        
        # Stop server
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

@pytest.mark.asyncio
async def test_state_machine_integration():
    """Test state machine with real-time event emission"""
    print("🧪 Testing state machine with real-time events...")
    
    try:
        # Create minimal state machine config
        test_config = {
            'metadata': {'name': 'test_machine', 'machine_name': 'test'},
            'initial_state': 'start',
            'actions': {
                'start': [
                    {'type': 'log', 'message': 'Test started'}
                ],
                'end': []
            },
            'transitions': [
                {'from': 'start', 'event': 'test_event', 'to': 'end'}
            ]
        }
        
        # Create engine
        engine = StateMachineEngine('test_machine')
        engine.config = test_config
        engine.current_state = 'start'
        
        # Set up mock socket that captures events
        captured_events = []
        
        class MockEventSocket:
            def emit(self, event_data):
                captured_events.append(event_data)
                return True
        
        engine.event_socket = MockEventSocket()
        
        # Process test event
        await engine.process_event('test_event')
        
        # Check if event was captured
        if captured_events:
            event = captured_events[0]
            if (event['event_type'] == 'state_change' and 
                event['payload']['to_state'] == 'end'):
                print("✅ State machine integration successful")
                return True
        
        print("❌ State machine integration failed")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Run all integration tests"""
    print("🚀 Real-time Communication Integration Tests")
    print("=" * 50)
    
    tests = [
        test_unix_socket_emission,
        test_database_fallback,
        test_state_machine_integration,
        test_websocket_server
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)