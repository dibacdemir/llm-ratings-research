#!/bin/bash
#SBATCH --job-name=probe-base
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=04:00:00
#SBATCH --mem=120G
#SBATCH --cpus-per-task=8
#SBATCH --output=result/logs/%x-%j.out
#SBATCH --error=result/logs/%x-%j.out
# How should a *base* (not instruction-tuned) model be read, without few-shot?
# Score a few tasks with several answer prefixes, on the final OLMo-2-7B base
# and on one mid-training checkpoint, and compare option_mass and rho.
# Results land in result/_probe_base/<model>[@revision]__<prefix>/<task>.jsonl
set -uo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
cd /orcd/data/evelina9/001/USERS/phan3/llm-ratings-research
export PYTHONPATH=pipeline HF_HOME=/orcd/data/evelina9/001/USERS/phan3/hf_cache
MODEL=allenai/OLMo-2-1124-7B
TASKS="amouyal2024_plausibility diveica2023_socialness acceptability_replication_959 coherence_survey_list1_main presup_survey_1_acd_july_2012 edwards2024_spelling_to_pronunciation_transparency"
declare -A PREFIX=( [answer_sp]=$'\nAnswer: ' [rating_sp]=$'\nRating: ' )
for REV in "" stage1-step150000-tokens630B; do
  for tag in answer_sp rating_sp; do
    for T in $TASKS; do
      OUT="result/_probe_base/$(basename $MODEL)${REV:+@$REV}__${tag}/${T}.jsonl"
      echo "== $(date +%H:%M) ${REV:-final} prefix=$tag task=$T =="
      "$PY" pipeline/run_expected_rating.py --task "$T" --model "$MODEL" ${REV:+--revision "$REV"} \
          --no-chat --answer-prefix "${PREFIX[$tag]}" --limit 200 --batch-size 16 \
          --out "$OUT" --overwrite 2>&1 | grep -E "^task|wrote|Error|error" | head -3
    done
  done
done
echo "PROBE DONE"
