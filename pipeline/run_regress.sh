#!/bin/bash
#SBATCH --job-name=regress
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=08:00:00
#SBATCH --mem=120G
#SBATCH --cpus-per-task=16
#SBATCH --output=result/logs/%x-%j.out
#SBATCH --error=result/logs/%x-%j.out
# Regression approach for one model over every eligible task (see regress_pilot.py).
#   MODEL_LIST="a b c" sbatch --array=0-2%2 pipeline/run_regress.sh
set -uo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
cd /orcd/data/evelina9/001/USERS/phan3/llm-ratings-research
export PYTHONPATH=pipeline
LAB_CACHE=/orcd/data/evelina9/001/USERS/phan3/hf_cache
read -ra _all <<< "$MODEL_LIST"; M="${_all[${SLURM_ARRAY_TASK_ID:-0}]}"
CACHE=$("$PY" -m llm_ratings.cache "$M" --where 2>/dev/null); DL=0
if [ -z "$CACHE" ]; then
    HF_HOME=$LAB_CACHE "$PY" -c "
from huggingface_hub import snapshot_download
snapshot_download('$M', allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.tiktoken','*.jinja','*.py'], ignore_patterns=['onnx/*','consolidated*','original/*'])" || exit 1
    CACHE=$("$PY" -m llm_ratings.cache "$M" --where) || exit 1; DL=1
fi
export HF_HOME="$CACHE" HF_HUB_OFFLINE=1
"$PY" -u pipeline/regress_pilot.py --model "$M" --tasks "$(cat analysis/regress_pilot/tasks_n200.txt)" --n 200,300 --resamples 10 --out analysis/regress
RC=$?
if [ "$RC" -eq 0 ] && [ "$DL" = 1 ] && [ "$CACHE" = "$LAB_CACHE" ]; then rm -rf "$LAB_CACHE/hub/models--${M//\//--}"; echo "weights removed"; fi
echo "REGRESS DONE rc=$RC"
