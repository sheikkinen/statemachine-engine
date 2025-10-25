"""
WebSocket server for real-time state machine event streaming

Listens on:
- Unix socket: /tmp/statemachine-events.sock (from state machines)
- WebSocket: ws://localhost:3002/ws/events (to browsers)

Version: 1.0.26 - Fixed ALL websocket.send_json() calls (initial state, keepalive ping, pong, refresh)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import socket
import json
import logging
import time
from pathlib import Path
from typing import Set, Dict
import sys
import functools
import threading
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from statemachine_engine.database.models import Database, get_realtime_event_model

# Setup logging to file and console
log_dir = Path.cwd() / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "websocket-server.log"

# Configure logging with both file and console handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to {log_file}")

# ============================================================================
# SAFE JSON SERIALIZATION
# ============================================================================

def safe_json_dumps(obj: dict, max_size: int = 10000, indent: int = 2) -> str:
    """
    Safely serialize JSON with size limits to prevent blocking.
    Returns truncated version if too large, or error message if serialization fails.
    """
    try:
        json_str = json.dumps(obj, indent=indent)
        if len(json_str) > max_size:
            return f"[TRUNCATED - {len(json_str)} bytes total]\n{json_str[:max_size]}..."
        return json_str
    except Exception as e:
        return f"[JSON serialization failed: {e}]"

def safe_json_dumps_compact(obj: dict, timeout_seconds: float = 0.1) -> tuple[str, bool]:
    """
    Safely serialize JSON in compact form (for WebSocket sending).
    Returns (json_string, success_flag).
    Uses compact separators like ws.send_json() does.
    
    NOTE: Even though we can't truly timeout a synchronous json.dumps(),
    we catch exceptions and return error messages. The timeout is aspirational.
    The real protection is that we do this OUTSIDE the WebSocket send.
    """
    try:
        # This can still block, but at least it's outside ws.send_json()
        # so the issue is more visible and doesn't look like a WebSocket timeout
        json_str = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        return (json_str, True)
    except RecursionError as e:
        logger.error(f"JSON serialization recursion error (circular reference?): {e}")
        return (f'{{"error":"serialization_failed","message":"circular_reference"}}', False)
    except TypeError as e:
        logger.error(f"JSON serialization type error (non-serializable object?): {e}")
        return (f'{{"error":"serialization_failed","message":"non_serializable_object"}}', False)
    except Exception as e:
        logger.error(f"JSON serialization failed: {e}")
        return (f'{{"error":"serialization_failed","message":"{str(e)}"}}', False)

# ============================================================================

# ============================================================================
# HANG DETECTION & PERFORMANCE MONITORING
# ============================================================================

class PerformanceMonitor:
    """Monitor for detecting server hangs and performance issues"""
    
    def __init__(self):
        self.last_heartbeat = time.time()
        self.operation_times = {}
        self.watchdog_enabled = True
        
    def heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = time.time()
        
    def log_operation(self, name: str, duration_ms: float):
        """Track operation timing"""
        if duration_ms > 100:  # Warn on operations > 100ms
            logger.warning(f"⚠️  SLOW OPERATION: {name} took {duration_ms:.2f}ms")
        self.operation_times[name] = (time.time(), duration_ms)

def log_timing(operation_name: str, warn_threshold_ms: float = 100):
    """Decorator to log operation timing and detect slow operations"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            logger.debug(f"⏱️  START: {operation_name}")
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                perf_monitor.log_operation(operation_name, duration_ms)
                if duration_ms > warn_threshold_ms:
                    logger.warning(f"⚠️  SLOW: {operation_name} took {duration_ms:.2f}ms")
                else:
                    logger.debug(f"⏱️  END: {operation_name} ({duration_ms:.2f}ms)")
                perf_monitor.heartbeat()  # Update heartbeat on successful operation
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(f"❌ FAILED: {operation_name} after {duration_ms:.2f}ms: {e}")
                raise
        return wrapper
    return decorator

