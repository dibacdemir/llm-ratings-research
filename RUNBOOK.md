# Runbook

One command, five verbs.

```bash
conda activate compressibility

./ratings list                          # what datasets exist, which are scorable
./ratings check                         # read the prompts before spending GPU time
./ratings run --models "Qwen/Qwen2.5-7B-Instruct"
./ratings show --serve                  # rebuild the pages, serve them
./ratings serve --stop                  # stop the server
```

## Adding a dataset

One folder under `data/<level>/`. No registry, no list to edit.

```
data/<level>/<name>/
    instruction.txt      the wording, <<{word}>> (or <<{sentence}>>) where the stimulus goes
    ratings.csv          unit,mean,std,n,individual_ratings
    metadata.json        {"task": "<name>", "source": "published|surveyor|mturk", "level": "<level>"}
```

Levels: `subword`, `lexical_semantics`, `syntax`, `sentence_semantics`,
`pragmatics`, `discourse`, `other`. Then:

```bash
./ratings check <name>                      # the exact prompt a model will receive
python pipeline/human_reliability.py        # split-half reliability into metadata.json
python pipeline/build_index.py              # data/INDEX.csv
./ratings run --models ...                  # the new dataset is included automatically
```

`pipeline/selftest_end_to_end.sh` creates a dataset, scores it with a real
model and deletes it, so this stays true as the code changes.

## The verbs

**`list`** — every dataset in `data/`, which can be scored, and the reason for
each that cannot (no discrete scale, more than one placeholder field, broken
encoding).

**`check`** — encoding first, then a complete prompt per dataset with the
assertions that matter: the placeholder is filled, the stimulus appears
verbatim, the prompt names the scale, and the text survives the tokenizer.
`./ratings check <name>` prints the full prompt for one dataset;
`--model <hf-id>` wraps it in that model's chat template.

**`run`** — one Slurm job per model (`pipeline/run_checked.sh`). Each job runs
the prompt checks and `pipeline/verify_scoring.py` for that model and stops if
either fails, then scores every scorable dataset and rebuilds the pages.
`--tasks "a b"` narrows, `--limit N` caps items per dataset (default 1000),
`--local` runs here instead of Slurm. Environment knobs for big models:
`BATCH_SIZE=8`, `SKIP_FP32=1` (skips the float32 comparison in the gate).

**`show`** — rebuilds `result/inspector.html` and `result/report.html`
(`pipeline/refresh_pages.sh`). `--serve` also starts the server on port 8000
and prints the `ssh -L` line.

**`serve`** — start or stop the local server without rebuilding.

## The pages

- **Item Inspector** — every task by level on the left; for the selected task,
  the dataset card (size, scale, reliability, who decided the level), the exact
  prompt, every model's numbers with the human row and ceiling, and the items.
  Self-contained: publishable as one file, all item data compressed inside.
- **Report** — every run together.

Both change only when rebuilt; `run` rebuilds at the end of every sweep.

## The human data

```bash
python pipeline/human_reliability.py    # split-half reliability, into data/*/metadata.json
python pipeline/build_metadata.py       # metadata/catalog.csv and the figures
```

---

**Read `option_mass` before believing a number.** It is how much probability
sat on the valid answers before renormalising; below ~0.9 the model did not
answer with a digit. The comparison table also flags a model that answered
almost identically every time (`!`) or used only the two ends of a graded
scale (`⇅`).

Caveats that survive the data being correct — edwards2024 asks for difficulty,
not transparency; gatti2024's human column is a best-worst score, not a rating —
live in `pipeline/llm_ratings/task_meta.NOTES` and are printed beside the task.
