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
    """Find the UI server.js file in the package installation."""
    try:
        import statemachine_engine
        package_dir = Path(statemachine_engine.__file__).parent
        server_path = package_dir / "ui" / "server.js"
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


def start_websocket_server():
    """Start the WebSocket server in background."""
    try:
        process = subprocess.Popen([
            sys.executable, '-m', 'statemachine_engine.monitoring.websocket_server'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give it time to start
        if process.poll() is None:  # Still running
            print("✓ WebSocket server started")
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
    
    args = parser.parse_args()
    
    # Set project root
    project_root = args.project_root or os.getcwd()
    project_root = os.path.abspath(project_root)
    
    print(f"🚀 Starting statemachine-engine UI server...")
    print(f"📁 Project root: {project_root}")
    print(f"🌐 Port: {args.port}")
    
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
        ws_process = start_websocket_server()
    
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
        subprocess.run(['node', 'server.js'], cwd=ui_dir, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ UI server failed with exit code {e.returncode}")
        cleanup()
    except KeyboardInterrupt:
        cleanup()


if __name__ == '__main__':
    main()