"""
WebSocket server for real-time state machine event streaming

Listens on:
- Unix socket: /tmp/statemachine-events.sock (from state machines)
- WebSocket: ws://localhost:3002/ws/events (to browsers)

Fallback: Polls database every 500ms for events if socket messages stop
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

    async def broadcast(self, event: dict):
        """Send event to all connected clients"""
        self.last_event_time = time.time()

        # Remove disconnected clients
        dead_connections = set()
        for ws in self.connections:
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                dead_connections.add(ws)

        self.connections -= dead_connections

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
            initial_state = await get_initial_state()
            await websocket.send_json(initial_state)
            logger.info(f"Client {client_id}: Sent initial state with {len(initial_state.get('machines', []))} machines")
        except Exception as e:
            logger.error(f"Client {client_id}: Failed to send initial state: {e}", exc_info=True)

        # Keep connection alive (receive pings from client)
        while True:
            try:
                data = await websocket.receive_text()

                # Handle control messages
                if data == 'ping':
                    await websocket.send_json({'type': 'pong'})
                elif data == 'refresh':
                    # Client can request fresh initial state
                    logger.info(f"Client {client_id} requested state refresh")
                    try:
                        refresh_state = await get_initial_state()
                        await websocket.send_json(refresh_state)
                    except Exception as e:
                        logger.error(f"Client {client_id}: Failed to send refresh: {e}", exc_info=True)
                else:
                    logger.debug(f"Client {client_id}: Unknown message: {data[:50]}")
                    
            except asyncio.TimeoutError:
                logger.warning(f"Client {client_id}: Receive timeout")
                continue

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
            
            # Non-blocking receive from DGRAM socket with timeout
            # Use sock_recvfrom for datagram sockets (returns data and address)
            # CRITICAL: Add timeout to prevent indefinite blocking
            try:
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 4096),
                    timeout=1.0  # 1 second timeout allows heartbeats to work
                )
            except asyncio.TimeoutError:
                # No data received, continue to heartbeat check
                logger.debug("Unix socket receive timeout (no data), continuing to heartbeat check")
                continue
            if data:
                event_count += 1
                try:
                    event = json.loads(data.decode('utf-8'))
                    logger.info(f"Received event via Unix socket: {event.get('event_type', event.get('type'))} from {event.get('machine_name')}")
                    
                    # Transform event_type → type for client compatibility
                    if 'event_type' in event:
                        event['type'] = event.pop('event_type')
                    
                    await broadcaster.broadcast(event)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received (event #{event_count}): {e}, data: {data[:100]}")
                except Exception as e:
                    logger.error(f"Error broadcasting event #{event_count}: {e}", exc_info=True)
                    
        except BlockingIOError:
            # No data available, sleep briefly
            await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            logger.warning("Unix socket listener cancelled, shutting down")
            raise
        except OSError as e:
            logger.error(f"Unix socket OS error: {e}, attempting to continue", exc_info=True)
            await asyncio.sleep(1)  # Back off on OS errors
        except Exception as e:
            logger.error(f"Unexpected error in Unix socket listener: {e}", exc_info=True)
            await asyncio.sleep(0.1)  # Brief pause before continuing

async def database_fallback_poller():
    """Poll database for events if Unix socket goes quiet"""
    last_event_id = 0
    poll_count = 0
    last_heartbeat = time.time()

    logger.info("Database fallback poller started")

    while True:
        try:
            await asyncio.sleep(0.5)  # Poll every 500ms
            poll_count += 1

            # Heartbeat logging every 5 minutes
            current_time = time.time()
            if current_time - last_heartbeat > 300:
                time_since_event = current_time - broadcaster.last_event_time
                logger.info(f"Database fallback poller heartbeat: poll #{poll_count}, "
                          f"last event {time_since_event:.1f}s ago")
                last_heartbeat = current_time

            # Check if Unix socket is active (received event in last 5 seconds)
            if time.time() - broadcaster.last_event_time < 5.0:
                continue  # Socket is working, skip DB poll

            # Unix socket seems dead, check database
            # Create fresh model instance for each poll to avoid connection leaks
            try:
                realtime_model = get_realtime_event_model()
                events = realtime_model.get_unconsumed_events(since_id=last_event_id, limit=50)

                for event in events:
                    event_dict = {
                        'machine_name': event['machine_name'],
                        'type': event['event_type'],  # Use 'type' for client compatibility
                        'payload': event['payload'],
                        'timestamp': event['created_at']
                    }

                    await broadcaster.broadcast(event_dict)
                    last_event_id = event['id']

                if events:
                    # Mark events as consumed
                    event_ids = [event['id'] for event in events]
                    realtime_model.mark_events_consumed(event_ids)
                    logger.info(f"Processed {len(events)} events from database fallback")

            except Exception as e:
                logger.error(f"Database fallback poll error: {e}", exc_info=True)
                
        except asyncio.CancelledError:
            logger.warning("Database fallback poller cancelled, shutting down")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in database fallback poller: {e}", exc_info=True)
            await asyncio.sleep(1)  # Back off on errors

async def cleanup_old_events():
    """Periodically clean up old consumed events from database"""
    cleanup_count = 0
    
    while True:
        try:
            await asyncio.sleep(3600)  # Every hour
            cleanup_count += 1

            # Create fresh model instance for each cleanup to avoid connection leaks
            try:
                logger.info(f"Starting cleanup #{cleanup_count} of old realtime events")
                realtime_model = get_realtime_event_model()
                deleted = realtime_model.cleanup_old_events(hours_old=24)
                logger.info(f"Cleanup #{cleanup_count} complete: removed {deleted if deleted != -1 else 'unknown'} old events")
            except Exception as e:
                logger.error(f"Cleanup #{cleanup_count} error: {e}", exc_info=True)
                
        except asyncio.CancelledError:
            logger.warning("Cleanup task cancelled, shutting down")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in cleanup task: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait before retry

@app.on_event("startup")
async def startup():
    """Start background tasks"""
    logger.info("Starting WebSocket server background tasks...")
    
    try:
        # Start background tasks with error tracking
        tasks = {
            'unix_socket_listener': asyncio.create_task(unix_socket_listener()),
            'database_fallback_poller': asyncio.create_task(database_fallback_poller()),
            'cleanup_old_events': asyncio.create_task(cleanup_old_events())
        }
        
        # Store tasks for potential monitoring
        app.state.background_tasks = tasks
        
        logger.info(f"WebSocket server started on port 3002 with {len(tasks)} background tasks")
        
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
                logger.info(f"Background task '{name}' running successfully")
                
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