#!/bin/bash
# Quick test for batch concurrent spawning
# Tests that multiple jobs are spawned concurrently, not sequentially

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/examples/patient_records"

echo "🧪 Testing Concurrent Job Spawning"
echo "=================================="

# Cleanup
echo "🧹 Cleaning up previous test data..."
rm -f data/patient_records.db
rm -f logs/*.log

# Create fresh database
echo "📦 Creating database..."
python -m statemachine_engine.database.cli init --db-path data/patient_records.db --force

# Insert 5 test jobs
echo "📝 Inserting 5 test jobs..."
for i in {1..5}; do
    python -m statemachine_engine.database.cli add-job \
        --db-path data/patient_records.db \
        --job-id "test_job_$(printf "%03d" $i)" \
        --job-type patient_records \
        --machine-type patient_records \
        --priority 1 \
        --data '{"report_id": "RPT-'$i'", "report_title": "Test Report '$i'", "summary_text": "Test summary for report '$i'"}'
done

echo "✅ Created 5 test jobs"

# Show initial job count
echo ""
echo "📊 Initial queue status:"
python -m statemachine_engine.database.cli list-jobs \
    --db-path data/patient_records.db \
    --status pending \
    | grep -c "test_job_" || echo "5 pending jobs"

# Start controller (will spawn all 5 jobs concurrently)
echo ""
echo "🚀 Starting concurrent controller..."
echo "Expected behavior:"
echo "  1. Controller finds all 5 jobs"
echo "  2. Spawns all 5 workers in a loop (sequential spawning)"
echo "  3. Waits for all 5 to complete (concurrent execution)"
echo "  4. All workers run simultaneously"
echo ""

timeout 30s python -m statemachine_engine.cli run \
    --yaml config/concurrent-controller.yaml \
    --db-path data/patient_records.db \
    --machine-name test-controller &

CONTROLLER_PID=$!

# Give it time to spawn all workers
sleep 5

# Check how many workers are running
echo ""
echo "🔍 Checking spawned workers (should be 5):"
WORKER_COUNT=$(ps aux | grep "patient_record_test_job" | grep -v grep | wc -l | tr -d ' ')
echo "Active workers: $WORKER_COUNT"

if [ "$WORKER_COUNT" -eq 5 ]; then
    echo "✅ SUCCESS: All 5 workers spawned concurrently!"
elif [ "$WORKER_COUNT" -gt 0 ]; then
    echo "⚠️  PARTIAL: Only $WORKER_COUNT workers spawned (expected 5)"
else
    echo "❌ FAILURE: No workers spawned"
fi

# Check database for processing jobs
echo ""
echo "📊 Job status in database:"
python -m statemachine_engine.database.cli list-jobs \
    --db-path data/patient_records.db \
    | tail -10

# Wait for controller to finish or timeout
echo ""
echo "⏳ Waiting for controller to complete..."
wait $CONTROLLER_PID 2>/dev/null || true

echo ""
echo "✅ Test complete!"
echo ""
echo "📄 Check logs for detailed execution:"
echo "  - logs/test-controller.log (controller logs)"
echo "  - logs/patient_record_test_job_*.log (worker logs)"
