#!/usr/bin/env python3
"""
State Machine CLI - Main entry point for running the state machine
"""

import asyncio
import argparse
import logging
import json
import sys
from pathlib import Path

from statemachine_engine.core.engine import StateMachineEngine
from statemachine_engine.database.models import get_job_model

async def run_state_machine(config_path: str, debug: bool = False, machine_name: str = None, actions_dir: str = None, event_socket_path: str = None, control_socket_prefix: str = None, initial_context_json: str = '{}'):
    """Run the state machine with given configuration"""
    # Set up logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting state machine with config: {config_path}")
    
    # Parse initial context from JSON
    try:
        user_context = json.loads(initial_context_json)
        if user_context:
            logger.info(f"Initial context provided: {list(user_context.keys())}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in --initial-context: {e}")
        return 1
    
    # Validate and resolve actions directory if provided
    if actions_dir:
        actions_path = Path(actions_dir).expanduser().resolve()
        if not actions_path.exists():
            logger.error(f"Actions directory not found: {actions_path}")
            sys.exit(1)
        if not actions_path.is_dir():
            logger.error(f"Actions path is not a directory: {actions_path}")
            sys.exit(1)
        logger.info(f"Using custom actions directory: {actions_path}")
        actions_dir = str(actions_path)
    
    # Create and configure state machine
    engine = StateMachineEngine(machine_name=machine_name, actions_root=actions_dir, event_socket_path=event_socket_path, control_socket_prefix=control_socket_prefix)
    
    try:
        await engine.load_config(config_path)
        
        # Initialize context with job model and user-provided context
        initial_context = {
            'job_model': get_job_model(),
            **user_context  # Merge user context
        }
        
        await engine.execute_state_machine(initial_context)
    except KeyboardInterrupt:
        logger.info("State machine stopped by user")
    except Exception as e:
        logger.error(f"State machine error: {e}")
        return 1
    
    return 0

async def async_main():
    """Async main CLI entry point"""
    parser = argparse.ArgumentParser(description="State Machine Engine")
    parser.add_argument('config', help='Path to YAML configuration file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--machine-name', help='Override machine name (default: read from config)')
    parser.add_argument('--actions-dir', help='Custom actions directory (absolute or relative path)')
    parser.add_argument('--event-socket-path', help='Custom event socket path (default: /tmp/statemachine-events.sock)')
    parser.add_argument('--control-socket-prefix', help='Custom control socket prefix (default: /tmp/statemachine-control)')
    parser.add_argument('--initial-context', 
                        default='{}',
                        help='JSON string with initial context variables (default: {})')

    args = parser.parse_args()

    return await run_state_machine(
        args.config, 
        args.debug, 
        args.machine_name, 
        args.actions_dir, 
        args.event_socket_path, 
        args.control_socket_prefix,
        args.initial_context
    )

def main():
    """Synchronous entry point for setuptools"""
    sys.exit(asyncio.run(async_main()))

if __name__ == "__main__":
    main()
