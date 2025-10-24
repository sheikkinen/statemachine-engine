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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    await broadcaster.connect(websocket)

    try:
        # Send initial state snapshot (with proper cleanup)
        initial_state = await get_initial_state()
        await websocket.send_json(initial_state)
        logger.info(f"Sent initial state with {len(initial_state.get('machines', []))} machines to new client")

        # Keep connection alive (receive pings from client)
        while True:
            data = await websocket.receive_text()

            # Handle control messages
            if data == 'ping':
                await websocket.send_json({'type': 'pong'})
            elif data == 'refresh':
                # Client can request fresh initial state
                logger.info("Client requested state refresh")
                refresh_state = await get_initial_state()
                await websocket.send_json(refresh_state)

    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        broadcaster.disconnect(websocket)

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

    while True:
        try:
            # Non-blocking receive from DGRAM socket
            # Use sock_recvfrom for datagram sockets (returns data and address)
            data, addr = await loop.sock_recvfrom(sock, 4096)
            if data:
                event = json.loads(data.decode('utf-8'))
                logger.info(f"Received event via Unix socket: {event.get('event_type', event.get('type'))} from {event.get('machine_name')}")
                
                # Transform event_type → type for client compatibility
                if 'event_type' in event:
                    event['type'] = event.pop('event_type')
                
                await broadcaster.broadcast(event)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except BlockingIOError:
            # No data available, sleep briefly
            await asyncio.sleep(0.001)
        except Exception as e:
            logger.error(f"Unix socket error: {e}")
            await asyncio.sleep(0.001)

async def database_fallback_poller():
    """Poll database for events if Unix socket goes quiet"""
    realtime_model = get_realtime_event_model()
    last_event_id = 0

    logger.info("Database fallback poller started")

    while True:
        await asyncio.sleep(0.5)  # Poll every 500ms

        # Check if Unix socket is active (received event in last 5 seconds)
        if time.time() - broadcaster.last_event_time < 5.0:
            continue  # Socket is working, skip DB poll

        # Unix socket seems dead, check database
        try:
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
            logger.error(f"Database fallback error: {e}")

async def cleanup_old_events():
    """Periodically clean up old consumed events from database"""
    realtime_model = get_realtime_event_model()

    while True:
        await asyncio.sleep(3600)  # Every hour

        try:
            realtime_model.cleanup_old_events(hours_old=24)
            logger.info("Cleaned up old realtime events")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

@app.on_event("startup")
async def startup():
    """Start background tasks"""
    asyncio.create_task(unix_socket_listener())
    asyncio.create_task(database_fallback_poller())
    asyncio.create_task(cleanup_old_events())
    logger.info("WebSocket server started on port 3002")

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