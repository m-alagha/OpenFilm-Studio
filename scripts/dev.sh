#!/usr/bin/env sh
# One-command development start for macOS/Linux. Requires uv and Node.js 22+.
set -e
cd "$(dirname "$0")/.."
exec uv run --project backend --frozen --extra dev python scripts/dev.py "$@"
