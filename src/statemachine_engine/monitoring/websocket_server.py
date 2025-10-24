"""
WebSocket server for real-time state machine event streaming

Listens on:
- Unix socket: /tmp/statemachine-events.sock (from state machines)
- WebSocket: ws://localhost:3002/ws/events (to browsers)
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
                logger.info(f"📤 Broadcasting to client {id(ws)}: {event.get('type', 'unknown')} event")
                logger.info(f"📦 Event content for client {id(ws)}: {json.dumps(event, indent=2)}")
                # CRITICAL: Add timeout to prevent blocking on slow clients
                await asyncio.wait_for(ws.send_json(event), timeout=2.0)
                logger.info(f"✅ Sent to client {id(ws)}")
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
            logger.info(f"📦 Initial state data: {json.dumps(initial_state, indent=2)}")
            await websocket.send_json(initial_state)
            logger.info(f"✅ Client {client_id}: Initial state sent successfully")
        except Exception as e:
            logger.error(f"❌ Client {client_id}: Failed to send initial state: {e}", exc_info=True)

        # Keep connection alive with periodic pings - run as background task
        async def send_keepalive():
            """Send periodic pings to keep WebSocket connection alive"""
            ping_interval = 20  # Send ping every 20 seconds
            try:
                while True:
                    await asyncio.sleep(ping_interval)
                    try:
                        ping_data = {'type': 'ping', 'timestamp': time.time()}
                        logger.info(f"🏓 Client {client_id}: Sending keepalive ping")
                        logger.info(f"📦 Ping data: {json.dumps(ping_data)}")
                        await websocket.send_json(ping_data)
                        logger.info(f"✅ Client {client_id}: Keepalive ping sent at {ping_data['timestamp']}")
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
                        logger.info(f"📦 Pong data: {json.dumps(pong_data)}")
                        await websocket.send_json(pong_data)
                        logger.info(f"🏓 Client {client_id}: Sent pong response")
                    elif data == 'pong':
                        logger.info(f"🏓 Client {client_id}: Received pong response")
                    elif data == 'refresh':
                        # Client can request fresh initial state
                        logger.info(f"🔄 Client {client_id}: Requested state refresh")
                        try:
                            refresh_state = await get_initial_state()
                            logger.info(f"🔄 Client {client_id}: Sending refresh state with {len(refresh_state.get('machines', []))} machines")
                            logger.info(f"📦 Refresh state data: {json.dumps(refresh_state, indent=2)}")
                            await websocket.send_json(refresh_state)
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
            
            # Non-blocking receive from DGRAM socket with timeout
            # Use sock_recvfrom for datagram sockets (returns data and address)
            # CRITICAL: Add timeout to prevent indefinite blocking
            try:
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(sock, 4096),
                    timeout=0.1  # 100ms timeout - shorter to prevent buffer buildup
                )
                logger.debug(f"🔌 Unix socket: Received {len(data)} bytes from {addr}")
            except asyncio.TimeoutError:
                # No data available, yield to event loop before continuing
                logger.debug(f"⏱️  Unix socket: Timeout (no data), yielding to event loop")
                await asyncio.sleep(0)  # Yield to other tasks
                continue
            if data:
                event_count += 1
                try:
                    event = json.loads(data.decode('utf-8'))
                    event_type = event.get('event_type', event.get('type', 'unknown'))
                    machine_name = event.get('machine_name', 'unknown')
                    logger.info(f"📥 Unix socket: Received event #{event_count}: {event_type} from {machine_name}")
                    logger.info(f"📦 Full event data received: {json.dumps(event, indent=2)}")
                    
                    # Transform event_type → type for client compatibility
                    if 'event_type' in event:
                        event['type'] = event.pop('event_type')
                    
                    logger.info(f"📡 Broadcasting event #{event_count} to {len(broadcaster.connections)} clients")
                    logger.info(f"📦 Event data to broadcast: {json.dumps(event, indent=2)}")
                    await broadcaster.broadcast(event)
                    logger.info(f"✅ Broadcast complete for event #{event_count}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received (event #{event_count}): {e}, data: {data[:100]}")
                except Exception as e:
                    logger.error(f"Error broadcasting event #{event_count}: {e}", exc_info=True)
                    
        except BlockingIOError:
            # No data available, sleep briefly
            logger.debug("🚫 Unix socket: BlockingIOError, sleeping briefly")
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



@app.on_event("startup")
async def startup():
    """Start background tasks"""
    logger.info("Starting WebSocket server background tasks...")
    
    try:
        # Start background tasks with error tracking
        tasks = {
            'unix_socket_listener': asyncio.create_task(unix_socket_listener())
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