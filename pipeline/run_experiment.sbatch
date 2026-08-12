#!/bin/bash
#SBATCH --job-name=llm-ratings
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G

# No --partition here on purpose: partition names differ per cluster and the
# right one changes with queue load. Discover with `sinfo -s` and pass it at
# submit time, where it overrides anything in this file.
#
# Submit from the REPO ROOT, not from pipeline/:
#   sbatch -p mit_normal_gpu pipeline/run_experiment.sbatch qwen17b dentella2023_grammaticality
#   EXTRA="--limit 300" sbatch -p mit_normal_gpu pipeline/run_experiment.sbatch qwen17b all
#   MODEL=... DATASET=... EXTRA="--limit 500" sbatch -p <partition> pipeline/run_experiment.sbatch
#
# SCRATCH_DIR must point at real scratch space. Home is 20 GB on Engaging and a
# single 8B model is ~16 GB, so defaulting to home would fill the quota and fail
# the download halfway. This script refuses to run rather than do that.

set -euo pipefail

MODEL="${1:-${MODEL:-llama8b}}"
DATASET="${2:-${DATASET:-all}}"
EXTRA="${EXTRA:-}"

# Code + datasets live in pool, model weights in scratch.
POOL_DIR="${POOL_DIR:-$SLURM_SUBMIT_DIR}"
SCRATCH_DIR="${SCRATCH_DIR:-}"

if [[ -z "$SCRATCH_DIR" ]]; then
    echo "ERROR: SCRATCH_DIR is unset. Find your scratch/pool path and export it, e.g." >&2
    echo "  export SCRATCH_DIR=/orcd/pool/<num>/users/\$USER" >&2
    echo "Do not let model weights land in \$HOME (20 GB quota)." >&2
    exit 1
fi
if [[ ! -d "$SCRATCH_DIR" ]]; then
    echo "ERROR: SCRATCH_DIR=$SCRATCH_DIR does not exist." >&2
    exit 1
fi

export HF_HOME="$SCRATCH_DIR/hf"
export HF_HUB_CACHE="$HF_HOME/hub"
export TRANSFORMERS_CACHE="$HF_HOME/hub"
export TOKENIZERS_PARALLELISM=false
mkdir -p "$HF_HUB_CACHE" "$POOL_DIR/logs" "$POOL_DIR/results"

# Gated repos (Llama) need a token. Keep it in ~/.bashrc as HF_TOKEN rather than
# `huggingface-cli login`, whose cache lives under HF_HOME on scratch and is
# purged along with everything else there.
if [[ -n "${HF_TOKEN:-}" ]]; then
    export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
fi

cd "$POOL_DIR"

# Engaging ships miniforge, not anaconda; keep both for portability.
module load miniforge 2>/dev/null || module load anaconda 2>/dev/null || true
eval "$(conda shell.bash hook)" 2>/dev/null || true
conda activate "${CONDA_ENV:-llm-ratings}" 2>/dev/null \
    || source activate "${CONDA_ENV:-llm-ratings}" 2>/dev/null \
    || true

# Fail here rather than 40 minutes into a GPU allocation with a bad env.
python -c "import torch, transformers, numpy, scipy" || {
    echo "ERROR: conda env '${CONDA_ENV:-llm-ratings}' is missing or incomplete." >&2
    echo "  module load miniforge && conda create -n llm-ratings python=3.11 -y" >&2
    echo "  conda activate llm-ratings && pip install torch transformers accelerate numpy scipy tqdm" >&2
    exit 1
}

echo "host=$(hostname) model=$MODEL dataset=$DATASET"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

python pipeline/experiments.py \
    --model "$MODEL" \
    --dataset "$DATASET" \
    --output-dir results \
    --batch-size "${BATCH_SIZE:-16}" \
    $EXTRA

MODEL_SLUG=$(python -c "
import sys; sys.path.insert(0, 'pipeline')
import experiments
print(experiments.slugify(experiments.MODEL_ALIASES.get('$MODEL', '$MODEL')))
")

python pipeline/reliability_correlation.py \
    --dataset "$DATASET" \
    --results "results/$MODEL_SLUG" \
    --quiet
