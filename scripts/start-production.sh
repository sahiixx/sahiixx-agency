#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "=== Starting One Person Agency (production) ==="

mkdir -p data

docker compose up --build -d

echo ""
echo "Services starting in detached mode. Health endpoints:"
echo "  API:  http://localhost:8080/health"
echo "  MCP:  http://localhost:8081/health"
echo "  Dashboard: http://localhost:8080/dashboard"
echo ""
echo "View logs: docker compose logs -f"
echo "Stop:     docker compose down"
