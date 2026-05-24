#!/usr/bin/env bash
set -euo pipefail

# Industrial Deep Diagnostic — Start Frontend
# Starts the Vue dev server on http://localhost:5180

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/app/frontend"

echo ""
echo "  Industrial Deep Diagnostic — Frontend"
echo "  ====================================="
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
  echo "  [ERROR] Node.js is not installed. Please install Node.js >= 18."
  exit 1
fi

echo "  Node.js: $(node -v)"

# Check if dependencies are installed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo ""
  echo "  Dependencies not found. Installing..."
  cd "$FRONTEND_DIR" && npm install
fi

echo ""
echo "  Starting Vue dev server on http://localhost:5180"
echo "  Backend API proxy: /api → http://localhost:3210"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

cd "$FRONTEND_DIR" && npx vite --host
