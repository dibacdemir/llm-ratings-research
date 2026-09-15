#!/bin/bash
#SBATCH --job-name=checked
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=12:00:00
#SBATCH --mem=200G
#SBATCH --cpus-per-task=16
#SBATCH --output=result/logs/%x-%j.out
#SBATCH --error=result/logs/%x-%j.out
# A sweep that refuses to start until the model's tokenizer and logit reading
# have been checked on this GPU: option digits must be single tokens, padding
# must not leak into the read, accented stimuli must survive the tokenizer.
# The checks are cheap; a sweep built on a mis-read digit is not.
#
#   MODELS="Qwen/Qwen2.5-7B-Instruct" sbatch --job-name=q7 pipeline/run_checked.sh
set -uo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
cd /orcd/data/evelina9/001/USERS/phan3/llm-ratings-research
export PYTHONPATH=pipeline
[ -n "${MODELS:-}" ] || { echo "MODELS is required"; exit 2; }
if [ -z "${TASKS:-}" ]; then
    TASKS=$(LIMIT="${LIMIT:-1000}" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, "pipeline")
from show_prompts import wired_tasks
print(" ".join("%s:%s" % (t, os.environ["LIMIT"]) for t, _c, _i in wired_tasks(("published","surveyor","mturk"))))
PYEOF
)
fi
export TASKS
for M in $MODELS; do
    echo "== checks: $M =="
    CACHE=$("$PY" -m llm_ratings.cache "$M" --where) || { echo "!! no cache holds $M"; exit 1; }
    export HF_HOME="$CACHE" HF_HUB_OFFLINE=1
    "$PY" pipeline/show_prompts.py --check --items 3 --sources published,surveyor,mturk --model "$M" \
        | tail -1 || { echo "!! prompt/tokenizer check failed for $M"; exit 1; }
    "$PY" pipeline/verify_scoring.py --task amouyal2024_plausibility --model "$M" --n-items 64 ${SKIP_FP32:+--skip-fp32} \
        || { echo "!! scoring verification failed for $M"; exit 1; }
    echo "== checks passed: $M =="
done
echo
SKIP_DIST=1 MODELS="$MODELS" TASKS="$TASKS" bash pipeline/run_sweep.sh
