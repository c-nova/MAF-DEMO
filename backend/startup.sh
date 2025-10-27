#!/bin/bash
set -e

echo "🚀 Starting MAF Demo Backend..."

# uvでアプリケーションを実行
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
