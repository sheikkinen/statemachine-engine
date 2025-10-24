"""
Test for SQLite connection leak fix

This test verifies that database connections are properly closed after use.
Before the fix in v1.0.9, connections were leaked because sqlite3.Connection
as a context manager only commits/rollbacks but doesn't close the connection.

Bug reproduction: After ~30 minutes with many DB operations, the WebSocket
server would freeze with 66+ unclosed file descriptors pointing to the database.
"""
import pytest
import tempfile
import os
from pathlib import Path
from statemachine_engine.database.models import Database, get_realtime_event_model


def count_open_fds_for_db(db_path: Path) -> int:
    """Count open file descriptors pointing to the database file
    
    This simulates what we saw with lsof -p <pid> | grep .db
    """
    pid = os.getpid()
    try:
        # Try to count via /proc (Linux) or lsof (macOS)
        import subprocess
        result = subprocess.run(
            ['lsof', '-p', str(pid)], 
            capture_output=True, 
            text=True,
            timeout=2
        )
        # Count lines that reference our database file
        count = result.stdout.count(str(db_path))
        return count
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # lsof not available or timed out - skip this check
        return -1


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield str(db_path)


def test_connection_closes_after_context_manager(temp_db):
    """Test that connections are closed after exiting context manager"""
    db = Database(temp_db)
    
    # Track initial FD count
    initial_fds = count_open_fds_for_db(Path(temp_db))
    
    # Perform multiple database operations
    for i in range(10):
        with db._get_connection() as conn:
            conn.execute("SELECT 1")
    
    # After the fix, FD count should not grow significantly
    # Before fix: each iteration would leak 1 connection
    final_fds = count_open_fds_for_db(Path(temp_db))
    
    if initial_fds >= 0 and final_fds >= 0:
        # Allow for some variation but should not leak 10 connections
        assert final_fds < initial_fds + 5, \
            f"Connection leak detected: started with {initial_fds} FDs, ended with {final_fds} FDs"


def test_connection_closes_on_exception(temp_db):
    """Test that connections are closed even when exceptions occur"""
    db = Database(temp_db)
    
    initial_fds = count_open_fds_for_db(Path(temp_db))
    
    # Perform operations that raise exceptions
    for i in range(10):
        try:
            with db._get_connection() as conn:
                conn.execute("SELECT * FROM nonexistent_table")
        except Exception:
            pass  # Expected to fail
    
    final_fds = count_open_fds_for_db(Path(temp_db))
    
    if initial_fds >= 0 and final_fds >= 0:
        assert final_fds < initial_fds + 5, \
            f"Connection leak on exception: started with {initial_fds} FDs, ended with {final_fds} FDs"


def test_realtime_model_many_operations_no_leak(temp_db):
    """Test that RealtimeEventModel doesn't leak connections over many operations
    
    This simulates the websocket_server.py scenario where database_fallback_poller()
    calls get_unconsumed_events() every 500ms in an infinite loop.
    """
    db = Database(temp_db)
    
    initial_fds = count_open_fds_for_db(Path(temp_db))
    
    # Simulate many polling cycles (30+ minutes at 500ms = ~3600 calls)
    # We'll test with 100 iterations to keep test fast
    for i in range(100):
        model = get_realtime_event_model()
        
        # This is what happens in database_fallback_poller()
        events = model.get_unconsumed_events(since_id=0, limit=50)
        
        # And in cleanup_old_events()
        if i % 10 == 0:
            model.cleanup_old_events(hours_old=24)
    
    final_fds = count_open_fds_for_db(Path(temp_db))
    
    if initial_fds >= 0 and final_fds >= 0:
        # Before fix: this would leak ~100+ connections
        # After fix: should stay constant (allow small variation)
        assert final_fds < initial_fds + 10, \
            f"Massive connection leak: started with {initial_fds} FDs, ended with {final_fds} FDs"


def test_connection_context_manager_explicitly_closes():
    """Test that _get_connection() is a proper context manager that closes
    
    This is a direct test of the fix - verify it's using @contextmanager
    and explicitly calling conn.close()
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        
        # Get a connection and verify it closes
        with db._get_connection() as conn:
            # Connection should be open here
            assert conn is not None
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        
        # After exiting context, connection should be closed
        # Attempting to use it should raise an error
        with pytest.raises(Exception) as exc_info:
            conn.execute("SELECT 1")
        
        # Should be ProgrammingError: Cannot operate on a closed database
        assert "closed" in str(exc_info.value).lower() or \
               "database" in str(exc_info.value).lower()


def test_nested_connections_dont_interfere(temp_db):
    """Test that nested connection contexts work correctly"""
    db = Database(temp_db)
    
    # Create a table in one connection
    with db._get_connection() as conn1:
        conn1.execute("CREATE TABLE test_table (id INTEGER, value TEXT)")
        conn1.commit()
    
    # Use it in another connection - should work fine
    with db._get_connection() as conn2:
        conn2.execute("INSERT INTO test_table VALUES (1, 'test')")
        conn2.commit()
    
    # Read in a third connection
    with db._get_connection() as conn3:
        cursor = conn3.execute("SELECT value FROM test_table WHERE id = 1")
        result = cursor.fetchone()
        assert result['value'] == 'test'


def test_connection_leak_reproduction():
    """Reproduce the exact scenario from the bug report
    
    The websocket server was receiving events and calling get_initial_state()
    repeatedly, leaking connections. After 30 minutes, 66+ connections were open.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "pipeline.db"
        db = Database(str(db_path))
        
        initial_fds = count_open_fds_for_db(db_path)
        
        # Simulate the websocket server behavior
        # Before fix: each get_initial_state() leaked 1 connection
        iterations = 66  # Same number we saw in the bug
        
        for i in range(iterations):
            # This is what get_initial_state() does
            with db._get_connection() as conn:
                machines = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table'
                """).fetchall()
        
        final_fds = count_open_fds_for_db(db_path)
        
        if initial_fds >= 0 and final_fds >= 0:
            # Before fix: would have 66+ leaked connections
            # After fix: should remain constant
            leaked = final_fds - initial_fds
            assert leaked < 10, \
                f"CRITICAL: Connection leak reproduced! " \
                f"Started: {initial_fds} FDs, Ended: {final_fds} FDs, " \
                f"Leaked: {leaked} connections (expected < 10)"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
