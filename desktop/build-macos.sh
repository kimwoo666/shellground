#!/usr/bin/env bash
# Run on the target Mac. This does not cross-compile or claim notarization.
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
python3.12 -m venv .venv-macos
mac_python="$project_dir/.venv-macos/bin/python"
"$mac_python" -m pip install -r requirements.txt -r python-requirements.txt
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYINSTALLER_CONFIG_DIR="$project_dir/build/pyinstaller-cache"
export MPLCONFIGDIR="$project_dir/build/matplotlib-cache"
"$mac_python" -m unittest test_python_course test_python_grading test_python_quiz test_python_worker test_python_review_grading test_build_layout
"$mac_python" build.py "$@"
