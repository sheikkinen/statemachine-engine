"""
StateMachineEngine - YAML-driven finite state machine for event-based workflow processing

IMPORTANT: Changes via Change Management, see CLAUDE.md

The engine loads YAML configuration defining states, events, transitions, and actions, then executes 
an async event loop processing state transitions. Actions are executed for each state using either 
built-in handlers (log, sleep) or pluggable action classes loaded dynamically from src/actions/ via
the ActionLoader. The ActionLoader automatically discovers actions in nested directories (e.g., 
actions/ideator/) without requiring hardcoded imports. The system maintains execution context across 
state changes and supports error recovery via wildcard transitions.

KEY FILES:
- config/walking_skeleton.yaml, config/face_changer.yaml - YAML state machine definitions
- src/state_machine/action_loader.py - Dynamic action discovery and loading
- src/actions/bash_action.py - Shell command execution action
- src/actions/ideator/*.py - Prompt ideation action modules
- src/queue/persistent_queue.py - Persistent job queue integration

KEY FUNCTIONS:
- load_config(yaml_path) - Load and validate YAML state machine configuration
- execute_state_machine(context) - Run async event loop with state transitions
- process_event(event, context) - Handle event and trigger state transition
- _execute_action(action_config) - Execute action defined in YAML configuration
- _execute_pluggable_action(type, config) - Load and execute pluggable action class via ActionLoader
"""

import asyncio
import logging
import yaml
import socket
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class EventSocketManager:
    """Manages Unix socket connection for real-time event emission"""

    def __init__(self, socket_path: str = '/tmp/statemachine-events.sock'):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
        self.logger = logging.getLogger(__name__)
        self._connect()

    def _connect(self):
        """Attempt to connect to Unix socket (non-blocking)"""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            self.sock.connect(self.socket_path)
            self.logger.debug(f"Connected to event socket: {self.socket_path}")
        except Exception as e:
            self.logger.debug(f"Event socket not available: {e}")
            self.sock = None

    def emit(self, event_data: dict) -> bool:
        """
        Emit event to socket. Returns True if successful, False otherwise.
        Never blocks or raises exceptions.
        """
        if not self.sock:
            return False

        try:
            message = json.dumps(event_data).encode('utf-8')
            self.sock.send(message)
            return True
        except Exception as e:
            self.logger.debug(f"Failed to emit event: {e}")
            # Try reconnect on next emit
            self._connect()
            return False