class WatchdogThread(threading.Thread):
    """Watchdog that dumps stack traces if server hangs"""
    
    def __init__(self, monitor: PerformanceMonitor, timeout: int = 15):
        super().__init__(daemon=True, name="Watchdog")
        self.monitor = monitor
        self.timeout = timeout
        self.running = True
        
    def run(self):
        """Monitor heartbeat and dump stack on hang"""
        logger.info(f"🐕 Watchdog started with {self.timeout}s timeout")
        while self.running:
            time.sleep(2)  # Check every 2 seconds
            time_since_heartbeat = time.time() - self.monitor.last_heartbeat
            
            if time_since_heartbeat > self.timeout:
                hang_report = []
                try:
                    hang_msg = f"🚨 SERVER HANG DETECTED: No heartbeat for {time_since_heartbeat:.1f}s"
                    logger.critical(hang_msg)
                    hang_report.append(hang_msg)
                    
                    trace_msg = "🚨 DUMPING ALL THREAD STACK TRACES:"
                    logger.critical(trace_msg)
                    hang_report.append(trace_msg)
                    
                    # Dump stack traces for all threads
                    for thread_id, frame in sys._current_frames().items():
                        try:
                            separator = f"\n{'='*80}"
                            logger.critical(separator)
                            hang_report.append(separator)
                            
                            thread_name = 'Unknown'
                            try:
                                if thread_id == threading.get_ident():
                                    thread_name = threading.current_thread().name
                                else:
                                    # Find thread by ID
                                    for t in threading.enumerate():
                                        if t.ident == thread_id:
                                            thread_name = t.name
                                            break
                            except:
                                pass
                            
                            thread_info = f"Thread {thread_id} ({thread_name}):"
                            logger.critical(thread_info)
                            hang_report.append(thread_info)
                            
                            stack_trace = ''.join(traceback.format_stack(frame))
                            logger.critical(stack_trace)
                            hang_report.append(stack_trace)
                        except Exception as e:
                            error_msg = f"Failed to dump stack for thread {thread_id}: {e}"
                            logger.critical(error_msg)
                            hang_report.append(error_msg)
                    
                    final_separator = f"{'='*80}\n"
                    logger.critical(final_separator)
                    hang_report.append(final_separator)
                    
                except Exception as e:
                    error_msg = f"Failed to dump stack traces: {e}"
                    logger.critical(error_msg)
                    hang_report.append(error_msg)
                finally:
                    # Also write to emergency file in case logger is blocking
                    try:
                        emergency_file = Path.cwd() / "logs" / "hang-emergency.log"
                        emergency_file.parent.mkdir(exist_ok=True)
                        with open(emergency_file, "a") as f:
                            f.write(f"\n{'='*80}\n")
                            f.write(f"HANG DETECTED AT {time.time()}\n")
                            f.write('\n'.join(hang_report))
                            f.write(f"\n{'='*80}\n")
                            f.flush()
                    except:
                        pass  # If emergency log fails, nothing we can do
                    
                    # Reset heartbeat to avoid spam (one dump per hang)
                    self.monitor.last_heartbeat = time.time()

# Global performance monitor and watchdog
perf_monitor = PerformanceMonitor()
watchdog = WatchdogThread(perf_monitor, timeout=15)
watchdog.start()

# ============================================================================

app = FastAPI(title="Face Changer Event Stream")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EventBroadcaster:
    """Manages WebSocket connections and broadcasts events"""

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.last_event_time = time.time()

    async def connect(self, websocket: WebSocket):
        """Add new WebSocket connection"""
        await websocket.accept()
        self.connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.connections)}")

    @log_timing("broadcast_event", warn_threshold_ms=50)
    async def broadcast(self, event: dict):
        """Send event to all connected clients"""
        logger.info(f"🔵 ENTERED broadcast() at {time.time()}")
        self.last_event_time = time.time()

        # Remove disconnected clients
        dead_connections = set()
        logger.info(f"🔵 Starting iteration over {len(self.connections)} connections")
        for ws in self.connections:
            try:
                client_id = id(ws)
                event_type = event.get('type', 'unknown')
                logger.info(f"📤 Broadcasting to client {client_id}: {event_type} event")
                
                # CRITICAL FIX: Pre-serialize JSON safely to avoid blocking
                # ws.send_json() calls json.dumps() synchronously BEFORE the await!
                # This was the root cause of 15-17s freezes
                logger.info(f"⏱️  About to serialize JSON at {time.time()}")
                event_json, success = safe_json_dumps_compact(event)
                logger.info(f"⏱️  JSON serialization complete at {time.time()}, success={success}")
                
                if not success:
                    logger.error(f"❌ Failed to serialize event for client {client_id}, skipping")
                    continue
                    
                logger.info(f"📦 Serialized {len(event_json)} bytes for client {client_id}")
                
                # Now send pre-serialized JSON - timeout only covers the send, not serialization
                logger.info(f"⏱️  About to call ws.send_text() at {time.time()}")
                await asyncio.wait_for(ws.send_text(event_json), timeout=2.0)
                logger.info(f"⏱️  ws.send_text() returned at {time.time()}")
                logger.info(f"✅ Sent to client {client_id}")
            except asyncio.TimeoutError:
                logger.warning(f"⏱️  Client {id(ws)}: Send timed out after 2s, marking as dead")
                dead_connections.add(ws)
            except Exception as e:
                logger.warning(f"Failed to send to client {id(ws)}: {e}")
                dead_connections.add(ws)

        self.connections -= dead_connections
        if dead_connections:
            logger.info(f"Removed {len(dead_connections)} dead connections")

