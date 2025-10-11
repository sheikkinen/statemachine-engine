#!/usr/bin/env python3
"""
Manual test for send-event real-time delivery
Run this to verify that CLI events appear in the Web UI immediately
"""
import subprocess
import time
import sys
from pathlib import Path

def run_command(cmd):
    """Run a command and return the output"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def main():
    print("=" * 70)
    print("MANUAL TEST: send-event Real-time Delivery")
    print("=" * 70)
    print()
    
    # Check if WebSocket server is running
    print("1. Checking if WebSocket server is running...")
    socket_path = Path('/tmp/statemachine-events.sock')
    if socket_path.exists():
        print("   ✅ WebSocket server socket found")
    else:
        print("   ⚠️  WebSocket server not running!")
        print("   Start it with: statemachine-ui")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return 1
    print()
    
    # Test 1: Send activity_log to UI
    print("2. Sending activity_log to UI...")
    cmd = (
        'python -m statemachine_engine.database.cli send-event '
        '--target ui --type activity_log '
        '--payload \'{"message": "Test from manual test script", "level": "INFO"}\''
    )
    code, stdout, stderr = run_command(cmd)
    print(f"   Exit code: {code}")
    print(f"   Output:\n{stdout}")
    if stderr:
        print(f"   Errors:\n{stderr}")
    
    if "Sent to WebSocket server" in stdout:
        print("   ✅ Real-time socket delivery confirmed")
    else:
        print("   ⚠️  No WebSocket socket delivery detected")
    print()
    
    # Test 2: Send with custom source
    print("3. Sending activity_log with custom source...")
    cmd = (
        'python -m statemachine_engine.database.cli send-event '
        '--target ui --type activity_log --source manual_test '
        '--payload \'{"message": "From manual_test source", "level": "SUCCESS"}\''
    )
    code, stdout, stderr = run_command(cmd)
    print(f"   Exit code: {code}")
    print(f"   Output:\n{stdout}")
    if stderr:
        print(f"   Errors:\n{stderr}")
    print()
    
    # Test 3: Send to non-UI target
    print("4. Sending event to non-UI target (worker1)...")
    cmd = (
        'python -m statemachine_engine.database.cli send-event '
        '--target worker1 --type custom_event '
        '--payload \'{"data": "test"}\''
    )
    code, stdout, stderr = run_command(cmd)
    print(f"   Exit code: {code}")
    print(f"   Output:\n{stdout}")
    if stderr:
        print(f"   Errors:\n{stderr}")
    
    if "Sent to WebSocket server" in stdout and "Sent to worker1 control socket" in stdout:
        print("   ✅ Both sockets attempted (WebSocket + control)")
    elif "Sent to WebSocket server" in stdout:
        print("   ✅ WebSocket delivery confirmed")
    else:
        print("   ℹ️  Socket delivery status unclear")
    print()
    
    # Test 4: Query recent events from database
    print("5. Querying recent events from database...")
    cmd = 'python -m statemachine_engine.database.cli list-events --target ui --limit 5'
    code, stdout, stderr = run_command(cmd)
    print(f"   Exit code: {code}")
    print(f"   Output:\n{stdout}")
    if stderr:
        print(f"   Errors:\n{stderr}")
    print()
    
    print("=" * 70)
    print("MANUAL VERIFICATION STEPS:")
    print("=" * 70)
    print()
    print("1. Open the Web UI in your browser")
    print("2. Navigate to the Activity Log tab")
    print("3. Run this script again")
    print("4. Verify that the messages appear IMMEDIATELY (without refresh)")
    print()
    print("Expected messages:")
    print("  - 'Test from manual test script' (level: INFO, source: cli)")
    print("  - 'From manual_test source' (level: SUCCESS, source: manual_test)")
    print()
    print("If messages appear instantly → ✅ Real-time delivery working!")
    print("If messages require refresh → ❌ Real-time delivery not working")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