class StateMachineEngine:
    """
    Core state machine engine that loads YAML configuration and executes
    state-based workflows with event processing
    
    """
    
    def __init__(self, machine_name: str = None, actions_root: str = None):
        self.config = None
        self.current_state = None
        self.context = {}
        self.actions = {}
        self.machine_name = machine_name
        self.actions_root = actions_root  # Custom actions directory
        self.event_socket = EventSocketManager()  # NEW: Unix socket for real-time events
        self.control_socket: Optional[socket.socket] = None  # Control socket for receiving events
        self.is_running = True
        self.propagation_count = 0  # Track frequency of job context propagation
        
    async def load_config(self, yaml_path: str) -> None:
        """Load state machine configuration from YAML file"""
        config_path = Path(yaml_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
            
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Set initial state
        self.current_state = self.config.get('initial_state', 'waiting')
        
        # Set machine name from config if not provided in constructor
        if not self.machine_name:
            self.machine_name = self.config.get('metadata', {}).get('machine_name', 'unknown')
        
        # Create control socket for receiving events
        self._create_control_socket()
        
        # Register actions
        await self._register_actions()
        
        logger.info(f"[{self.machine_name}] Loaded state machine config: {self.config.get('metadata', {}).get('name', 'Unknown')}")
        logger.info(f"[{self.machine_name}] Machine name: {self.machine_name}")
        logger.info(f"[{self.machine_name}] Initial state: {self.current_state}")
    
    async def _register_actions(self) -> None:
        """Register action handlers - uses ActionLoader dynamically"""
        # Actions are loaded dynamically via ActionLoader when needed
        pass
    
    def _create_control_socket(self) -> None:
        """Create Unix socket for receiving control events"""
        socket_path = f'/tmp/statemachine-control-{self.machine_name}.sock'
        
        try:
            # Remove stale socket file if it exists
            socket_path_obj = Path(socket_path)
            if socket_path_obj.exists():
                socket_path_obj.unlink()
                logger.debug(f"[{self.machine_name}] Removed stale socket: {socket_path}")
            
            # Create Unix DGRAM socket
            self.control_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.control_socket.bind(socket_path)
            self.control_socket.setblocking(False)
            
            logger.info(f"[{self.machine_name}] Control socket listening on: {socket_path}")
            
        except Exception as e:
            logger.error(f"[{self.machine_name}] Failed to create control socket: {e}")
            self.control_socket = None
    
    async def _check_control_socket(self) -> None:
        """Check for control events on Unix socket (non-blocking)"""
        if not self.control_socket:
            return
        
        try:
            # Non-blocking receive
            data, addr = self.control_socket.recvfrom(4096)
            if data:
                event = json.loads(data.decode('utf-8'))
                event_type = event.get('type', 'unknown')
                event_payload = event.get('payload', {})
                
                # Auto-parse JSON string payloads to dicts
                if isinstance(event_payload, str):
                    try:
                        event_payload = json.loads(event_payload)
                        event['payload'] = event_payload  # Update the event dict
                        logger.debug(
                            f"[{self.machine_name}] 📦 Parsed JSON payload: "
                            f"{len(event_payload)} fields"
                        )
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"[{self.machine_name}] ⚠️  Invalid JSON payload for {event_type}: {e}. "
                            f"Using empty dict. Raw: {str(event_payload)[:100]}..."
                        )
                        event_payload = {}
                        event['payload'] = {}
                
                # Log received message
                logger.info(f"[{self.machine_name}] 📥 Received event: {event_type}")
                logger.debug(f"[{self.machine_name}] 📥 Event payload: {event_payload}")
                
                # Emit to activity log for UI
                self._emit_realtime_event('activity_log', {
                    'message': f"📥 Received {event_type}",
                    'level': 'info',
                    'event_type': event_type,
                    'payload_keys': list(event_payload.keys()) if isinstance(event_payload, dict) else []
                })
                
                # Handle different event types
                # Store event data in context for actions to access
                self.context['event_data'] = event
                
                # Process the actual event type received
                await self.process_event(event_type)
                    
        except BlockingIOError:
            # No data available, this is expected
            pass
        except json.JSONDecodeError as e:
            logger.error(f"[{self.machine_name}] Invalid JSON in control event: {e}")
        except Exception as e:
            logger.debug(f"[{self.machine_name}] Control socket error: {e}")
    
    async def execute_state_machine(self, initial_context: Dict[str, Any] = None) -> None:
        """Execute the state machine with given initial context"""
        if not self.config:
            raise RuntimeError("No configuration loaded. Call load_config() first.")
            
        self.context = initial_context or {}
        
        # Add machine name to context for actions to use
        self.context['machine_name'] = self.machine_name
        
        # Register machine in database
        self._update_machine_state(self.current_state)
        
        logger.info(f"[{self.machine_name}] Starting state machine execution from state: {self.current_state}")
        
        # Start with initial event
        await self.process_event("start", self.context)
        
        # Main event loop
        while self.is_running:
            # Check control socket for incoming events
            await self._check_control_socket()
            
            # Check if we've reached a terminal state
            if self.current_state == "stopped":
                logger.info(f"[{self.machine_name}] State machine reached terminal state: {self.current_state}")
                break
                
            # Execute actions for current state
            await self._execute_state_actions()
            
            # Adaptive sleep: longer when idle, shorter when active
            # Idle = in waiting state with no recent activity
            is_idle = (
                self.current_state == "waiting" and
                not hasattr(self, '_last_activity_time') or
                (hasattr(self, '_last_activity_time') and time.time() - self._last_activity_time > 5.0)
            )
            
            if is_idle:
                await asyncio.sleep(0.5)  # 500ms when idle (reduces CPU usage)
            else:
                await asyncio.sleep(0.05)  # 50ms when active (responsive)
        
        # Cleanup on exit
        self._cleanup_sockets()
    
    async def process_event(self, event: str, context: Dict[str, Any] = None) -> bool:
        """Process an event and potentially transition to a new state"""
        if context:
            self.context.update(context)
        
        # Only log event processing for non-routine events (suppress cleanup_done, no_events)
        routine_events = ['cleanup_done', 'no_events', 'no_jobs']
        if event not in routine_events:
            logger.debug(f"[{self.machine_name}] Processing event '{event}' in state '{self.current_state}'")
        
        # Find valid transition
        new_state = await self._find_transition(self.current_state, event)
        if new_state:            
            # Only log state transitions for important events, skip idle cycles and self-loops
            is_self_loop = (self.current_state == new_state)
            is_idle_event = event in ['wake_up', 'no_events', 'no_jobs']
            
            # Track transition count for rate limiting repetitive transitions
            if not hasattr(self, '_transition_count'):
                self._transition_count = {}
            
            transition_key = f"{self.current_state}--{event}-->{new_state}"
            if transition_key not in self._transition_count:
                self._transition_count[transition_key] = 0
            self._transition_count[transition_key] += 1
            
            # Determine log level: DEBUG for idle self-loops, INFO for interesting transitions
            log_at_debug = is_self_loop and is_idle_event
            
            # For DEBUG logging, only log first and every 100th occurrence to reduce spam
            should_log_debug = (
                self._transition_count[transition_key] == 1 or
                self._transition_count[transition_key] % 100 == 0
            )
            
            # For INFO logging, log first, state changes, important events, or every 10th
            should_log_info = (
                self._transition_count[transition_key] == 1 or  # First occurrence
                not is_idle_event or  # Important events
                not is_self_loop or  # State changes
                self._transition_count[transition_key] % 10 == 0  # Every 10th repetition
            )
            
            should_log = should_log_debug if log_at_debug else should_log_info
            
            if should_log:
                # Get actions for the new state to show what will be executed
                next_actions = self.config.get('actions', {}).get(new_state, [])
                action_descriptions = []
                for action in next_actions:
                    action_type = action.get('type', 'unknown')
                    if action_type == 'bash':
                        desc = action.get('description', action.get('command', 'bash'))[:30]
                    elif action_type == 'sleep':
                        duration = action.get('duration', 1)
                        desc = f'sleep {duration}s'
                    elif action_type == 'log':
                        desc = 'log'
                    else:
                        desc = action_type
                    action_descriptions.append(desc)
                
                actions_text = " / ".join(action_descriptions) if action_descriptions else "no actions"
                count_suffix = f" (#{self._transition_count[transition_key]})" if self._transition_count[transition_key] > 1 else ""
                
                # Use appropriate log level
                log_message = f"[{self.machine_name}] {self.current_state} --{event}--> {new_state}: {actions_text}{count_suffix}"
                if log_at_debug:
                    logger.debug(log_message)
                else:
                    logger.info(log_message)
            
            # Store previous state for event emission
            previous_state = self.current_state
            self.current_state = new_state
            
            # Mark activity time for non-idle events and state changes
            if not is_idle_event or not is_self_loop:
                self._last_activity_time = time.time()
            
            # Log state change for UI consumption and emit real-time event
            # Skip self-loop idle transitions to reduce UI spam
            should_emit_to_ui = not (is_self_loop and is_idle_event)
            await self._log_state_change(previous_state, new_state, event, emit_to_ui=should_emit_to_ui)
            
            return True
        else:
            # Only log missing transitions for non-idle events
            if event not in ['cleanup_done']:
                logger.debug(f"[{self.machine_name}] No transition found for event '{event}' in state '{self.current_state}'")
            return False
    
    async def _log_state_change(self, from_state: str, to_state: str, event_trigger: str, emit_to_ui: bool = True):
        """Log current state to database for UI consumption and emit real-time event"""
        
        # Emit real-time event via Unix socket (skip idle self-loops to reduce UI spam)
        if emit_to_ui:
            self._emit_realtime_event('state_change', {
                'from_state': from_state,
                'to_state': to_state,
                'event_trigger': event_trigger,
                'timestamp': time.time()
            })
        
        # Update machine_state table for UI monitoring
        self._update_machine_state(to_state)
    
    def _update_machine_state(self, current_state: str):
        """Update machine_state table for UI monitoring"""
        job_model = self.context.get('job_model')
        if job_model and hasattr(job_model, 'db') and self.machine_name:
            try:
                import os
                with job_model.db._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO machine_state (machine_name, current_state, last_activity, pid, metadata)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(machine_name) DO UPDATE SET
                            current_state = excluded.current_state,
                            last_activity = excluded.last_activity,
                            pid = excluded.pid
                    """, (self.machine_name, current_state, time.time(), os.getpid(), None))
                    conn.commit()
            except Exception as e:
                logger.debug(f"[{self.machine_name}] Failed to update machine_state: {e}")
    
    def _emit_realtime_event(self, event_type: str, payload: dict):
        """Emit event via Unix socket with database fallback"""
        event_data = {
            'machine_name': self.machine_name,
            'event_type': event_type,
            'payload': payload
        }

        # Try fast path (Unix socket)
        if self.event_socket.emit(event_data):
            return

        # Fallback: Write to database
        job_model = self.context.get('job_model')
        if job_model and hasattr(job_model, 'db'):
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from database.models import get_realtime_event_model
                realtime_model = get_realtime_event_model()
                realtime_model.log_event(self.machine_name, event_type, payload)
            except Exception as e:
                logger.warning(f"[{self.machine_name}] Failed to log realtime event to database: {e}")
    
    def emit_job_started(self, job_id: str, job_type: str = None):
        """Emit job_started event"""
        self._emit_realtime_event('job_started', {
            'job_id': job_id,
            'job_type': job_type,
            'timestamp': time.time()
        })
    
    def emit_job_completed(self, job_id: str, job_type: str = None):
        """Emit job_completed event"""
        self._emit_realtime_event('job_completed', {
            'job_id': job_id,
            'job_type': job_type,
            'timestamp': time.time()
        })
    
    def emit_error(self, error_message: str, job_id: str = None):
        """Emit error event"""
        self._emit_realtime_event('error', {
            'error_message': error_message,
            'job_id': job_id,
            'timestamp': time.time()
        })
    
    async def _find_transition(self, current_state: str, event: str) -> Optional[str]:
        """Find valid transition for current state and event"""
        transitions = self.config.get('transitions', [])
        
        for transition in transitions:
            from_state = transition.get('from')
            to_state = transition.get('to')
            on_event = transition.get('event')
            
            # Check if transition matches (support wildcard '*' for from state)
            if (from_state == current_state or from_state == '*') and on_event == event:
                return to_state
                
        return None
    
    def _propagate_job_context(self) -> None:
        """Propagate job data from current_job to main context for variable substitution"""
        current_job = self.context.get('current_job')
        if current_job and isinstance(current_job, dict):
            # First propagate database fields from job itself (id, source_job_id, etc.)
            db_fields = ['id', 'source_job_id', 'job_id', 'job_type']
            for field in db_fields:
                if field in current_job and current_job[field] is not None:
                    self.context[field] = current_job[field]

            # Then propagate job data fields
            job_data = current_job.get('data', {})
            if job_data:
                # Propagate job data fields to main context for template substitution
                for key, value in job_data.items():
                    if value is not None:  # Only propagate non-None values
                        self.context[key] = value

                # Track propagation frequency to reduce log spam
                self.propagation_count += 1
                if self.propagation_count == 1:
                    logger.info(f"[{self.machine_name}] Job context propagation started: {list(job_data.keys())}")
                elif self.propagation_count % 100 == 0:
                    logger.warning(f"[{self.machine_name}] Job context propagated {self.propagation_count} times: {list(job_data.keys())}")
    
    async def _execute_state_actions(self) -> None:
        """Execute actions defined for current state"""
        # Add current_state to context for template substitution
        self.context['current_state'] = self.current_state
        
        state_actions = self.config.get('actions', {}).get(self.current_state, [])
        
        for action_config in state_actions:
            await self._execute_action(action_config)
            
            # After each action, check if current_job was added to context and propagate job data
            self._propagate_job_context()
    
    def _substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Substitute {variable} placeholders with context values.
        
        Supports:
        - Simple variables: {job_id}, {id}, {status}
        - Nested keys with dot notation: {event_data.payload.job_id}
        - Leaves unknown placeholders unchanged
        """
        import re
        
        if not isinstance(template, str):
            return template
            
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_.]*)\}'
        
        def replace_match(match):
            key = match.group(1)
            
            # Handle nested keys (e.g., event_data.payload.job_id)
            if '.' in key:
                parts = key.split('.')
                obj = context
                for part in parts:
                    if isinstance(obj, dict):
                        obj = obj.get(part)
                        if obj is None:
                            return match.group(0)  # Keep placeholder if path not found
                    else:
                        return match.group(0)  # Keep placeholder if not dict
                return str(obj) if obj is not None else match.group(0)
            
            # Handle simple keys
            value = context.get(key)
            if value is not None:
                return str(value)
            
            return match.group(0)  # Keep placeholder if not found
        
        return re.sub(pattern, replace_match, template)
    
    def _interpolate_config(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively interpolate variables in action config.
        
        Processes all string values in the config dict, replacing {variable}
        placeholders with values from context. This happens at engine level
        before actions receive their config, ensuring consistent variable
        substitution across all actions.
        """
        interpolated = {}
        
        for key, value in config.items():
            if isinstance(value, str):
                # Substitute variables in string values
                interpolated[key] = self._substitute_variables(value, context)
            elif isinstance(value, dict):
                # Recursively process nested dicts
                interpolated[key] = self._interpolate_config(value, context)
            elif isinstance(value, list):
                # Process each list item
                interpolated[key] = [
                    self._substitute_variables(item, context) if isinstance(item, str)
                    else self._interpolate_config(item, context) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                # Pass through other types unchanged
                interpolated[key] = value
        
        return interpolated
    
    async def _execute_action(self, action_config: Dict[str, Any]) -> None:
        """Execute a single action"""
        # Interpolate variables BEFORE processing action
        # This ensures all {variable} placeholders are resolved at engine level
        interpolated_config = self._interpolate_config(action_config, self.context)
        
        action_type = interpolated_config.get('type')
        
        if not action_type:
            logger.error(f"[{self.machine_name}] Action missing 'type' field: {action_config}")
            return
            
        # For now, implement basic actions directly
        # Later this will delegate to action registry
        if action_type == 'log':
            message = interpolated_config.get('message', 'No message')
            level = interpolated_config.get('level', 'info')  # Default to info
            # Rate limit repetitive log messages - only log first occurrence and every 10th
            if not hasattr(self, '_log_count'):
                self._log_count = {}
            
            if message not in self._log_count:
                self._log_count[message] = 0
            self._log_count[message] += 1
            
            if self._log_count[message] == 1 or self._log_count[message] % 10 == 0:
                count_suffix = f" (#{self._log_count[message]})" if self._log_count[message] > 1 else ""
                log_func = getattr(logger, level, logger.info)
                log_func(f"[{self.machine_name}] Action log: {message}{count_suffix}")
            
        elif action_type == 'sleep':
            duration = interpolated_config.get('duration', 1)
            # Reduce verbosity for idle cycles - only log on first sleep, long sleeps, or every 10th occurrence
            if not hasattr(self, '_sleep_count'):
                self._sleep_count = 0
            self._sleep_count += 1
            
            if duration > 10 or self._sleep_count == 1 or self._sleep_count % 10 == 0:
                logger.info(f"[{self.machine_name}] 💤 Sleeping for {duration} seconds (cycle {self._sleep_count})")
            await asyncio.sleep(duration)
            # Generate wake_up event after sleeping
            await self.process_event('wake_up')
            
            
        else:
            # Try to execute as pluggable action (pass interpolated config)
            await self._execute_pluggable_action(action_type, interpolated_config)
    
    
    async def _execute_pluggable_action(self, action_type: str, action_config: Dict[str, Any]) -> None:
        """Execute pluggable action from actions module using ActionLoader"""
        try:
            # Import ActionLoader
            from .action_loader import ActionLoader
            
            # Add queue to context for actions to use
            if hasattr(self, '_queue'):
                self.context['queue'] = self._queue
            
            # Add global config to context so actions can access configuration parameters
            self.context['config'] = self.config
            
            # Load action class dynamically using ActionLoader with custom actions_root if provided
            loader = ActionLoader(actions_root=self.actions_root)
            action_class = loader.load_action_class(action_type)
            
            if action_class is None:
                error_msg = f"Could not load action '{action_type}' - not found in actions directory"
                logger.error(f"[{self.machine_name}] {error_msg}")
                self.context['last_error'] = error_msg
                self.context['last_error_action'] = action_type
                self.emit_error(error_msg)  # Log to realtime_events
                await self.process_event('error')
                return
            
            try:
                # Create and execute action instance
                action = action_class(action_config)
                event = await action.execute(self.context)
                
                # Process the returned event (if any)
                if event:
                    await self.process_event(event)
                    
            except Exception as e:
                error_msg = f"Error executing action {action_type}: {e}"
                logger.error(f"[{self.machine_name}] {error_msg}")
                self.context['last_error'] = error_msg
                self.context['last_error_action'] = action_type
                self.emit_error(error_msg, job_id=self.context.get('current_job', {}).get('job_id'))  # Log to realtime_events
                await self.process_event('error')

        except Exception as e:
            error_msg = f"Error loading pluggable action {action_type}: {e}"
            logger.error(f"[{self.machine_name}] {error_msg}")
            self.context['last_error'] = error_msg
            self.context['last_error_action'] = action_type
            self.emit_error(error_msg, job_id=self.context.get('current_job', {}).get('job_id'))  # Log to realtime_events
            await self.process_event('error')
    
    def _cleanup_sockets(self) -> None:
        """Clean up Unix sockets on shutdown"""
        if self.control_socket:
            try:
                socket_path = f'/tmp/statemachine-control-{self.machine_name}.sock'
                self.control_socket.close()
                
                # Remove socket file
                socket_path_obj = Path(socket_path)
                if socket_path_obj.exists():
                    socket_path_obj.unlink()
                    logger.info(f"[{self.machine_name}] Cleaned up control socket")
            except Exception as e:
                logger.warning(f"[{self.machine_name}] Error cleaning up control socket: {e}")
