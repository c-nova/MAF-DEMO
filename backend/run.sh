#!/bin/bash
set -e

echo "🚀 Starting MAF Demo Backend..."

# backendディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# uvicornを実行
exec .venv/bin/python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
