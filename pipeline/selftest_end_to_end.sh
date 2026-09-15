#!/bin/bash
# Prove the claim the runbook makes: a dataset is two files and nothing else.
#
# Creates a throwaway dataset, asks the pipeline to find it, read its prompt and
# score it with a real model, then removes it. If this passes, adding a real
# dataset needs no code change either.
#
#   pipeline/selftest_end_to_end.sh              needs a GPU for the scoring step
#   pipeline/selftest_end_to_end.sh --no-model   everything except the scoring

set -euo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"
NAME=_selftest_brightness
DIR=data/other/$NAME
CSV=$DIR/ratings.csv
INS=$DIR/instruction.txt
cleanup () { rm -rf "$DIR" result/_selftest_run.jsonl result/_selftest_run.jsonl.meta.json; }
trap cleanup EXIT

mkdir -p "$(dirname "$CSV")" "$(dirname "$INS")"
cat > "$CSV" <<'CSVEOF'
unit,mean,std,n,individual_ratings
sunlight,6.10,0.99,10,"[7, 6, 7, 5, 6, 7, 6, 5, 7, 5]"
cave,1.80,0.79,10,"[2, 1, 2, 3, 1, 2, 1, 2, 3, 1]"
café décor,4.20,1.03,10,"[4, 5, 3, 4, 5, 4, 3, 5, 4, 5]"
twilight,3.40,0.97,10,"[3, 4, 2, 3, 5, 3, 4, 3, 2, 5]"
CSVEOF
printf '{"task": "%s", "source": "published", "level": "other", "language": "english"}\n' "$NAME" > "$DIR/metadata.json"
cat > "$INS" <<'INSEOF'
How bright is the thing this word refers to?
Please rate the word <<{word}>> on a scale from 1 (very dark) to 7 (very bright). Answer with one digit.
INSEOF

fail () { echo "FAIL: $1"; exit 1; }

echo "1. discovered without being registered anywhere"
"$PY" - <<'PYEOF' || fail "the task was not discovered"
import sys; sys.path.insert(0, "pipeline")
from llm_ratings import data
names = [t for t, *_ in data.list_tasks()]
assert "_selftest_brightness" in names, names[:3]
print("   found among %d datasets" % len(names))
PYEOF

echo "2. scale read from the instruction, not guessed"
"$PY" - <<'PYEOF' || fail "scale resolution"
import sys; sys.path.insert(0, "pipeline")
from llm_ratings import data, prompt
loc = data.find_task("_selftest_brightness")
lo, hi = data.resolve_scale(prompt.read_instructions(loc["instructions"]),
                            data.load_items(loc["csv"]))
assert (lo, hi) == (1, 7), (lo, hi)
print("   scale %d-%d" % (lo, hi))
PYEOF

echo "3. prompt builds, accents survive"
"$PY" pipeline/show_prompts.py --check --task _selftest_brightness --sources all --items 4 \
    | tail -1 || fail "prompt checks"

if [ "${1:-}" = "--no-model" ]; then
    echo; echo "PASS (scoring step skipped)"; exit 0
fi

echo "4. a real model scores it"
MODEL=${SELFTEST_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}
CACHE=$("$PY" -m llm_ratings.cache "$MODEL" --where 2>/dev/null) \
    || fail "no local cache holds $MODEL"
HF_HOME="$CACHE" HF_HUB_OFFLINE=1 "$PY" pipeline/run_expected_rating.py \
    --task _selftest_brightness --model "$MODEL" \
    --out result/_selftest_run.jsonl --overwrite >/dev/null || fail "scoring"
"$PY" - <<'PYEOF' || fail "the scored output is not usable"
import json
rows = [json.loads(l) for l in open("result/_selftest_run.jsonl")]
assert len(rows) == 4, len(rows)
for r in rows:
    assert len(r["probs"]) == 7, r["probs"]
    assert abs(sum(r["probs"]) - 1) < 1e-6
assert any(r["unit"] == "café décor" for r in rows), "accented unit lost"
lit = {r["unit"]: sum((i + 1) * p for i, p in enumerate(r["probs"])) for r in rows}
print("   expected ratings: " + ", ".join("%s %.2f" % kv for kv in lit.items()))
PYEOF

echo
echo "PASS: a csv and an instruction file are all a new dataset needs."
