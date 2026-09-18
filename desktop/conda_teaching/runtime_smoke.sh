#!/usr/bin/env bash
# Only invoked in the marked, disconnected image-builder guest as learner.
set -euo pipefail
test -e /dev/virtio-ports/org.shellground.agent
test "$(cat /opt/shellground/guest-owned)" = shellground-disposable-guest-v1
test "$(id -u)" = 1100
source /opt/shellground/miniconda/etc/profile.d/conda.sh
test ! -e /home/learner/conda-envs/sg-proof
test ! -e /home/learner/conda-envs/sg-copy
step() {
    local label="$1" started="$SECONDS"
    shift
    printf 'SG_STEP_START %s elapsed=%ss\n' "$label" "$SECONDS"
    "$@"
    printf 'SG_STEP_DONE %s duration=%ss\n' "$label" "$((SECONDS-started))"
}
cleanup() {
    local outcome="$1"
    printf 'SG_SMOKE_EXIT code=%s elapsed=%ss\n' "$outcome" "$SECONDS"
    set +e
    conda deactivate >/dev/null 2>&1
    # These two names were verified absent before this run. Never clean any
    # other environment or use a recursive removal on the learner's home.
    for smoke_prefix in /home/learner/conda-envs/sg-proof /home/learner/conda-envs/sg-copy; do
        if [[ -f "$smoke_prefix/conda-meta/history" ]]; then
            timeout 15 /opt/shellground/miniconda/bin/conda env remove --prefix "$smoke_prefix" -y >/dev/null 2>&1
        fi
    done
    exit "$outcome"
}
trap 'cleanup "$?"' EXIT
mkdir -p /home/learner/conda-proof
cd /home/learner/conda-proof
step create conda create -n sg-proof python=3.12 training-math=1.0 -y
step activate conda activate sg-proof
step interpreter python -c 'import sys, training_math as m; assert sys.version_info[:2] == (3,12); assert sys.prefix == "/home/learner/conda-envs/sg-proof"; assert m.__version__ == "1.0"; assert m.total([2,3,5]) == 10'
step install conda install training-text=1.0 -y
step import_text python -c 'import training_text as t; assert t.normalize(" hello ") == "HELLO"'
step update conda update training-math -y
step import_update python -c 'import training_math as m; assert m.__version__ == "1.1"; assert m.mean([2,4,6]) == 4'
# Keep timing markers out of the actual YAML export.
export_intent() { conda env export --from-history > environment.yml; }
step export export_intent
step deactivate conda deactivate
step recreate conda env create -n sg-copy -f environment.yml -y
step run_copy conda run -n sg-copy python -c 'import training_math as m, training_text as t; assert m.__version__ == "1.1"; assert m.mean([2,4,6]) == 4; assert t.normalize(" ok ") == "OK"'
step remove_package conda remove -n sg-copy training-text -y
step verify_removal conda run -n sg-copy python -c 'import importlib.util, training_math; assert importlib.util.find_spec("training_text") is None; assert training_math.total([3,4]) == 7'
step remove_copy conda env remove -n sg-copy -y
step remove_proof conda env remove -n sg-proof -y
test ! -e /home/learner/conda-envs/sg-copy/conda-meta/history
test ! -e /home/learner/conda-envs/sg-proof/conda-meta/history
printf 'CONDA_REAL_OFFLINE_CREATE_ACTIVATE_INSTALL_UPDATE_EXPORT_RECREATE_REMOVE_OK\n'
