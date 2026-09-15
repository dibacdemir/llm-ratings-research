#!/bin/bash
#SBATCH --job-name=sweep
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=12:00:00
#SBATCH --mem=200G
#SBATCH --cpus-per-task=16
#SBATCH --output=result/logs/%x-%j.out
# separate file: pointing --error at the same path lets SLURM's two buffered
# streams overwrite each other, which produces log lines that never existed
#SBATCH --error=result/logs/%x-%j.err
#
# models x tasks, with the prompt format chosen per pair by --auto-format.
#
#   MODELS="a b" TASKS="t1 t2:4000" sbatch pipeline/run_sweep.sh
#
# Weights are spread over two caches (the scratch one and the group one), so
# HF_HOME is resolved per model instead of being hard-coded -- guessing wrong
# costs a GPU allocation and a confusing "no model.safetensors" error.

set -uo pipefail
export HF_HUB_OFFLINE=1
CACHES=${CACHES:-"/home/phan3/orcd/scratch/huggingface /orcd/data/evelina9/001/USERS/phan3/hf_cache"}
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
REPO=${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
BATCH_SIZE=${BATCH_SIZE:-32}
LIMIT=${LIMIT:-3000}
N_SPLITS=${N_SPLITS:-2000}
ALIGN_BOOT=${ALIGN_BOOT:-2000}

cd "$REPO" || exit 1
mkdir -p result/logs
[ -f pipeline/run_expected_rating.py ] || { echo "error: REPO=$REPO is wrong" >&2; exit 1; }

find_cache () {  # echo the cache holding ALL of $1's weight shards, or nothing
    for c in $CACHES; do
        if HF_HOME=$c PYTHONPATH=pipeline "$PY" -m llm_ratings.cache "$1" \
               >/dev/null 2>&1; then
            echo "$c"; return
        fi
    done
}

MODELS=${MODELS:?set MODELS="org/name ..."}
TASKS=${TASKS:?set TASKS="task[:limit] ..."}
echo "repo   $REPO"
echo "models $MODELS"
echo "tasks  $TASKS"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null
echo

failed=()
for M in $MODELS; do
    C=$(find_cache "$M")
    if [ -z "$C" ]; then
        echo "!! no cache holds $M -- skipped"; failed+=("$M/nocache"); continue
    fi
    export HF_HOME=$C
    for spec in $TASKS; do
        task=${spec%%:*}
        lim=$LIMIT
        [ "$spec" != "$task" ] && lim=${spec##*:}
        echo "=============================================================="
        echo "[$(date +%H:%M:%S)] $M / $task (limit $lim, cache $(basename "$C"))"
        echo "=============================================================="
        O="result/$(basename "$M")/${task}__autofmt.jsonl"
        "$PY" pipeline/run_expected_rating.py --task "$task" --model "$M" \
            --out "$O" --limit "$lim" \
            --batch-size "$BATCH_SIZE" --overwrite \
            || { failed+=("$M/$task/score"); continue; }
        "$PY" pipeline/analyze_run.py "$O"
        # SKIP_DIST=1 when the metric has not been chosen yet: the .jsonl holds
        # the full PMFs, so any distributional statistic can be computed later
        # on CPU without re-running the model.
        if [ "${SKIP_DIST:-0}" != "1" ]; then
            "$PY" pipeline/run_dist_eval.py --ratings "$O" --n-splits "$N_SPLITS" \
                --align-boot "$ALIGN_BOOT" --max-items 3000 \
                || failed+=("$M/$task/dist")
        fi
        echo
    done
done

echo "=============================================================="
if [ ${#failed[@]} -eq 0 ]; then echo "SWEEP DONE - all ok"
else echo "SWEEP DONE - FAILED: ${failed[*]}"; fi

# Rebuild the pages so result/inspector.html and result/report.html are current
# the moment the job ends -- otherwise a browser refresh shows stale data,
# because both pages carry their data inline. Set NO_PAGES=1 to skip.
if [ "${NO_PAGES:-0}" != "1" ]; then
    echo
    echo "== refreshing pages =="
    pipeline/refresh_pages.sh 2>&1 | grep -E "^wrote|^Open|html" || echo "page refresh failed"
fi
