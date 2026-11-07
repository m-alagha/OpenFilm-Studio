#!/usr/bin/env bash
# Run every check: secret scan, backend lint/types/tests, mock smoke, frontend lint/types/
# tests/build, and the end-to-end dev-stack smoke test.
# Offline after install. Makes no provider calls and needs no API key.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== secret scan"
(cd "$ROOT" && uv run --no-sync --project backend python scripts/check_secrets.py)

echo "== backend"
cd "$ROOT/backend"
uv run --no-sync ruff check . ../scripts
uv run --no-sync ruff format --check . ../scripts
uv run --no-sync mypy
uv run --no-sync pytest -q
uv run --no-sync python -m app.smoke

echo "== frontend"
cd "$ROOT/frontend"
npm run --silent check

echo "== end-to-end smoke (real backend + UI, temporary data dir)"
cd "$ROOT"
uv run --no-sync --project backend python scripts/e2e_smoke.py

echo "ALL CHECKS PASSED"
