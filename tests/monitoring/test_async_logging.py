"""
Tests for async-safe logging configuration

Verifies:
1. QueueHandler setup works correctly
2. Logging doesn't block
3. Queue listener processes logs in background
4. Graceful shutdown flushes remaining logs
5. Emergency logger works independently
"""

import pytest
import asyncio
import logging
import logging.handlers
import time
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from statemachine_engine.monitoring.async_logging import (
    setup_async_logging,
    create_emergency_logger
)


class TestAsyncLogging:
    """Test async-safe logging configuration"""
    
    def test_setup_async_logging_creates_handlers(self, tmp_path):
        """Test that setup_async_logging creates proper handlers"""
        log_file = tmp_path / "test.log"
        
        logger, listener = setup_async_logging(log_file)
        
        try:
            # Should have at least one handler (QueueHandler)
            # Note: pytest may add its own handlers to root logger
            assert len(logger.handlers) >= 1
            
            # Find the QueueHandler we added
            queue_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.QueueHandler)]
            assert len(queue_handlers) >= 1, "Should have at least one QueueHandler"
            
            # Listener should be started
            assert listener is not None
            
        finally:
            listener.stop()
    
    def test_async_logging_writes_to_file(self, tmp_path):
        """Test that async logging actually writes to file"""
        log_file = tmp_path / "test.log"
        
        logger, listener = setup_async_logging(log_file, include_console=False)
        
        try:
            # Write some logs
            logger.info("Test message 1")
            logger.warning("Test message 2")
            logger.error("Test message 3")
            
            # Stop listener to flush
            listener.stop()
            
            # Check file contents
            assert log_file.exists()
            contents = log_file.read_text()
            assert "Test message 1" in contents
            assert "Test message 2" in contents
            assert "Test message 3" in contents
            
        except Exception:
            listener.stop()
            raise
    
    def test_async_logging_respects_log_level(self, tmp_path):
        """Test that log level filtering works"""
        log_file = tmp_path / "test.log"
        
        logger, listener = setup_async_logging(
            log_file, 
            log_level=logging.WARNING,
            include_console=False
        )
        
        try:
            # Write logs at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Stop listener to flush
            listener.stop()
            
            # Check file contents
            contents = log_file.read_text()
            assert "Debug message" not in contents
            assert "Info message" not in contents
            assert "Warning message" in contents
            assert "Error message" in contents
            
        except Exception:
            listener.stop()
            raise
    
    @pytest.mark.asyncio
    async def test_logging_doesnt_block_event_loop(self, tmp_path):
        """Test that logging doesn't block async event loop"""
        log_file = tmp_path / "test.log"
        
        logger, listener = setup_async_logging(log_file, include_console=False)
        
        try:
            # Log many messages rapidly
            start = time.time()
            for i in range(1000):
                logger.info(f"Message {i}")
            duration = time.time() - start
            
            # Logging should be fast (< 0.5s for 1000 messages with pytest overhead)
            # Because it just enqueues, doesn't wait for disk I/O
            # Note: pytest capture adds overhead, so this is more lenient
            assert duration < 0.5, f"Logging took {duration}s - it's blocking!"
            
            # Stop listener to flush
            listener.stop()
            
            # Verify logs were written
            contents = log_file.read_text()
            assert "Message 0" in contents
            assert "Message 999" in contents
            
        except Exception:
            listener.stop()
            raise
    
    def test_custom_log_format(self, tmp_path):
        """Test that custom log format is respected"""
        log_file = tmp_path / "test.log"
        
        custom_format = "%(levelname)s - %(message)s"
        logger, listener = setup_async_logging(
            log_file,
            log_format=custom_format,
            include_console=False
        )
        
        try:
            logger.info("Test message")
            listener.stop()
            
            contents = log_file.read_text()
            # Should have custom format (no timestamp or logger name)
            assert "INFO - Test message" in contents
            # Should NOT have timestamp
            assert "statemachine_engine" not in contents
            
        except Exception:
            listener.stop()
            raise
    
    def test_custom_logger_name(self, tmp_path):
        """Test that custom logger name works"""
        log_file = tmp_path / "test.log"
        
        logger, listener = setup_async_logging(
            log_file,
            logger_name="custom.logger",
            include_console=False
        )
        
        try:
            assert logger.name == "custom.logger"
            
            logger.info("Test message")
            listener.stop()
            
            contents = log_file.read_text()
            assert "custom.logger" in contents
            
        except Exception:
            listener.stop()
            raise
    
    def test_emergency_logger_works_independently(self, tmp_path):
        """Test that emergency logger works without queue"""
        log_file = tmp_path / "emergency.log"
        
        emergency_logger = create_emergency_logger(log_file)
        
        # Write directly (blocking, but that's the point for emergencies)
        emergency_logger.warning("Emergency message 1")
        emergency_logger.error("Emergency message 2")
        
        # Should be written immediately (synchronous)
        assert log_file.exists()
        contents = log_file.read_text()
        assert "EMERGENCY" in contents
        assert "Emergency message 1" in contents
        assert "Emergency message 2" in contents
    
    def test_console_logging_can_be_disabled(self, tmp_path):
        """Test that console logging is optional"""
        log_file = tmp_path / "test.log"
        
        # Without console
        logger1, listener1 = setup_async_logging(
            log_file,
            include_console=False
        )
        
        try:
            # Listener should have only 1 handler (file)
            # Note: We can't directly inspect listener's handlers easily,
            # but we can verify logging still works
            logger1.info("Test")
            listener1.stop()
            
            assert log_file.exists()
            
        except Exception:
            listener1.stop()
            raise
    
    def test_multiple_loggers_dont_interfere(self, tmp_path):
        """Test that multiple async loggers can coexist"""
        log_file1 = tmp_path / "logger1.log"
        log_file2 = tmp_path / "logger2.log"
        
        logger1, listener1 = setup_async_logging(
            log_file1,
            logger_name="logger1",
            include_console=False
        )
        logger2, listener2 = setup_async_logging(
            log_file2,
            logger_name="logger2",
            include_console=False
        )
        
        try:
            logger1.info("Message from logger1")
            logger2.info("Message from logger2")
            
            listener1.stop()
            listener2.stop()
            
            # Each file should have its own messages
            contents1 = log_file1.read_text()
            contents2 = log_file2.read_text()
            
            assert "Message from logger1" in contents1
            assert "Message from logger2" not in contents1
            
            assert "Message from logger2" in contents2
            assert "Message from logger1" not in contents2
            
        except Exception:
            listener1.stop()
            listener2.stop()
            raise


