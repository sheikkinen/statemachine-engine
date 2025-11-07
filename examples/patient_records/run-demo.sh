#!/bin/bash

# Patient Records Demo - Multiple Concurrent Instances
# Demonstrates Kanban visualization with 10+ concurrent FSM instances

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config/patient-records.yaml"
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
    pkill -f "statemachine.*patient.*record" 2>/dev/null || true
    
    # Stop UI server if running
    if [[ -f "$LOG_DIR/ui_server.pid" ]]; then
        local ui_pid=$(cat "$LOG_DIR/ui_server.pid")
        if ps -p "$ui_pid" >/dev/null 2>&1; then
            kill "$ui_pid" 2>/dev/null || true
            echo "✓ UI server stopped"
        fi
        rm -f "$LOG_DIR/ui_server.pid"
    fi
    
    sleep 2
    echo "✅ Cleanup complete"
}

# Function to start a single machine instance
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
    cd "$SCRIPT_DIR/../.."
    
    # Check if UI server is already running
    if lsof -ti:3001 >/dev/null 2>&1; then
        echo "   └─ UI server already running on port 3001"
        return 0
    fi
    
    # Check if Node.js is available
    if ! command -v node &> /dev/null; then
        echo "⚠️  Node.js not found, skipping Web UI"
        echo "   Install Node.js to enable the web interface"
        return 1
    fi
    
    # Start UI server in background
    cd src/statemachine_engine/ui
    PROJECT_ROOT="$SCRIPT_DIR/../.." node server.cjs > "$LOG_DIR/ui-server.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$LOG_DIR/ui_server.pid"
    cd "$SCRIPT_DIR"
    echo "   └─ PID: $pid, URL: http://localhost:3001"
    
    # Wait for UI server to start
    sleep 2
}

# Function to send sample events to machines
send_sample_events() {
    echo "📨 Sending generic job events to all machines..."
    
    # Send generic job_N events to each machine
    for i in $(seq 1 $MACHINE_COUNT); do
        local machine_name="patient_record_${i}"
        local job_id="job_${i}"
        
        echo "   └─ Sending new_report (${job_id}) to $machine_name"
        
        statemachine-db send-event \
            --target "$machine_name" \
            --type "new_report" \
            --payload "{\"report_id\":\"${job_id}\",\"report_title\":\"Job ${i}\",\"summary_text\":\"Processing job ${i}\"}" \
            >/dev/null 2>&1
        
        # Brief delay between events
        sleep 0.2
    done
    
    echo "📊 Demo running! Open http://localhost:3002 and press 'K' for Kanban view"
    echo "💡 Events will process automatically via timeouts (10s summarizing, 5s fact-checking)"
}

# Function to send continuous events for dynamic demo
continuous_events() {
    echo "🔄 Starting continuous event simulation..."
    
    local event_types=("summary_complete" "validation_passed" "validation_failed" "summary_invalid" "process_next")
    local counter=1
    
    while true; do
        # Pick random machine and event
        local machine_num=$(( (RANDOM % MACHINE_COUNT) + 1 ))
        local machine_name="patient_record_${machine_num}"
        local event_type="${event_types[$((RANDOM % ${#event_types[@]}))]}"
        
        echo "   └─ [$counter] Sending $event_type to $machine_name"
        
        statemachine-db send-event \
            --target "$machine_name" \
            --type "$event_type" \
            --payload "{\"timestamp\":\"$(date -Iseconds)\"}" \
            >/dev/null 2>&1
        
        counter=$((counter + 1))
        
        # Random delay between 2-8 seconds
        sleep $(( (RANDOM % 7) + 2 ))
    done
}

# Function to show status of all machines
status() {
    echo "📊 Patient Records Demo Status:"
    echo "================================"
    
    # Check monitoring server
    if lsof -ti:3002 >/dev/null 2>&1; then
        echo "✅ Monitoring server: Running (http://localhost:3002)"
    else
        echo "❌ Monitoring server: Not running"
    fi
    
    # Check each machine
    local running_count=0
    for i in $(seq 1 $MACHINE_COUNT); do
        local machine_name="patient_record_${i}"
        local pid_file="$LOG_DIR/${machine_name}.pid"
        
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if ps -p "$pid" >/dev/null 2>&1; then
                echo "✅ $machine_name: Running (PID: $pid)"
                running_count=$((running_count + 1))
            else
                echo "❌ $machine_name: Stopped"
                rm -f "$pid_file"
            fi
        else
            echo "❌ $machine_name: Not started"
        fi
    done
    
    echo "--------------------------------"
    echo "Total: $running_count/$MACHINE_COUNT machines running"
    
    # Show recent activity
    echo ""
    echo "📋 Recent Activity (last 10 entries):"
    if [[ -n "$(ls -A "$LOG_DIR"/*.log 2>/dev/null)" ]]; then
        tail -n 2 "$LOG_DIR"/*.log 2>/dev/null | grep -E "(📄|✍️|✅|❌|🔄)" | tail -10
    else
        echo "   └─ No activity logs found"
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
        echo "🏥 Starting Patient Records Demo with $MACHINE_COUNT instances..."
        cleanup
        generate_diagrams
        start_monitoring
        start_ui_server
        
        for i in $(seq 1 $MACHINE_COUNT); do
            start_machine $i
            sleep 0.2  # Brief delay between starts
        done
        
        echo ""
        echo "⏳ Waiting for machines to initialize..."
        sleep 5
        
        send_sample_events
        echo ""
        echo "🎯 Demo started successfully!"
        echo "   • Web UI: http://localhost:3001"
        echo "   • Monitoring: http://localhost:3002"
        echo "   • Press 'K' in UI for Kanban view"
        echo "   • Run '$0 events' to watch real-time events"
        echo "   • Run '$0 continuous' for dynamic simulation"
        ;;
        
    "continuous")
        echo "🎬 Starting continuous event simulation..."
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
        echo "🏥 Patient Records Demo - Kanban Visualization"
        echo "=============================================="
        echo ""
        echo "Usage: $0 <command>"
        echo "       MACHINE_COUNT=<n> $0 <command>  (set instance count, default: 1)"
        echo ""
        echo "Commands:"
        echo "  start      Start patient record machines + monitoring"
        echo "  continuous Start continuous event simulation for dynamic demo"
        echo "  events     Show real-time event stream"
        echo "  status     Show current status of all machines"
        echo "  cleanup    Stop all machines and clean up"
        echo "  help       Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 start                    # Start 1 machine (default)"
        echo "  MACHINE_COUNT=10 $0 start   # Start 10 machines"
        echo ""
        echo "Demo Workflow:"
        echo "1. Run 'MACHINE_COUNT=1 $0 start' to test with 1 machine"
        echo "2. Open http://localhost:3002 in browser"
        echo "3. Watch job flow: waiting → summarizing → fact_checking → ready"
        echo "4. Run 'MACHINE_COUNT=10 $0 start' to test Kanban with 10 machines"
        echo "5. Press 'K' key to open Kanban view"
        echo "6. Run '$0 continuous' in another terminal for dynamic simulation"
        echo ""
        ;;
esac