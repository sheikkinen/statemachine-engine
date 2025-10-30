#!/usr/bin/env python3
"""
UI Server CLI for statemachine-engine

Starts the web UI server with WebSocket monitoring for state machine visualization.
"""

import argparse
import os
import sys
import subprocess
import signal
import time
from pathlib import Path


def find_ui_server():
    """Find the UI server.cjs file in the package installation."""
    try:
        import statemachine_engine
        package_dir = Path(statemachine_engine.__file__).parent
        server_path = package_dir / "ui" / "server.cjs"
        if server_path.exists():
            return server_path
        else:
            print(f"❌ UI server not found at {server_path}")
            return None
    except ImportError:
        print("❌ statemachine_engine package not found")
        return None


def check_node():
    """Check if Node.js is available."""
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def start_websocket_server(event_socket_path=None, websocket_port=None):
    """Start the WebSocket server in background with custom parameters."""
    try:
        cmd = [sys.executable, '-m', 'statemachine_engine.monitoring.websocket_server']
        
        # Add custom parameters if provided
        if websocket_port:
            cmd.extend(['--port', str(websocket_port)])
        if event_socket_path:
            cmd.extend(['--event-socket-path', event_socket_path])
            
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give it time to start
        if process.poll() is None:  # Still running
            print("✓ WebSocket server started")
            if websocket_port:
                print(f"  WebSocket server on port: {websocket_port}")
            if event_socket_path:
                print(f"  Event socket path: {event_socket_path}")
            return process
        else:
            print("❌ WebSocket server failed to start")
            return None
    except Exception as e:
        print(f"❌ Failed to start WebSocket server: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Start the statemachine-engine web UI server"
    )
    parser.add_argument('--port', type=int, default=3001, 
                       help='Port for the web server (default: 3001)')
    parser.add_argument('--project-root', type=str, default=None,
                       help='Project root directory (default: current directory)')
    parser.add_argument('--no-websocket', action='store_true',
                       help='Skip starting the WebSocket server')
    parser.add_argument('--event-socket-path', type=str, default=None,
                       help='Custom event socket path for WebSocket server (default: /tmp/statemachine-events.sock)')
    parser.add_argument('--websocket-port', type=int, default=None,
                       help='Custom port for WebSocket server (default: 3002)')
    
    args = parser.parse_args()
    
    # Set project root
    project_root = args.project_root or os.getcwd()
    project_root = os.path.abspath(project_root)
    
    print(f"🚀 Starting statemachine-engine UI server...")
    print(f"📁 Project root: {project_root}")
    print(f"🌐 UI Port: {args.port}")
    if args.websocket_port:
        print(f"🔌 WebSocket Port: {args.websocket_port}")
    if args.event_socket_path:
        print(f"📡 Event Socket: {args.event_socket_path}")
    
    # Check requirements
    if not check_node():
        print("❌ Node.js is required but not found")
        print("   Please install Node.js from https://nodejs.org/")
        sys.exit(1)
    
    # Find UI server
    server_path = find_ui_server()
    if not server_path:
        sys.exit(1)
    
    # Start WebSocket server
    ws_process = None
    if not args.no_websocket:
        print("🌐 Starting WebSocket server...")
        ws_process = start_websocket_server(
            event_socket_path=args.event_socket_path,
            websocket_port=args.websocket_port
        )
    
    # Set environment variables
    env = os.environ.copy()
    env['PROJECT_ROOT'] = project_root
    env['PORT'] = str(args.port)
    
    # Change to UI directory and start server
    ui_dir = server_path.parent
    
    print(f"🖥️  Starting UI server from {ui_dir}...")
    
    # Cleanup function
    def cleanup(signum=None, frame=None):
        print("\n🛑 Shutting down...")
        if ws_process:
            ws_process.terminate()
            print("✓ WebSocket server stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Start the Node.js server
        subprocess.run(['node', 'server.cjs'], cwd=ui_dir, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ UI server failed with exit code {e.returncode}")
        cleanup()
    except KeyboardInterrupt:
        cleanup()


if __name__ == '__main__':
    main()