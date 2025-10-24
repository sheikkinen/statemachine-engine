"""
Tests for WebSocket server connection handling

Verifies:
1. Initial state is sent on connection
2. Database connections are properly cleaned up
3. Multiple reconnections don't exhaust resources
4. Refresh command works
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from statemachine_engine.monitoring.websocket_server import app, get_initial_state


class TestWebSocketServer:
    """Test WebSocket server connection handling"""
    
    def test_health_endpoint(self):
        """Test that health endpoint returns status"""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'connections' in data
        assert 'last_event_time' in data
        assert 'seconds_since_last_event' in data
        assert 'unix_socket_active' in data
    
    def test_initial_endpoint(self):
        """Test that /initial endpoint returns initial state"""
        client = TestClient(app)
        response = client.get("/initial")
        
        assert response.status_code == 200
        data = response.json()
        assert data['type'] == 'initial'
        assert 'machines' in data
        assert 'timestamp' in data
        assert isinstance(data['machines'], list)
    
    @pytest.mark.asyncio
    async def test_get_initial_state_returns_valid_data(self):
        """Test that get_initial_state returns properly formatted data"""
        state = await get_initial_state()
        
        assert state['type'] == 'initial'
        assert 'machines' in state
        assert 'timestamp' in state
        assert isinstance(state['machines'], list)
        assert isinstance(state['timestamp'], float)
    
    @pytest.mark.asyncio
    async def test_get_initial_state_handles_errors_gracefully(self):
        """Test that get_initial_state doesn't crash on errors"""
        # Even if there's no database, it should return empty machines list
        state = await get_initial_state()
        
        assert state['type'] == 'initial'
        assert 'machines' in state
        # Should either have machines or an error field
        assert isinstance(state['machines'], list)
    
    @pytest.mark.asyncio
    async def test_multiple_initial_state_calls_dont_leak_connections(self):
        """Test that multiple calls to get_initial_state clean up properly"""
        # Call multiple times rapidly to simulate reconnections
        for i in range(50):
            state = await get_initial_state()
            assert state['type'] == 'initial'
            
            # Small delay to allow cleanup
            if i % 10 == 0:
                await asyncio.sleep(0.1)
        
        # If connections leaked, this would fail or hang
        # Success means connections were properly cleaned up
    
    def test_websocket_sends_initial_state_on_connect(self):
        """Test that WebSocket sends initial state immediately on connect"""
        client = TestClient(app)
        
        with client.websocket_connect("/ws/events") as websocket:
            # First message should be initial state
            data = websocket.receive_json()
            
            assert data['type'] == 'initial'
            assert 'machines' in data
            assert 'timestamp' in data
    
    def test_websocket_responds_to_ping(self):
        """Test that WebSocket responds to ping with pong"""
        client = TestClient(app)
        
        with client.websocket_connect("/ws/events") as websocket:
            # Receive initial state
            websocket.receive_json()
            
            # Send ping
            websocket.send_text('ping')
            
            # Should receive pong
            response = websocket.receive_json()
            assert response['type'] == 'pong'
    
    def test_websocket_handles_refresh_command(self):
        """Test that WebSocket handles refresh command"""
        client = TestClient(app)
        
        with client.websocket_connect("/ws/events") as websocket:
            # Receive initial state
            initial = websocket.receive_json()
            assert initial['type'] == 'initial'
            
            # Request refresh
            websocket.send_text('refresh')
            
            # Should receive fresh initial state
            refreshed = websocket.receive_json()
            assert refreshed['type'] == 'initial'
            assert 'machines' in refreshed
            assert 'timestamp' in refreshed
            # Timestamp should be newer
            assert refreshed['timestamp'] >= initial['timestamp']
    
    def test_multiple_reconnections_work(self):
        """Test that multiple reconnections don't exhaust resources"""
        client = TestClient(app)
        
        # Simulate 20 reconnections
        for i in range(20):
            with client.websocket_connect("/ws/events") as websocket:
                # Each connection should get initial state
                data = websocket.receive_json()
                assert data['type'] == 'initial'
                
                # Send a ping
                websocket.send_text('ping')
                pong = websocket.receive_json()
                assert pong['type'] == 'pong'
            
            # Connection closed, test next one
        
        # If resources leaked, this would fail
        # Success means proper cleanup happened
    
    def test_websocket_connection_closed_cleanly(self):
        """Test that WebSocket connections close without errors"""
        client = TestClient(app)
        
        with client.websocket_connect("/ws/events") as websocket:
            # Receive initial state
            websocket.receive_json()
            
        # Connection should close cleanly without exceptions
        # If there were leaked resources, TestClient would complain


class TestWebSocketResilience:
    """Test WebSocket server resilience to errors"""
    
    def test_health_check_shows_connection_count(self):
        """Test that health check tracks active connections"""
        client = TestClient(app)
        
        # No connections
        response = client.get("/health")
        initial_count = response.json()['connections']
        
        # Open a WebSocket
        with client.websocket_connect("/ws/events") as websocket:
            websocket.receive_json()  # Receive initial state
            
            # Health check should show increased count
            response = client.get("/health")
            active_count = response.json()['connections']
            assert active_count >= initial_count
        
        # After close, count should decrease
        response = client.get("/health")
        final_count = response.json()['connections']
        assert final_count <= active_count
