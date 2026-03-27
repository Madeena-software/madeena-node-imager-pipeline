#!/usr/bin/env bash
set -euo pipefail
# Run backend/app.py from repository root without needing to cd into backend/
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Prefer virtualenv python if present
if [ -x "$REPO_ROOT/.venv/bin/python3" ]; then
  PY="$REPO_ROOT/.venv/bin/python3"
else
  PY="${PY:-python3}"
fi
exec "$PY" "$REPO_ROOT/backend/app.py" "$@"
