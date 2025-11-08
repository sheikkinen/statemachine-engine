#!/bin/bash

# Patient Records Demo - Multiple Concurrent Instances
# Demonstrates Kanban visualization with 10+ concurrent FSM instances

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config/patient-records.yaml"
CONTROLLER_CONFIG="$SCRIPT_DIR/config/concurrent-controller.yaml"
LOG_DIR="$SCRIPT_DIR/logs"

# Configurable instance count (default: 1, override with env var)
MACHINE_COUNT="${MACHINE_COUNT:-1}"

# Activate virtual environment if available
VENV_PATH="$SCRIPT_DIR/../../venv"
if [[ -d "$VENV_PATH" && -f "$VENV_PATH/bin/activate" ]]; then
    echo "🐍 Activating virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
elif [[ -n "$VIRTUAL_ENV" ]]; then
    echo "🐍 Using active virtual environment: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment found - ensure statemachine commands are in PATH"
fi

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Function to clean up background processes
cleanup() {
    echo "🧹 Cleaning up patient records demo..."
    
    # Stop controller first
    pkill -f "statemachine.*concurrent.*controller" 2>/dev/null || true
    
    # Stop any worker machines
    pkill -f "statemachine.*patient.*record" 2>/dev/null || true
    
    # Stop WebSocket server if running
    if [[ -f "$LOG_DIR/websocket_server.pid" ]]; then
        local ws_pid=$(cat "$LOG_DIR/websocket_server.pid")
        if ps -p "$ws_pid" >/dev/null 2>&1; then
            kill "$ws_pid" 2>/dev/null || true
            echo "✓ WebSocket server stopped"
        fi
        rm -f "$LOG_DIR/websocket_server.pid"
    fi
    
    # Stop UI server if running
    if [[ -f "$LOG_DIR/ui_server.pid" ]]; then
        local ui_pid=$(cat "$LOG_DIR/ui_server.pid")
        if ps -p "$ui_pid" >/dev/null 2>&1; then
            kill "$ui_pid" 2>/dev/null || true
            echo "✓ UI server stopped"
        fi
        rm -f "$LOG_DIR/ui_server.pid"
    fi
    
    # Clean up control sockets (controller + workers)
    rm -f /tmp/statemachine-control-concurrent_controller.sock 2>/dev/null || true
    rm -f /tmp/statemachine-control-patient_record_*.sock 2>/dev/null || true
    
    # Nuke the database for fresh start (both locations)
    if [[ -f "$SCRIPT_DIR/data/pipeline.db" ]]; then
        rm -f "$SCRIPT_DIR/data/pipeline.db"
        echo "✓ Database cleaned (local)"
    fi
    if [[ -f "$SCRIPT_DIR/../../data/pipeline.db" ]]; then
        rm -f "$SCRIPT_DIR/../../data/pipeline.db"
        echo "✓ Database cleaned (repo root)"
    fi
    
    sleep 2
    echo "✅ Cleanup complete"
}

# Function to populate job queue with pending jobs
populate_queue() {
    echo "📥 Populating job queue with $MACHINE_COUNT jobs..."
    
    for i in $(seq 1 $MACHINE_COUNT); do
        local job_id="job_$(printf '%03d' $i)"
        local report_id="report_${i}"
        
        statemachine-db add-job "$job_id" \
            --type patient_records \
            --payload "{\"report_id\":\"${report_id}\",\"report_title\":\"Patient Report ${i}\",\"summary_text\":\"Processing report ${i}\"}" \
            >/dev/null 2>&1
        
        echo "   └─ Added job: $job_id (report: $report_id)"
    done
    
    echo "✅ Queue populated with $MACHINE_COUNT jobs"
}

# Function to start the controller (spawns workers as needed)
start_controller() {
    echo "🎮 Starting concurrent controller..."
    local controller_name="concurrent_controller"
    local log_file="$LOG_DIR/${controller_name}.log"
    
    # Start controller in background
    statemachine "$CONTROLLER_CONFIG" \
        --machine-name "$controller_name" > "$log_file" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$LOG_DIR/${controller_name}.pid"
    echo "   └─ PID: $pid, Log: $log_file"
    echo "   └─ Controller will spawn workers for queued jobs"
}

# Function to start a single machine instance (legacy, kept for compatibility)
start_machine() {
    local instance_id=$1
    local machine_name="patient_record_${instance_id}"
    local log_file="$LOG_DIR/${machine_name}.log"
    
    echo "🏥 Starting machine: $machine_name"
    
    # Start state machine in background
    statemachine "$CONFIG_FILE" \
        --machine-name "$machine_name" > "$log_file" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$LOG_DIR/${machine_name}.pid"
    echo "   └─ PID: $pid, Log: $log_file"
}

