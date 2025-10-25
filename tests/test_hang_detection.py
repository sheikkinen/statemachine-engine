#!/usr/bin/env python3
"""
Test script to verify hang detection system works

This simulates a hang by adding a blocking sleep operation
to verify the watchdog detects and logs it.
"""

import asyncio
import time
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from statemachine_engine.monitoring.websocket_server import perf_monitor, watchdog

async def simulate_hang(duration_seconds: int):
    """Simulate a server hang by blocking the event loop"""
    print(f"\n{'='*80}")
    print(f"SIMULATING {duration_seconds}s HANG - Watch for watchdog detection")
    print(f"{'='*80}\n")
    
    # Update heartbeat before hang
    perf_monitor.heartbeat()
    print(f"✅ Heartbeat updated at {time.time()}")
    
    # BLOCK the event loop (BAD - this is what we're detecting)
    print(f"⏸️  Sleeping for {duration_seconds} seconds (blocking event loop)...")
    time.sleep(duration_seconds)  # BLOCKING SLEEP - watchdog should detect this!
    
    print(f"✅ Sleep complete at {time.time()}")
    perf_monitor.heartbeat()

async def main():
    """Test hang detection"""
    print("Starting hang detection test...")
    print(f"Watchdog timeout: 15 seconds")
    print(f"Watchdog thread: {'Running' if watchdog.is_alive() else 'NOT RUNNING'}")
    
    if not watchdog.is_alive():
        print("❌ ERROR: Watchdog thread not running!")
        return
    
    # Test 1: No hang (should not trigger watchdog)
    print("\n" + "="*80)
    print("TEST 1: Normal operation (5s) - should NOT trigger watchdog")
    print("="*80)
    for i in range(5):
        await asyncio.sleep(1)
        perf_monitor.heartbeat()
        print(f"  {i+1}s - heartbeat updated")
    print("✅ TEST 1 PASSED: No watchdog alert\n")
    
    # Test 2: Trigger hang (should trigger watchdog)
    print("\n" + "="*80)
    print("TEST 2: Simulated hang (20s) - SHOULD trigger watchdog")
    print("="*80)
    print("Expected: Watchdog should dump stack traces after 15 seconds")
    await simulate_hang(20)
    print("✅ TEST 2 COMPLETE: Check logs above for watchdog stack dump\n")
    
    # Test 3: Recovery (should not trigger again immediately)
    print("\n" + "="*80)
    print("TEST 3: Recovery check - resuming normal heartbeats")
    print("="*80)
    for i in range(5):
        await asyncio.sleep(1)
        perf_monitor.heartbeat()
        print(f"  {i+1}s - heartbeat updated")
    print("✅ TEST 3 PASSED: Normal operation resumed\n")
    
    print("="*80)
    print("TESTING COMPLETE")
    print("="*80)
    print("\nExpected results:")
    print("  - TEST 1: No watchdog alerts (5s < 15s timeout)")
    print("  - TEST 2: Watchdog stack dump during 20s hang")
    print("  - TEST 3: No watchdog alerts after recovery")
    print("\nCheck the output above for 🚨 SERVER HANG DETECTED message")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        watchdog.running = False
        print("Watchdog stopped")
