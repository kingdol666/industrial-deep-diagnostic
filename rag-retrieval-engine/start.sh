#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# 1. Create virtual environment (if not exists)
if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment with uv..."
    uv venv
fi

# 2. Install dependencies
echo "📦 Installing dependencies..."
uv sync

# 3. Start server
echo "🚀 Starting RAG Retrieval Engine..."
uv run python server.py
