"""
Tests for EventSocketManager lazy reconnect (feature-request-event-socket-lazy-reconnect).

Tests that:
1. emit() retries _connect() when sock is None (lazy reconnect)
2. Failed reconnect logs at WARNING level, not DEBUG
3. Reconnect attempts are rate-limited to once per 5 seconds
4. _connect() closes socket fd on failure (no leak)
"""
import logging
import socket
import time
from unittest.mock import MagicMock, patch

import pytest

from statemachine_engine.core.engine import EventSocketManager


@pytest.fixture
def disconnected_manager():
    """Create an EventSocketManager that failed initial connect."""
    with patch.object(EventSocketManager, '_connect'):
        mgr = EventSocketManager(socket_path='/tmp/test-no-exist.sock')
        mgr.sock = None  # simulate failed initial connect
        mgr._last_connect_attempt = 0.0  # allow immediate reconnect
    return mgr


class TestLazyReconnect:
    """emit() should attempt reconnect when sock is None."""

    def test_emit_retries_connect_when_sock_is_none(self, disconnected_manager):
        """emit() calls _connect() and retries send after successful reconnect."""
        mgr = disconnected_manager
        fake_sock = MagicMock()

        def reconnect_succeeds():
            mgr.sock = fake_sock

        mgr._connect = MagicMock(side_effect=reconnect_succeeds)

        result = mgr.emit({"type": "test_event"})

        mgr._connect.assert_called_once()
        assert result is True
        fake_sock.send.assert_called_once()

    def test_emit_drops_logged_at_warning(self, disconnected_manager, caplog):
        """When reconnect fails, the drop is logged at WARNING (not DEBUG)."""
        mgr = disconnected_manager
        mgr._connect = MagicMock()  # does nothing, sock stays None

        with caplog.at_level(logging.DEBUG):
            result = mgr.emit({"type": "test_event"})

        assert result is False
        # Must have a WARNING-level record about the drop
        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("socket" in m.message.lower() or "emit" in m.message.lower() for m in warning_msgs), (
            f"Expected WARNING about socket/emit, got: {[m.message for m in warning_msgs]}"
        )

    def test_reconnect_rate_limited(self, disconnected_manager):
        """_connect() is not called more than once within 5 seconds."""
        mgr = disconnected_manager
        call_count = 0
        def counting_connect():
            nonlocal call_count
            call_count += 1
            mgr._last_connect_attempt = time.monotonic()  # real implementation sets this

        mgr._connect = MagicMock(side_effect=counting_connect)

        # Two rapid emit calls — first triggers reconnect, second is rate-limited
        mgr.emit({"type": "event_1"})
        mgr.emit({"type": "event_2"})

        assert call_count == 1


class TestConnectFdLeak:
    """_connect() must not leak file descriptors on failure."""

    def test_connect_closes_socket_on_failure(self):
        """If connect() raises, the socket fd is closed before setting None."""
        fake_sock = MagicMock(spec=socket.socket)
        fake_sock.connect.side_effect = ConnectionRefusedError("no listener")

        with patch('socket.socket', return_value=fake_sock):
            mgr_cls = EventSocketManager.__new__(EventSocketManager)
            mgr_cls.socket_path = '/tmp/test-no-exist.sock'
            mgr_cls.sock = None
            mgr_cls._last_connect_attempt = 0.0
            mgr_cls.logger = logging.getLogger('test')
            mgr_cls._connect()

        fake_sock.close.assert_called_once()
        assert mgr_cls.sock is None