broadcaster = EventBroadcaster()

def check_process_running(machine_name: str) -> bool:
    """Check if a state machine process is running"""
    try:
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=2)
        output = result.stdout
        return 'state_machine/cli.py' in output and machine_name in output
    except Exception as e:
        logger.warning(f"Failed to check process for {machine_name}: {e}")
        return False

@log_timing("get_initial_state", warn_threshold_ms=200)
async def get_initial_state() -> dict:
    """Get initial state snapshot with proper connection cleanup"""
    db = Database()
    try:
        # Get current machine states
        with db._get_connection() as conn:
            machines = conn.execute("""
                SELECT machine_name, current_state, last_activity, metadata
                FROM machine_state
                ORDER BY machine_name
            """).fetchall()

        # Convert to dict and add running status (async-safe)
        machines_data = []
        for machine in machines:
            machine_dict = dict(machine)
            # Skip process check to avoid blocking - rely on last_activity instead
            # Process check can hang and block the event loop
            machine_dict['running'] = False  # Deprecated, use last_activity timestamp
            machines_data.append(machine_dict)

        return {
            'type': 'initial',
            'machines': machines_data,
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get initial state: {e}", exc_info=True)
        return {
            'type': 'initial',
            'machines': [],
            'timestamp': time.time(),
            'error': str(e)
        }

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming"""
    client_id = id(websocket)  # Unique ID for logging
    
    try:
        await broadcaster.connect(websocket)
        logger.info(f"Client {client_id} connected from {websocket.client}")

        # Send initial state snapshot (with proper cleanup)
        try:
            logger.info(f"📋 Client {client_id}: Fetching initial state...")
            initial_state = await get_initial_state()
            logger.info(f"📋 Client {client_id}: Sending initial state with {len(initial_state.get('machines', []))} machines")
            logger.info(f"📦 Initial state data: {safe_json_dumps(initial_state)}")
            # Pre-serialize to avoid blocking event loop
            initial_json, success = safe_json_dumps_compact(initial_state)
            if not success:
                logger.error(f"❌ Client {client_id}: Failed to serialize initial state")
                raise ValueError("Failed to serialize initial state")
            await websocket.send_text(initial_json)
            logger.info(f"✅ Client {client_id}: Initial state sent successfully")
        except Exception as e:
            logger.error(f"❌ Client {client_id}: Failed to send initial state: {e}", exc_info=True)

        # Keep connection alive with periodic pings - run as background task
        async def send_keepalive():
            """Send periodic pings to keep WebSocket connection alive"""
            ping_interval = 10  # Send ping every 10 seconds (reduced from 20 for client compatibility)
            try:
                while True:
                    await asyncio.sleep(ping_interval)
                    try:
                        ping_data = {'type': 'ping', 'timestamp': time.time()}
                        logger.info(f"🏓 Client {client_id}: Sending keepalive ping")
                        logger.info(f"📦 Ping data: {safe_json_dumps(ping_data)}")
                        # Pre-serialize to avoid blocking event loop
                        ping_json, success = safe_json_dumps_compact(ping_data)
                        if success:
                            await websocket.send_text(ping_json)
                            logger.info(f"✅ Client {client_id}: Keepalive ping sent at {ping_data['timestamp']}")
                        else:
                            logger.error(f"❌ Client {client_id}: Failed to serialize ping data")
                    except Exception as e:
                        logger.warning(f"Client {client_id}: Failed to send keepalive ping: {e}")
                        break
            except asyncio.CancelledError:
                logger.info(f"Client {client_id}: Keepalive task cancelled")
                
        # Start keepalive as background task
        keepalive_task = asyncio.create_task(send_keepalive())
        
        try:
            # Handle incoming client messages
            while True:
                try:
                    # Wait for client messages with timeout
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    logger.info(f"📨 Client {client_id}: Received message: {data}")
                    
                    # Handle control messages
                    if data == 'ping':
                        logger.info(f"🏓 Client {client_id}: Received ping, sending pong")
                        pong_data = {'type': 'pong'}
                        logger.info(f"📦 Pong data: {safe_json_dumps(pong_data)}")
                        # Pre-serialize to avoid blocking event loop
                        pong_json, success = safe_json_dumps_compact(pong_data)
                        if success:
                            await websocket.send_text(pong_json)
                            logger.info(f"🏓 Client {client_id}: Sent pong response")
                        else:
                            logger.error(f"❌ Client {client_id}: Failed to serialize pong data")
                    elif data == 'pong':
                        logger.info(f"🏓 Client {client_id}: Received pong response")
                    elif data == 'refresh':
                        # Client can request fresh initial state
                        logger.info(f"🔄 Client {client_id}: Requested state refresh")
                        try:
                            refresh_state = await get_initial_state()
                            logger.info(f"🔄 Client {client_id}: Sending refresh state with {len(refresh_state.get('machines', []))} machines")
                            logger.info(f"📦 Refresh state data: {safe_json_dumps(refresh_state)}")
                            # Pre-serialize to avoid blocking event loop
                            refresh_json, success = safe_json_dumps_compact(refresh_state)
                            if not success:
                                logger.error(f"❌ Client {client_id}: Failed to serialize refresh state")
                                raise ValueError("Failed to serialize refresh state")
                            await websocket.send_text(refresh_json)
                            logger.info(f"✅ Client {client_id}: Sent refresh state")
                        except Exception as e:
                            logger.error(f"Client {client_id}: Failed to send refresh: {e}", exc_info=True)
                    else:
                        logger.info(f"❓ Client {client_id}: Unknown message type: {data}")
                        
                except asyncio.TimeoutError:
                    # No message from client in 5 seconds - this is normal, continue
                    logger.debug(f"Client {client_id}: No message in 5s (normal)")
                    continue
                    
        finally:
            # Cancel keepalive task on disconnect
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except asyncio.CancelledError:
        logger.info(f"Client {client_id} connection cancelled")
        raise
    except Exception as e:
        logger.error(f"Client {client_id}: WebSocket error: {e}", exc_info=True)
    finally:
        broadcaster.disconnect(websocket)
        logger.debug(f"Client {client_id} cleanup complete")

async def unix_socket_listener():
    """Listen for events from state machines via Unix socket"""
    socket_path = '/tmp/statemachine-events.sock'

    # Remove existing socket file
    if Path(socket_path).exists():
        Path(socket_path).unlink()

    # Create Unix socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(socket_path)
    sock.setblocking(False)

    logger.info(f"Listening on Unix socket: {socket_path}")

    loop = asyncio.get_event_loop()
    event_count = 0
    last_heartbeat = time.time()

    while True:
        try:
            # Heartbeat logging every 60 seconds to detect silent failures
            current_time = time.time()
            if current_time - last_heartbeat > 60:
                logger.info(f"Unix socket listener heartbeat: {event_count} events received, still listening")
                last_heartbeat = current_time
                perf_monitor.heartbeat()  # Update watchdog heartbeat
            
            # Non-blocking receive from DGRAM socket with timeout
            # Use sock_recvfrom for datagram sockets (returns data and address)
            # CRITICAL: Add timeout to prevent indefinite blocking
            try:
                recv_start = time.time()
                logger.debug(f"⏱️  Unix socket: Starting receive (timeout=0.1s)")
                
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 4096),
                    timeout=0.1  # 100ms timeout - shorter to prevent buffer buildup
                )
                
                recv_duration_ms = (time.time() - recv_start) * 1000
                logger.debug(f"🔌 Unix socket: Received {len(data)} bytes in {recv_duration_ms:.2f}ms from {addr}")
                perf_monitor.heartbeat()  # Update watchdog heartbeat
                
            except asyncio.TimeoutError:
                # No data available, yield to event loop before continuing
                logger.debug(f"⏱️  Unix socket: Timeout (no data), yielding to event loop")
                perf_monitor.heartbeat()  # Still alive, just no data
                await asyncio.sleep(0)  # Yield to other tasks
                continue
                
            if data:
                event_count += 1
                try:
                    # Parse JSON with timing
                    parse_start = time.time()
                    event = json.loads(data.decode('utf-8'))
                    parse_duration_ms = (time.time() - parse_start) * 1000
                    
                    event_type = event.get('event_type', event.get('type', 'unknown'))
                    machine_name = event.get('machine_name', 'unknown')
                    
                    logger.info(f"📥 Unix socket: Event #{event_count} ({event_type}) from {machine_name} - parsed in {parse_duration_ms:.2f}ms")
                    logger.info(f"📦 Full event data received: {safe_json_dumps(event)}")
                    
                    # Transform event_type → type for client compatibility
                    if 'event_type' in event:
                        event['type'] = event.pop('event_type')
                    
                    # Broadcast with timing
                    broadcast_start = time.time()
                    # Cache connection count to avoid potential blocking on set access
                    conn_count = len(broadcaster.connections)
                    logger.info(f"📡 Broadcasting event #{event_count} to {conn_count} clients")
                    logger.info(f"📦 Event data to broadcast: {safe_json_dumps(event)}")
                    
                    logger.info(f"⏱️  ABOUT TO CALL broadcaster.broadcast() at {time.time()}")
                    await broadcaster.broadcast(event)
                    logger.info(f"⏱️  RETURNED FROM broadcaster.broadcast() at {time.time()}")
                    
                    broadcast_duration_ms = (time.time() - broadcast_start) * 1000
                    logger.info(f"✅ Broadcast complete for event #{event_count} in {broadcast_duration_ms:.2f}ms")
                    
                    perf_monitor.heartbeat()  # Update after successful broadcast
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received (event #{event_count}): {e}, data: {data[:100]}")
                except Exception as e:
                    logger.error(f"Error broadcasting event #{event_count}: {e}", exc_info=True)
                    
        except BlockingIOError:
            # No data available, sleep briefly
            logger.debug("🚫 Unix socket: BlockingIOError, sleeping briefly")
            perf_monitor.heartbeat()
            await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            logger.warning("⚠️  Unix socket listener cancelled, shutting down")
            raise
        except OSError as e:
            logger.error(f"❌ Unix socket OS error: {e}, attempting to continue", exc_info=True)
            await asyncio.sleep(1)  # Back off on OS errors
        except Exception as e:
            logger.error(f"❌ Unexpected error in Unix socket listener: {e}", exc_info=True)
            await asyncio.sleep(0.1)  # Brief pause before continuing


async def server_heartbeat():
    """Background task that logs server health every 5 seconds"""
    heartbeat_count = 0
    while True:
        try:
            await asyncio.sleep(5)
            heartbeat_count += 1
            
            # Get task count
            tasks = asyncio.all_tasks()
            task_count = len(tasks)
            
            # Log comprehensive health
            time_since_last_event = time.time() - broadcaster.last_event_time
            logger.info(f"💓 Server heartbeat #{heartbeat_count} | "
                       f"connections={len(broadcaster.connections)} | "
                       f"tasks={task_count} | "
                       f"last_event={time_since_last_event:.1f}s ago")
            
            # Update watchdog
            perf_monitor.heartbeat()
            
            # Log active tasks in debug mode
            if task_count > 10:  # Warn if too many tasks
                logger.warning(f"⚠️  High task count: {task_count} active tasks")
                for task in list(tasks)[:5]:  # Log first 5
                    logger.debug(f"  Task: {task.get_name()} - {task._state}")
                    
        except asyncio.CancelledError:
            logger.info("Server heartbeat cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in server heartbeat: {e}", exc_info=True)



@app.on_event("startup")
async def startup():
    """Start background tasks"""
    logger.info("=" * 80)
    logger.info("🚀 WebSocket Server v1.0.26 Starting Up")
    logger.info("✅ ALL websocket.send_json() calls replaced with send_text()")
    logger.info("=" * 80)
    logger.info("Starting WebSocket server background tasks...")
    
    try:
        # Start background tasks with error tracking
        tasks = {
            'unix_socket_listener': asyncio.create_task(unix_socket_listener()),
            'server_heartbeat': asyncio.create_task(server_heartbeat())
        }
        
        # Store tasks for potential monitoring
        app.state.background_tasks = tasks
        
        logger.info(f"WebSocket server started on port 3002 with {len(tasks)} background tasks")
        logger.info("🐕 Watchdog thread monitoring for hangs (15s timeout)")
        
        # Log task status after brief delay
        await asyncio.sleep(0.5)
        for name, task in tasks.items():
            if task.done():
                logger.error(f"Background task '{name}' exited immediately!")
                try:
                    task.result()  # Will raise exception if task failed
                except Exception as e:
                    logger.error(f"Background task '{name}' error: {e}", exc_info=True)
            else:
                logger.info(f"✅ Background task '{name}' running successfully")
                
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    socket_path = '/tmp/statemachine-events.sock'
    if Path(socket_path).exists():
        Path(socket_path).unlink()

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_since_last_event = time.time() - broadcaster.last_event_time
    
    return {
        "status": "ok",
        "connections": len(broadcaster.connections),
        "last_event_time": broadcaster.last_event_time,
        "seconds_since_last_event": round(time_since_last_event, 2),
        "unix_socket_active": time_since_last_event < 10.0
    }

@app.get("/initial")
async def get_initial_endpoint():
    """HTTP endpoint to get initial state (for debugging)"""
    return await get_initial_state()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3002, log_level="info")