# Function to start WebSocket monitoring server
start_monitoring() {
    echo "📡 Starting WebSocket monitoring server..."
    cd "$SCRIPT_DIR/../.."
    
    # Check if monitoring server is already running
    if lsof -ti:3002 >/dev/null 2>&1; then
        echo "   └─ Monitoring server already running on port 3002"
        return 0
    fi
    
    # Start monitoring in background
    python -m statemachine_engine.monitoring.websocket_server > "$LOG_DIR/websocket-server.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$LOG_DIR/websocket_server.pid"
    echo "   └─ PID: $pid, URL: http://localhost:3002"
    
    # Wait for server to start
    sleep 3
}

# Function to generate FSM diagrams
generate_diagrams() {
    echo "📚 Generating FSM diagrams..."
    cd "$SCRIPT_DIR/../.."
    
    mkdir -p docs/fsm-diagrams
    
    echo "📄 Processing $CONFIG_FILE..."
    python -m statemachine_engine.tools.cli "$CONFIG_FILE" 2>&1 | grep -E "(✅|⚠️|❌|📁)" || {
        echo "  ⚠️  Failed to generate diagrams"
    }
    
    if ls docs/fsm-diagrams/patient_records/*.mermaid 1> /dev/null 2>&1; then
        echo "✓ Diagrams generated in docs/fsm-diagrams/patient_records/"
    else
        echo "⚠️  No diagrams generated (UI may not display properly)"
    fi
    echo ""
}

# Function to start UI server
start_ui_server() {
    echo "🖥️  Starting Web UI..."
    
    # Check if statemachine-ui is available
    if ! command -v statemachine-ui &> /dev/null; then
        echo "⚠️  statemachine-ui not found, skipping Web UI"
        echo "   Install statemachine-engine to enable the web interface"
        return 1
    fi
    
    # Kill any stale processes on port 3001
    lsof -ti:3001 | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Start UI server in background using statemachine-ui command
    local project_root="$(cd "$SCRIPT_DIR/../.." && pwd)"
    statemachine-ui --port 3001 --project-root "$project_root" --no-websocket > "$LOG_DIR/ui-server.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$LOG_DIR/ui_server.pid"
    
    # Wait for UI to be ready with health checks
    local max_attempts=10
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        sleep 1
        if curl -s http://localhost:3001/api/config > /dev/null 2>&1; then
            echo "   └─ PID: $pid, URL: http://localhost:3001"
            echo "   └─ UI server ready"
            return 0
        fi
        attempt=$((attempt + 1))
    done
    
    echo "   └─ ⚠️ UI server may not be fully ready (check logs/ui-server.log)"
    return 1
}

# Function to send sample events to machines (legacy)
send_sample_events() {
    echo "📨 Sample events sent via job queue..."
    echo "   └─ Controller is managing worker lifecycle"
    echo ""
    echo "📊 Demo running! Open http://localhost:3001 and press 'K' for Kanban view"
    echo "💡 Workers will spawn automatically as controller processes queue"
}

# Function to send continuous events for dynamic demo
continuous_events() {
    echo "🔄 Adding jobs continuously to the queue..."
    echo "   Controller will spawn workers as needed"
    echo ""
    
    local counter=$((MACHINE_COUNT + 1))
    
    while true; do
        local job_id="job_$(printf '%03d' $counter)"
        local report_id="report_${counter}"
        
        echo "   └─ [$counter] Adding job: $job_id"
        
        statemachine-db add-job "$job_id" \
            --type patient_records \
            --payload "{\"report_id\":\"${report_id}\",\"report_title\":\"Report ${counter}\",\"timestamp\":\"$(date -Iseconds)\"}" \
            >/dev/null 2>&1
        
        counter=$((counter + 1))
        
        # Random delay between 3-10 seconds
        sleep $(( (RANDOM % 8) + 3 ))
    done
}

# Function to show status of all machines
status() {
    echo "📊 Patient Records Demo Status (Controller Pattern):"
    echo "===================================================="
    
    # Check monitoring server
    if lsof -ti:3002 >/dev/null 2>&1; then
        echo "✅ Monitoring server: Running (http://localhost:3002)"
    else
        echo "❌ Monitoring server: Not running"
    fi
    
    # Check UI server
    if lsof -ti:3001 >/dev/null 2>&1; then
        echo "✅ UI server: Running (http://localhost:3001)"
    else
        echo "❌ UI server: Not running"
    fi
    
    # Check controller
    local controller_pid_file="$LOG_DIR/concurrent_controller.pid"
    if [[ -f "$controller_pid_file" ]]; then
        local pid=$(cat "$controller_pid_file")
        if ps -p "$pid" >/dev/null 2>&1; then
            echo "✅ Controller: Running (PID: $pid)"
        else
            echo "❌ Controller: Stopped"
            rm -f "$controller_pid_file"
        fi
    else
        echo "❌ Controller: Not started"
    fi
    
    # Check worker machines (dynamically spawned)
    echo ""
    echo "🔍 Active Workers (spawned by controller):"
    local worker_count=0
    for pid_file in "$LOG_DIR"/patient_record_*.pid; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            local machine_name=$(basename "$pid_file" .pid)
            if ps -p "$pid" >/dev/null 2>&1; then
                echo "   └─ $machine_name (PID: $pid)"
                worker_count=$((worker_count + 1))
            else
                rm -f "$pid_file"
            fi
        fi
    done
    
    if [[ $worker_count -eq 0 ]]; then
        echo "   └─ No active workers (controller spawns workers as needed)"
    fi
    
    echo ""
    echo "📋 Job Queue Status:"
    # Show pending jobs count
    local pending_count=$(statemachine-db list-jobs --status pending 2>/dev/null | grep -c "patient_records" || echo "0")
    echo "   └─ Pending jobs: $pending_count"
    
    echo "--------------------------------"
    echo "Total: $worker_count active workers"
    
    # Show recent activity
    echo ""
    echo "📋 Recent Controller Activity (last 5 entries):"
    if [[ -f "$LOG_DIR/concurrent_controller.log" ]]; then
        tail -n 5 "$LOG_DIR/concurrent_controller.log" 2>/dev/null | grep -E "(�|🚀|✅|😴|❌)" || echo "   └─ No recent activity"
    else
        echo "   └─ Controller log not found"
    fi
}

# Function to show real-time events
events() {
    echo "📺 Real-time event monitor (Ctrl+C to stop):"
    echo "=============================================="
    statemachine-events
}

# Main command dispatch
case "${1:-help}" in
    "start")
        echo "🏥 Starting Patient Records Demo (Controller Pattern) with $MACHINE_COUNT jobs..."
        cleanup
        generate_diagrams
        start_monitoring
        start_ui_server
        
        # Populate job queue
        populate_queue
        
        echo ""
        echo "⏳ Waiting for services to initialize..."
        sleep 3
        
        # Start controller (spawns workers dynamically)
        start_controller
        
        echo ""
        sleep 2
        
        send_sample_events
        echo ""
        echo "🎯 Demo started successfully!"
        echo "   • Web UI: http://localhost:3001"
        echo "   • Monitoring: http://localhost:3002"
        echo "   • Press 'K' in UI for Kanban view"
        echo "   • Controller spawns workers as needed"
        echo "   • Run '$0 events' to watch real-time events"
        echo "   • Run '$0 continuous' to add jobs dynamically"
        echo "   • Run '$0 status' to see controller + workers"
        ;;
        
    "continuous")
        echo "🎬 Adding jobs continuously to queue..."
        echo "   Controller will spawn workers dynamically"
        echo "Press Ctrl+C to stop"
        continuous_events
        ;;
        
    "events")
        events
        ;;
        
    "status")
        status
        ;;
        
    "cleanup"|"stop")
        cleanup
        ;;
        
    "help"|*)
        echo "🏥 Patient Records Demo - Controller Pattern + Kanban"
        echo "====================================================="
        echo ""
        echo "Usage: $0 <command>"
        echo "       MACHINE_COUNT=<n> $0 <command>  (set job count, default: 1)"
        echo ""
        echo "Commands:"
        echo "  start      Start controller + monitoring (spawns workers dynamically)"
        echo "  continuous Add jobs continuously to queue"
        echo "  events     Show real-time event stream"
        echo "  status     Show controller + active workers"
        echo "  cleanup    Stop controller, workers, and clean up"
        echo "  help       Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 start                    # Start with 1 job"
        echo "  MACHINE_COUNT=10 $0 start   # Start with 10 jobs in queue"
        echo ""
        echo "Demo Workflow:"
        echo "1. Run 'MACHINE_COUNT=3 $0 start' to populate queue with 3 jobs"
        echo "2. Controller spawns workers dynamically (patient_record_job_001, etc.)"
        echo "3. Open http://localhost:3001 in browser"
        echo "4. Press 'K' key to open Kanban view"
        echo "5. Watch workers process jobs and complete"
        echo "6. Run '$0 continuous' in another terminal to add more jobs"
        echo "7. Controller spawns new workers as jobs arrive"
        echo ""
        echo "Architecture:"
        echo "  concurrent-controller.yaml  → Reads queue, spawns workers"
        echo "  patient-records.yaml        → Worker FSM (spawned per job)"
        echo "  Database queue              → Job storage (pending → processing → completed)"
        echo ""
        ;;
esac