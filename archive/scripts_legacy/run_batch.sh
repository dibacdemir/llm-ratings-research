#!/bin/bash
#SBATCH --job-name=llm-ratings
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=12:00:00
#SBATCH --mem=200G
#SBATCH --cpus-per-task=16
#SBATCH --output=result/logs/%x-%j.out
#SBATCH --error=result/logs/%x-%j.out
#
# Score one model on several tasks, then run the distribution eval on each.
# Results land in result/<model name>/<task>.jsonl (+ .meta.json, .dist.csv,
# .summary.json); the SLURM log goes to result/logs/.
#
#   sbatch scripts/run_batch.sh <model> [task[:limit] ...]
#
# Run it directly (no SLURM) with the same arguments to test on a node you
# already hold interactively.

set -uo pipefail

# The scratch cache is the one that actually holds weights (the pool cache has
# configs only). Set unconditionally: sbatch propagates the submitting shell's
# environment, and ~/.bashrc exports the pool path, so a `${HF_HOME:-...}`
# default would silently lose to it and the job would die on a missing shard.
# Override with LLM_RATINGS_HF_HOME, not HF_HOME.
export HF_HOME=${LLM_RATINGS_HF_HOME:-/home/phan3/orcd/scratch/huggingface}
export HF_HUB_OFFLINE=1

PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
# Under sbatch the script is copied to /var/spool/slurmd, so BASH_SOURCE does
# not point at the repo — use the submit directory there.
if [ -z "${REPO:-}" ]; then
    if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
        REPO=$SLURM_SUBMIT_DIR
    else
        REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
    fi
fi
if [ ! -f "$REPO/scripts/run_expected_rating.py" ]; then
    echo "error: REPO=$REPO is not the repo (no scripts/run_expected_rating.py)" >&2
    echo "       submit from the repo root, or pass REPO=/path/to/repo" >&2
    exit 1
fi
BATCH_SIZE=${BATCH_SIZE:-32}
N_SPLITS=${N_SPLITS:-2000}
ALIGN_BOOT=${ALIGN_BOOT:-2000}
MAX_DIST_ITEMS=${MAX_DIST_ITEMS:-3000}   # cap the O(n) bootstrap stage

MODEL=${1:?usage: run_batch.sh <model> [task[:limit] ...]}
shift
TASKS=("$@")
if [ ${#TASKS[@]} -eq 0 ]; then
    TASKS=(dentella2023_grammaticality
           amouyal2024_plausibility
           diveica2023_socialness
           edwards2024_spelling_to_pronunciation_transparency:4000
           lancaster2020_visual:4000)
fi

cd "$REPO" || exit 1
mkdir -p result/logs

# Fail fast if the weights are not actually in the cache: resolving the shards
# costs nothing, loading the model and discovering it costs a GPU allocation.
# llm_ratings.cache walks the shard index -- a cache can hold the index and
# none of the shards, which is exactly how the scratch copy of Qwen2.5-32B is.
PYTHONPATH=scripts "$PY" -m llm_ratings.cache "$MODEL" || {
    echo "preflight: no complete weights for $MODEL under HF_HOME=$HF_HOME" >&2
    exit 1
}

echo "repo    $REPO"
echo "HF_HOME $HF_HOME"
echo "model   $MODEL"
echo "tasks   ${TASKS[*]}"
echo "python  $PY"
echo "node    $(hostname)  ${SLURM_JOB_ID:+job $SLURM_JOB_ID}"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null
echo

failed=()
for spec in "${TASKS[@]}"; do
    task=${spec%%:*}
    limit=""
    [ "$spec" != "$task" ] && limit="--limit ${spec##*:}"
    echo "=============================================================="
    echo "[$(date +%H:%M:%S)] $task $limit"
    echo "=============================================================="
    # shellcheck disable=SC2086
    "$PY" scripts/run_expected_rating.py \
        --task "$task" --model "$MODEL" \
        --batch-size "$BATCH_SIZE" --overwrite $limit || { failed+=("$task/score"); continue; }

    out="result/$(basename "$MODEL")/$task.jsonl"
    "$PY" scripts/run_dist_eval.py --ratings "$out" \
        --n-splits "$N_SPLITS" --align-boot "$ALIGN_BOOT" \
        --max-items "$MAX_DIST_ITEMS" || failed+=("$task/dist")
    echo
done

echo "=============================================================="
if [ ${#failed[@]} -eq 0 ]; then
    echo "[$(date +%H:%M:%S)] all tasks done"
else
    echo "[$(date +%H:%M:%S)] FAILED: ${failed[*]}"
    exit 1
fi
