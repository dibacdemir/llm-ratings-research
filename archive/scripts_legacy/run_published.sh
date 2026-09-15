#!/bin/bash
# The whole published-norms pipeline, in the order it has to happen.
#
#   scripts/run_published.sh --check      verify prompts only, launch nothing
#   scripts/run_published.sh              check, then submit the sweep
#   scripts/run_published.sh --pages      rebuild the pages from what is on disk
#
# The check runs first and a failure stops the submission, because every
# expensive mistake this project has hit -- a placeholder left unfilled, a
# stimulus that never reached the model, a scale the prompt never names --
# is visible in the prompt string and invisible in the summary numbers.

set -euo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"

MODELS_SMALL="Qwen/Qwen2.5-1.5B-Instruct Qwen/Qwen2.5-3B-Instruct meta-llama/Llama-3.2-3B-Instruct google/gemma-3-1b-it"
MODELS_MID="Qwen/Qwen2.5-7B-Instruct meta-llama/Meta-Llama-3.1-8B-Instruct allenai/OLMo-3-7B-Instruct mistralai/Ministral-8B-Instruct-2410"
MODELS_32B="Qwen/Qwen2.5-32B-Instruct"
MODELS_27B="google/gemma-3-27b-it"
LIMIT=${LIMIT:-1000}

# The task list comes from the data, never from a list typed here, so a dataset
# the collaborators add or fix is picked up without editing this file.
TASKS=$("$PY" - <<'PYEOF'
import sys
sys.path.insert(0, "scripts")
from show_prompts import wired_tasks
import os
print(" ".join("%s:%s" % (t, os.environ.get("LIMIT", "1000"))
               for t, _c, _i in wired_tasks()))
PYEOF
)
N=$(wc -w <<< "$TASKS")

echo "== 0. encoding =="
# Cheap, and the failure it catches is invisible downstream: a model reading
# "canâ€™t" is not being asked the question the humans answered.
"$PY" scripts/check_encoding.py --sources published || true

echo
echo "== 1. prompts =="
echo "$N wired published datasets"
"$PY" scripts/show_prompts.py --check --items 3
for m in Qwen/Qwen2.5-7B-Instruct google/gemma-3-27b-it; do
    printf '   through %-34s ' "$m"
    "$PY" scripts/show_prompts.py --check --items 3 --model "$m" 2>/dev/null | tail -1
done

if [ "${1:-}" = "--check" ]; then
    echo
    echo "Checked only. Full text of any dataset:"
    echo "   $PY scripts/show_prompts.py --task <name> --model <hf-id>"
    exit 0
fi

if [ "${1:-}" = "--pages" ]; then
    exec scripts/refresh_pages.sh
fi

echo
echo "== 2. submitting =="
sub () { SKIP_DIST=1 ${3:-} MODELS="$2" TASKS="$TASKS" sbatch --job-name="$1" scripts/run_sweep.sh; }
sub pub-sm  "$MODELS_SMALL"
sub pub-mid "$MODELS_MID"
sub pub-32b "$MODELS_32B"
BATCH_SIZE=8 sub pub-27b "$MODELS_27B"

echo
echo "== 3. after they finish =="
echo "   the jobs rebuild the pages themselves; then open"
echo "   scripts/refresh_pages.sh --serve"
