#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SHELLGROUND_PYTHON:-python3}"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
fi
export PYTHONPATH="$SCRIPT_DIR/.runtime:$SCRIPT_DIR/.build-tools${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON_BIN" "$SCRIPT_DIR/build.py"
