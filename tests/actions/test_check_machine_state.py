#!/usr/bin/env python3
"""
Standalone tester for check_machine_state_action

Tests the state checking logic to debug why controller sees stale data.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import sqlite3

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from statemachine_engine.actions.builtin import CheckMachineStateAction
from statemachine_engine.database.models import get_job_model

def test_direct_db_query():
    """Test direct database query to see what data exists"""
    print("=" * 60)
    print("Direct Database Query Test")
    print("=" * 60)

    db_path = 'data/pipeline.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT
            job_id,
            json_extract(metadata, '$.machine') as machine,
            json_extract(metadata, '$.state') as state,
            completed_at,
            (strftime('%s', 'now') - strftime('%s', completed_at)) as age_seconds
        FROM pipeline_results
        WHERE step_name = 'state_change'
          AND json_extract(metadata, '$.machine') = 'sdxl_generator'
        ORDER BY completed_at DESC
        LIMIT 5
    """)

    rows = cursor.fetchall()

    print(f"\nFound {len(rows)} state records for sdxl_generator:")
    print("-" * 60)
    for row in rows:
        print(f"  State: {row['state']}")
        print(f"  Timestamp: {row['completed_at']}")
        print(f"  Age: {row['age_seconds']}s")
        print()

    conn.close()
    return rows[0] if rows else None

def test_action_query():
    """Test the action's state query method"""
    print("=" * 60)
    print("CheckMachineStateAction Query Test")
    print("=" * 60)

    # Create action instance
    config = {
        'target_machine': 'sdxl_generator',
        'expected_states': ['waiting', 'waiting_for_controller'],
        'timeout_seconds': 30
    }

    action = CheckMachineStateAction(config)

    print(f"\nAction config:")
    print(f"  Target: {action.target_machine}")
    print(f"  Expected states: {action.expected_states}")
    print(f"  Timeout: {action.timeout_seconds}s")

    # Call internal method
    print(f"\nCalling _get_current_state()...")
    current_state = action._get_current_state('sdxl_generator')

    print(f"\nResult: {current_state}")

    if current_state:
        if current_state in action.expected_states:
            print(f"✅ State '{current_state}' is in expected states")
            return 'in_expected_state'
        else:
            print(f"⚠️ State '{current_state}' is NOT in expected states {action.expected_states}")
            return 'unexpected_state'
    else:
        print(f"❌ No recent state data (stale or missing)")
        return 'not_running'

def test_timestamp_parsing():
    """Test timestamp parsing to find timezone/format issues"""
    print("=" * 60)
    print("Timestamp Parsing Test")
    print("=" * 60)

    db_path = 'data/pipeline.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT completed_at
        FROM pipeline_results
        WHERE step_name = 'state_change'
          AND json_extract(metadata, '$.machine') = 'sdxl_generator'
        ORDER BY completed_at DESC
        LIMIT 1
    """).fetchone()

    if not row:
        print("❌ No state data found")
        return

    timestamp_str = row['completed_at']
    print(f"\nDatabase timestamp string: {timestamp_str}")
    print(f"Type: {type(timestamp_str)}")

    try:
        parsed = datetime.fromisoformat(timestamp_str)
        print(f"Parsed datetime: {parsed}")
        print(f"Parsed type: {type(parsed)}")

        now = datetime.now()
        print(f"Current datetime: {now}")
        print(f"Current type: {type(now)}")

        age = (now - parsed).total_seconds()
        print(f"\nCalculated age: {age:.1f}s")

        if age < 0:
            print("⚠️ WARNING: Negative age - timestamp is in the future!")
        elif age < 60:
            print(f"✅ Fresh data ({age:.1f}s old)")
        else:
            print(f"❌ Stale data ({age:.1f}s old)")

    except Exception as e:
        print(f"❌ Error parsing timestamp: {e}")

    conn.close()

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("CHECK MACHINE STATE ACTION STANDALONE TESTER")
    print("=" * 60)
    print()

    # Test 1: Direct DB query
    latest_row = test_direct_db_query()
    print()

    # Test 2: Timestamp parsing
    test_timestamp_parsing()
    print()

    # Test 3: Action query
    result = test_action_query()
    print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Latest state from direct query: {latest_row['state'] if latest_row else 'None'}")
    print(f"Action query result: {result}")
    print()

    if result == 'not_running':
        print("❌ ISSUE: Action returns 'not_running' but database has data")
        print("   This indicates a timestamp/staleness detection problem")
    elif result == 'unexpected_state':
        print("⚠️ State mismatch - controller should send ready_for_next_job event")
    else:
        print("✅ State validation working correctly")

if __name__ == '__main__':
    main()
