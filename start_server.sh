#!/bin/bash
# Visionary Server Startup Script

echo "========================================="
echo "  VISIONARY DETECTION SYSTEM"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import websockets" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Starting Visionary server..."
echo ""
echo "Web UI: Open web/index.html in your browser"
echo "Server: ws://localhost:8765"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================="
echo ""

# Start the server
python3 backend/server.py
