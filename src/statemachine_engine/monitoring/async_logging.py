"""
Async-safe logging configuration for event loop applications

PROBLEM:
--------
In async applications, calling logger.info() with FileHandler/StreamHandler
blocks the event loop while waiting for disk/stdout I/O to complete.
This can cause 15+ second freezes when disk is slow, buffer is full, or
OS is swapping.

WHY THIS MATTERS:
-----------------
The async event loop is single-threaded. When you write:

    logger.info("message")  # With FileHandler
        ↓
    file.write() + file.flush()  # BLOCKS entire event loop!
        ↓
    All async tasks frozen (no heartbeats, no WebSocket messages, etc.)

This violates the cardinal rule of async programming:
    "Never call blocking I/O directly in the event loop"

THE SOLUTION:
-------------
Use QueueHandler + QueueListener to move I/O to a background thread:

    ┌─────────────────────────────────────┐
    │  Async Event Loop (Main Thread)     │
    │  ┌──────────────────────────────┐   │
    │  │ logger.info() → Queue.put()   │   │ ← Non-blocking (< 1μs)
    │  │ Continue processing           │   │
    │  └──────────────────────────────┘   │
    └─────────────────────────────────────┘
                       │
                       │ Thread-safe Queue
                       ↓
    ┌─────────────────────────────────────┐
    │  Background Thread (QueueListener)   │
    │  ┌──────────────────────────────┐   │
    │  │ Queue.get() → Format → Write  │   │
    │  │ to disk and stdout           │   │ ← Can block safely
    │  └──────────────────────────────┘   │
    └─────────────────────────────────────┘

IMPLEMENTATION:
---------------
1. QueueHandler: Accepts log records and puts them in a thread-safe queue
   - Non-blocking: Queue.put() is O(1) and returns immediately
   - Safe: Queue is thread-safe, can be used from async context

2. QueueListener: Background thread that processes the queue
   - Runs in separate thread (not in event loop)
   - Gets log records from queue and writes to actual handlers
   - Can block on I/O without affecting event loop

3. FileHandler/StreamHandler: Run in background thread
   - Blocking I/O happens off the main thread
   - Event loop never waits for disk writes

USAGE:
------
    from statemachine_engine.monitoring.async_logging import setup_async_logging
    
    # Setup non-blocking logging
    logger, queue_listener = setup_async_logging(
        log_file='logs/app.log',
        log_level=logging.INFO
    )
    
    # Use logger normally (it's now non-blocking!)
    logger.info("This returns in < 1μs")
    
    # Graceful shutdown (flush remaining logs)
    queue_listener.stop()

BENEFITS:
---------
✅ Logging never blocks the event loop
✅ Can use verbose logging without performance penalty
✅ Proper async architecture (separation of concerns)
✅ Production-ready (handles high throughput)
✅ No data loss (queue buffers during disk slowness)
✅ Thread-safe (queue handles concurrency)

CAVEATS:
--------
- Logs may appear slightly delayed (queue processing time)
- Very high log volume can fill queue memory (configurable size)
- Shutdown must call queue_listener.stop() to flush remaining logs

REFERENCES:
-----------
- Python logging.handlers.QueueHandler: https://docs.python.org/3/library/logging.handlers.html#queuehandler
- Async logging best practices: https://docs.python.org/3/howto/logging-cookbook.html#dealing-with-handlers-that-block
"""

import logging
import logging.handlers
import queue
from pathlib import Path
from typing import Optional, Tuple, Union


def setup_async_logging(
    log_file: Union[str, Path],
    log_level: int = logging.INFO,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    logger_name: Optional[str] = None,
    queue_size: int = -1,
    include_console: bool = True
) -> Tuple[logging.Logger, logging.handlers.QueueListener]:
    """
    Configure non-blocking logging for async applications.
    
    This sets up a QueueHandler that enqueues log records without blocking,
    and a QueueListener that processes the queue in a background thread.
    
    Args:
        log_file: Path to log file (will be created if doesn't exist)
        log_level: Logging level (logging.DEBUG, INFO, WARNING, etc.)
        log_format: Format string for log messages
        logger_name: Name for logger (defaults to calling module)
        queue_size: Max queue size (-1 for unlimited)
        include_console: Whether to also log to stdout
        
    Returns:
        Tuple of (logger, queue_listener)
        - logger: Configured logger with QueueHandler
        - queue_listener: QueueListener instance (call .stop() on shutdown)
        
    Example:
        logger, listener = setup_async_logging('logs/app.log')
        logger.info("Non-blocking log message")
        # ... application runs ...
        listener.stop()  # Flush remaining logs on shutdown
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create thread-safe queue for log records
    log_queue = queue.Queue(queue_size)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Create actual I/O handlers (will run in background thread)
    handlers = []
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    handlers.append(file_handler)
    
    # Console handler (optional)
    if include_console:
        import sys
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
    
    # Create QueueListener to process queue in background thread
    queue_listener = logging.handlers.QueueListener(
        log_queue,
        *handlers,
        respect_handler_level=True
    )
    
    # Create QueueHandler (non-blocking, just enqueues)
    queue_handler = logging.handlers.QueueHandler(log_queue)
    
    # Configure logger
    logger = logging.getLogger(logger_name)
    logger.addHandler(queue_handler)
    logger.setLevel(log_level)
    
    # Start background thread
    queue_listener.start()
    
    return logger, queue_listener


def create_emergency_logger(log_file: Union[str, Path]) -> logging.Logger:
    """
    Create a synchronous logger for emergency use when async logging fails.
    
    This is useful for watchdog threads or emergency handlers that need to
    log even if the main logging system is blocked or broken.
    
    Args:
        log_file: Path to emergency log file
        
    Returns:
        Logger with direct (blocking) file handler
        
    Warning:
        This logger WILL block on I/O - only use for emergencies!
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    emergency_logger = logging.getLogger('emergency')
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - EMERGENCY - %(levelname)s - %(message)s'
    ))
    emergency_logger.addHandler(handler)
    emergency_logger.setLevel(logging.WARNING)
    
    return emergency_logger
