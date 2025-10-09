#!/usr/bin/env python3
"""Event Monitor Tool

Connects to WebSocket server and displays state machine events in real-time.

USAGE:
    statemachine-events
    statemachine-events --machine simple_worker
    statemachine-events --format json > events.log
    statemachine-events --duration 60
"""

import asyncio
import websockets
import json
import sys
import signal
import time
import argparse
from datetime import datetime
from typing import Optional


class EventMonitor:
    """Monitor state machine events via WebSocket"""
    
    def __init__(self, 
                 filter_machine: Optional[str] = None,
                 output_format: str = 'human',
                 duration: Optional[float] = None,
                 host: str = 'localhost',
                 port: int = 3002):
        self.filter_machine = filter_machine
        self.output_format = output_format
        self.duration = duration
        self.host = host
        self.port = port
        self.running = True
        self.event_count = 0
        self.start_time = None
        
    def format_event_human(self, event: dict) -> str:
        """Format event for human-readable output"""
        machine = event.get('machine_name', 'unknown')
        event_type = event.get('type', 'unknown')
        payload = event.get('payload', {})
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Format based on event type
        if event_type == 'state_change':
            from_state = payload.get('from_state', '?')
            to_state = payload.get('to_state', '?')
            trigger = payload.get('event_trigger', '?')
            return f"[{timestamp}] 🔄 {machine}: {from_state} --{trigger}--> {to_state}"
        elif event_type == 'job_started':
            job_id = payload.get('job_id', '?')
            return f"[{timestamp}] ▶️  {machine}: Started job {job_id}"
        elif event_type == 'job_completed':
            job_id = payload.get('job_id', '?')
            return f"[{timestamp}] ✅ {machine}: Completed job {job_id}"
        elif event_type == 'error':
            error_msg = payload.get('error_message', '?')
            return f"[{timestamp}] ❌ {machine}: {error_msg}"
        elif event_type == 'activity_log':
            message = payload.get('message', '?')
            return f"[{timestamp}] 📝 {machine}: {message}"
        else:
            return f"[{timestamp}] 📡 {machine}: {event_type}"
    
    def format_event_json(self, event: dict) -> str:
        """Format event as JSON (one line per event)"""
        return json.dumps(event)
    
    def format_event_compact(self, event: dict) -> str:
        """Format event in compact form"""
        machine = event.get('machine_name', 'unknown')
        event_type = event.get('type', 'unknown')
        payload = event.get('payload', {})
        
        if event_type == 'state_change':
            to_state = payload.get('to_state', '?')
            return f"{machine} → {to_state}"
        elif event_type == 'job_started':
            job_id = payload.get('job_id', '?')
            return f"{machine} ▶️ {job_id}"
        elif event_type == 'job_completed':
            job_id = payload.get('job_id', '?')
            return f"{machine} ✅ {job_id}"
        else:
            return f"{machine} • {event_type}"
    
    def print_event(self, event: dict):
        """Print event in selected format"""
        # Filter by machine name if specified
        if self.filter_machine:
            machine_name = event.get('machine_name', '')
            if machine_name != self.filter_machine:
                return
        
        # Format and print
        if self.output_format == 'json':
            output = self.format_event_json(event)
        elif self.output_format == 'compact':
            output = self.format_event_compact(event)
        else:  # human
            output = self.format_event_human(event)
        
        print(output, flush=True)
        self.event_count += 1
    
    def check_duration(self) -> bool:
        """Check if duration limit reached"""
        if self.duration is None:
            return False
        
        elapsed = time.time() - self.start_time
        return elapsed >= self.duration
    
    async def run(self):
        """Connect to WebSocket server and monitor events"""
        self.start_time = time.time()
        
        # Print startup message (except in JSON mode)
        if self.output_format != 'json':
            ws_url = f'ws://{self.host}:{self.port}/ws'
            print(f"🔌 Connecting to {ws_url}...", file=sys.stderr)
            if self.filter_machine:
                print(f"🔍 Filtering events for machine: {self.filter_machine}", file=sys.stderr)
            if self.duration:
                print(f"⏱️  Monitoring for {self.duration} seconds", file=sys.stderr)
            print("", file=sys.stderr)
        
        try:
            async with websockets.connect(f'ws://{self.host}:{self.port}/ws/events') as websocket:
                if self.output_format != 'json':
                    print(f"✅ Connected! Monitoring events...", file=sys.stderr)
                    print("", file=sys.stderr)
                
                while self.running:
                    # Check duration limit
                    if self.check_duration():
                        break
                    
                    try:
                        # Receive event from WebSocket
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        event = json.loads(message)
                        self.print_event(event)
                        
                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError as e:
                        if self.output_format != 'json':
                            print(f"⚠️  Invalid JSON: {e}", file=sys.stderr)
                        continue
                    
        except ConnectionRefusedError:
            print(f"❌ Could not connect to WebSocket server at {self.host}:{self.port}", file=sys.stderr)
            print(f"   Is the WebSocket server running?", file=sys.stderr)
            print(f"   Start it with: python -m statemachine_engine.monitoring.websocket_server", file=sys.stderr)
            sys.exit(1)
        except websockets.exceptions.WebSocketException as e:
            print(f"❌ WebSocket error: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            pass
        finally:
            # Print summary (except in JSON mode)
            if self.output_format != 'json':
                print("", file=sys.stderr)
                print(f"📊 Total events monitored: {self.event_count}", file=sys.stderr)
                
                if self.duration:
                    elapsed = time.time() - self.start_time
                    print(f"⏱️  Duration: {elapsed:.1f}s", file=sys.stderr)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Monitor state machine events in real-time',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  statemachine-events                       Monitor all events
  statemachine-events --machine worker1     Filter by machine name
  statemachine-events --format json         JSON output (one per line)
  statemachine-events --format compact      Compact terse output
  statemachine-events --duration 30         Monitor for 30 seconds
  statemachine-events --host 192.168.1.10   Connect to remote server
        """
    )
    
    parser.add_argument(
        '--machine',
        help='Filter events by machine name'
    )
    
    parser.add_argument(
        '--format',
        choices=['human', 'json', 'compact'],
        default='human',
        help='Output format (default: human)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        help='Monitor for N seconds then exit'
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='WebSocket server host (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=3002,
        help='WebSocket server port (default: 3002)'
    )
    
    args = parser.parse_args()
    
    # Create and run monitor
    monitor = EventMonitor(
        filter_machine=args.machine,
        output_format=args.format,
        duration=args.duration,
        host=args.host,
        port=args.port
    )
    
    # Run async event loop
    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
