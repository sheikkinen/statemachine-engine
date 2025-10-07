#!/bin/bash
# Start a simple worker state machine
# Usage: ./scripts/start-worker.sh [config_file] [machine_name]

set -e

CONFIG=${1:-"examples/simple_worker/config/worker.yaml"}
MACHINE_NAME=${2:-"worker"}

echo "🚀 Starting worker state machine..."
echo "📄 Config: $CONFIG"
echo "🤖 Machine: $MACHINE_NAME"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    if [ -f "venv/bin/activate" ]; then
        echo "📦 Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ No virtual environment found. Please run:"
        echo "   python -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -e ."
        exit 1
    fi
fi

# Check if config file exists
if [ ! -f "$CONFIG" ]; then
    echo "❌ Config file not found: $CONFIG"
    exit 1
fi

# Start the state machine
echo "✓ Starting state machine..."
statemachine "$CONFIG" --machine-name "$MACHINE_NAME" --debug

