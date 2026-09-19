#!/bin/bash
#SBATCH --job-name=checked
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=12:00:00
#SBATCH --mem=200G
#SBATCH --cpus-per-task=16
#SBATCH --output=result/logs/%x-%j.out
#SBATCH --error=result/logs/%x-%j.out
# One model, start to finish, on one GPU:
#
#   1. download the weights into the lab cache if no cache has them
#   2. check the tokenizer and the logit reading on this GPU (option digits
#      single tokens, padding not leaking into the read, accented stimuli
#      surviving) -- refuse to score if either fails
#   3. score every scorable dataset (run_sweep.sh)
#   4. if every dataset was written, delete the weights from the lab cache
#      (results are a few hundred KB per task and are kept; a 7B model
#      re-downloads in minutes). Weights in other caches are never touched.
#
#   MODELS="Qwen/Qwen2.5-7B-Instruct" sbatch --job-name=q7 pipeline/run_checked.sh
#
# Several models with at most N GPUs at once, as a job array:
#
#   MODEL_LIST="a b c d" sbatch --array=0-3%2 pipeline/run_checked.sh
#
# Knobs: BATCH_SIZE=8 and SKIP_FP32=1 for models over ~12B, KEEP_WEIGHTS=1
# to skip step 4, NO_PAGES=1 (the default here) to skip the page rebuild --
# run ./ratings show once when a batch is done instead.
set -uo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
cd /orcd/data/evelina9/001/USERS/phan3/llm-ratings-research
export PYTHONPATH=pipeline
LAB_CACHE=/orcd/data/evelina9/001/USERS/phan3/hf_cache

if [ -n "${SLURM_ARRAY_TASK_ID:-}" ] && [ -n "${MODEL_LIST:-}" ]; then
    read -ra _all <<< "$MODEL_LIST"
    MODELS="${_all[$SLURM_ARRAY_TASK_ID]}"
fi
[ -n "${MODELS:-}" ] || { echo "MODELS (or MODEL_LIST + --array) is required"; exit 2; }
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
N_TASKS=$(wc -w <<< "$TASKS")

for M in $MODELS; do
    echo "== weights: $M =="
    CACHE=$("$PY" -m llm_ratings.cache "$M" --where 2>/dev/null)
    DOWNLOADED=0
    if [ -z "$CACHE" ]; then
        echo "not cached; downloading to $LAB_CACHE"
        HF_HOME=$LAB_CACHE "$PY" - "$M" <<'PYEOF' || { echo "!! download failed for $M"; exit 1; }
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1],
                  allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model",
                                  "*.tiktoken", "*.jinja", "*.py"],
                  ignore_patterns=["onnx/*", "*fp16*", "*q4*", "*q8*", "*int8*",
                                   "consolidated*", "original/*"])
PYEOF
        CACHE=$("$PY" -m llm_ratings.cache "$M" --where) || { echo "!! download incomplete for $M"; exit 1; }
        DOWNLOADED=1
    fi
    export HF_HOME="$CACHE" HF_HUB_OFFLINE=1

    echo "== checks: $M =="
    "$PY" pipeline/show_prompts.py --check --items 3 --sources published,surveyor,mturk --model "$M" \
        | tail -1 || { echo "!! prompt/tokenizer check failed for $M"; exit 1; }
    "$PY" pipeline/verify_scoring.py --task amouyal2024_plausibility --model "$M" --n-items 64 ${SKIP_FP32:+--skip-fp32} \
        || { echo "!! scoring verification failed for $M"; exit 1; }
    echo "== checks passed: $M =="
    echo

    NO_PAGES=${NO_PAGES:-1} SKIP_DIST=1 MODELS="$M" TASKS="$TASKS" bash pipeline/run_sweep.sh
    RC=$?

    # step 4: only when every task was written, and only from the lab cache
    DIR="result/$(basename "$M")"
    N_OUT=$(ls "$DIR"/*__autofmt.jsonl 2>/dev/null | wc -l)
    if [ "$RC" -eq 0 ] && [ "$N_OUT" -ge "$N_TASKS" ] && [ "${KEEP_WEIGHTS:-0}" != "1" ] \
       && [ "$CACHE" = "$LAB_CACHE" ]; then
        SNAP="$LAB_CACHE/hub/models--${M//\//--}"
        echo "== $N_OUT/$N_TASKS results written; removing weights $SNAP =="
        rm -rf "$SNAP"
    else
        echo "== weights kept ($N_OUT/$N_TASKS results, rc=$RC, cache=$CACHE) =="
    fi
done
