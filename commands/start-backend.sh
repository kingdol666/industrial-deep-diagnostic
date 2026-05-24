#!/usr/bin/env bash
set -euo pipefail

# Industrial Deep Diagnostic — Start Backend
# Starts the Express API server on http://localhost:3210

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/app/backend"

echo ""
echo "  Industrial Deep Diagnostic — Backend"
echo "  ===================================="
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
  echo "  [ERROR] Node.js is not installed. Please install Node.js >= 18."
  exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
echo "  Node.js: $(node -v)"

# Check if dependencies are installed
if [ ! -d "$BACKEND_DIR/node_modules" ]; then
  echo ""
  echo "  Dependencies not found. Installing..."
  cd "$BACKEND_DIR" && npm install
fi

# Ensure data directory exists
mkdir -p "$PROJECT_ROOT/data"
mkdir -p "$PROJECT_ROOT/workspace/diagnostic-runs"

echo ""
echo "  Starting Express API server on http://localhost:3210"
echo "  Project root: $PROJECT_ROOT"
echo "  Data directory: $PROJECT_ROOT/data"
echo "  Workspace directory: $PROJECT_ROOT/workspace/diagnostic-runs"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

cd "$PROJECT_ROOT" && node "$BACKEND_DIR/src/index.mjs"
