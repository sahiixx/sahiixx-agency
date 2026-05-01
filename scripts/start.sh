#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Ensure data dir exists
mkdir -p data

# Sync repos if registry is empty
if [ ! -f data/registry.json ]; then
    echo "=== Syncing GitHub repos ==="
    opa sync
fi

echo "=== Starting One Person Agency ==="
echo "API:     http://localhost:8080"
echo "Dashboard: http://localhost:8080/dashboard"
echo ""

# Start API server in background
echo "Starting API server..."
nohup uvicorn sahiixx_agency.api.main:app --host 0.0.0.0 --port 8080 > /tmp/opa_api.log 2>&1 < /dev/null &
echo $! > /tmp/opa_api.pid
sleep 3

echo "Agency is running!"
echo ""
echo "Commands:"
echo "  opa stats          # View stats"
echo "  opa registry       # View modules"
echo "  opa dispatch       # Dispatch tasks"
echo "  opa intel          # Run intel scout"
echo ""
echo "Press Ctrl+C to stop"

# Wait for interrupt
trap 'kill $(cat /tmp/opa_api.pid) 2>/dev/null; exit 0' INT
wait