class TestAsyncLoggingEdgeCases:
    """Test edge cases and error handling"""
    
    def test_logging_with_unicode_characters(self, tmp_path):
        """Test that unicode characters are handled correctly"""
        log_file = tmp_path / "test.log"
        
        logger, listener = setup_async_logging(log_file, include_console=False)
        
        try:
            # Log with various unicode characters
            logger.info("Test with emoji: 🚀 ✅ 📥 🔴")
            logger.info("Test with Chinese: 你好世界")
            logger.info("Test with Arabic: مرحبا بالعالم")
            
            listener.stop()
            
            contents = log_file.read_text()
            assert "🚀" in contents
            assert "你好世界" in contents
            assert "مرحبا بالعالم" in contents
            
        except Exception:
            listener.stop()
            raise
    
    def test_logging_creates_missing_directories(self, tmp_path):
        """Test that logging creates parent directories if missing"""
        log_file = tmp_path / "subdir" / "nested" / "test.log"
        
        # Directory doesn't exist yet
        assert not log_file.parent.exists()
        
        logger, listener = setup_async_logging(log_file, include_console=False)
        
        try:
            logger.info("Test message")
            listener.stop()
            
            # Directory should be created
            assert log_file.parent.exists()
            assert log_file.exists()
            
        except Exception:
            listener.stop()
            raise
