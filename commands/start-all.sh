#!/usr/bin/env bash
set -euo pipefail

# Industrial Deep Diagnostic — Start All
# Starts both backend and frontend concurrently

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   Industrial Deep Diagnostic — Full Stack    ║"
echo "  ║   Backend:  http://localhost:3210             ║"
echo "  ║   Frontend: http://localhost:5180             ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

cleanup() {
  echo ""
  echo "  Shutting down..."
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  echo "  All processes stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "  Starting backend..."
bash "$SCRIPT_DIR/start-backend.sh" &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 1

# Start frontend
echo "  Starting frontend..."
bash "$SCRIPT_DIR/start-frontend.sh" &
FRONTEND_PID=$!

echo ""
echo "  Both servers are running."
echo "  Open http://localhost:5180 in your browser."
echo "  Press Ctrl+C to stop all."
echo ""

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID 2>/dev/null || true

cleanup
