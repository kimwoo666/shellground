#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SHELLGROUND_PYTHON:-python3}"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
fi
export PYTHONPATH="$SCRIPT_DIR/.python-runtime:$SCRIPT_DIR/.runtime:$SCRIPT_DIR/.build-tools${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYINSTALLER_CONFIG_DIR="$SCRIPT_DIR/build/pyinstaller-cache"
export MPLCONFIGDIR="$SCRIPT_DIR/build/matplotlib-cache"
"$PYTHON_BIN" "$SCRIPT_DIR/build.py" "$@"
