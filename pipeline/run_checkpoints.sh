#!/bin/bash
#SBATCH --job-name=ckpt
#SBATCH --partition=pi_evelina9
#SBATCH --gres=gpu:a100:1
#SBATCH --time=06:00:00
#SBATCH --mem=120G
#SBATCH --cpus-per-task=8
#SBATCH --output=result/logs/%x-%j.out
#SBATCH --error=result/logs/%x-%j.out
# Training dynamics: score one OLMo-2-7B pre-training checkpoint on every task.
#
# Base models do not follow the instruction, so the reading differs from the
# main sweep: no chat template, and the prompt ends with "\nAnswer: " (the
# trailing space matters -- OLMo's tokenizer emits the space as its own token,
# and without it the first token is a space rather than a digit). Chosen by
# probe_base_reading.sh: option_mass 0.97-1.00 on the final base model, and
# rho within ~0.05 of the instruct model on the tasks probed.
#
# Results go to result/OLMo-2-1124-7B@<revision>/<task>__autofmt.jsonl so the
# pages and the pilot scripts see each checkpoint as its own model.
#
#   REVS="stage1-step150-tokens1B stage1-step600-tokens3B" sbatch --array=0-1%2 pipeline/run_checkpoints.sh
set -uo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
cd /orcd/data/evelina9/001/USERS/phan3/llm-ratings-research
export PYTHONPATH=pipeline HF_HOME=/orcd/data/evelina9/001/USERS/phan3/hf_cache
MODEL=${MODEL:-allenai/OLMo-2-1124-7B}
read -ra _revs <<< "$REVS"
REV="${_revs[${SLURM_ARRAY_TASK_ID:-0}]}"
LIMIT=${LIMIT:-1000}
TASKS=$("$PY" - <<'PYEOF'
import sys; sys.path.insert(0, "pipeline")
from show_prompts import wired_tasks
print(" ".join(t for t, _c, _i in wired_tasks(("published","surveyor","mturk"))))
PYEOF
)
OUTDIR="result/$(basename $MODEL)@$REV"
echo "== $MODEL @ $REV -> $OUTDIR  ($(wc -w <<< "$TASKS") tasks) =="
fail=0
for T in $TASKS; do
    OUT="$OUTDIR/${T}__autofmt.jsonl"
    [ -s "$OUT" ] && continue
    "$PY" pipeline/run_expected_rating.py --task "$T" --model "$MODEL" --revision "$REV" \
        --no-chat --answer-prefix $'\nAnswer: ' --limit "$LIMIT" --batch-size "${BATCH_SIZE:-16}" \
        --out "$OUT" --overwrite 2>&1 | grep -E "^wrote|Error|error:" | head -2 \
        || { echo "!! failed: $T"; fail=$((fail+1)); }
done
N=$(ls "$OUTDIR"/*__autofmt.jsonl 2>/dev/null | wc -l)
echo "== $REV: $N results, $fail failures =="
if [ "$N" -ge "$(wc -w <<< "$TASKS")" ]; then
    # only this revision's snapshot; other revisions of the model are separate snapshot dirs
    SNAP=$(HF_HOME=$HF_HOME "$PY" -c "
from huggingface_hub import snapshot_download; import os
print(snapshot_download('$MODEL', revision='$REV', allow_patterns=['config.json']))" 2>/dev/null)
    [ -d "$SNAP" ] && { echo "removing weights $SNAP"; rm -rf "$SNAP"; }
    echo "CKPT DONE - all ok"
else
    echo "CKPT DONE - INCOMPLETE"
fi
