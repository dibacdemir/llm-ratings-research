# pipeline/

Everything is reachable through `./ratings` at the repo root. This file says
what each piece is, for when you need to go one level down.

## The skeleton

`ratings` calls these, in this order, and nothing else is required to add a
dataset or to run a sweep.

| | |
|---|---|
| `llm_ratings/` | the library: finding datasets, building prompts, reading logits, task metadata |
| `check_encoding.py` | text decoded with the wrong codec, across `data/` |
| `show_prompts.py` | the complete prompt per dataset, plus the assertions `run` refuses to start without |
| `check_tasks.py` | what exists, what is scorable, what blocks the rest |
| `run_checked.sh` | the Slurm job for one model: prompt checks, `verify_scoring.py`, then `run_sweep.sh` |
| `run_sweep.sh` | score many datasets with one model, then rebuild the pages |
| `run_expected_rating.py` | score one model on one dataset |
| `verify_scoring.py` | is the logit reading correct for this model: padding, dtype, greedy vs sampling |
| `build_report_data.py`, `build_explorer_data.py`, `build_prompt_data.py` | runs and datasets to JSON |
| `pack_inspector_data.py` | every pair's items, compressed, so the standalone page carries them |
| `build_report.py` | JSON + template to a self-contained page |
| `refresh_pages.sh` | all the builders, then optionally serve |
| `serve.sh` | the local server on port 8000 |
| `selftest_end_to_end.sh` | proves a new dataset needs only one folder |

## The human data

| | |
|---|---|
| `human_reliability.py` | split-half reliability of every dataset's raters, into `data/*/metadata.json` |
| `build_index.py` | `data/INDEX.csv` from the metadata files |
| `build_metadata.py` | `metadata/`: the catalog and the figures |

## The library

| | |
|---|---|
| `data.py` | walks `data/<level>/<task>/`, parses the norm CSVs, resolves the response scale |
| `prompt.py` | fills `<<{...}>>` with the stimulus in double quotes, applies the chat template |
| `hf_backend.py` | one forward pass, probability on the scale digits, renormalised |
| `task_meta.py` | per-task level, source, caveats, reliability, and the tasks that must not be scored |
| `facts.py` | a cache of per-CSV facts so page rebuilds do not re-read 291 files |
| `dist.py`, `cache.py` | Ted's distribution statistics; locating model weights in the shared caches |

## Analyses that stand on their own

| | |
|---|---|
| `analyze_run.py` | three questions about a single run (used by the report builder) |
| `run_dist_eval.py` | do model and human *distributions* match, not just their means (slow; `SKIP_DIST=1` skips it in sweeps) |

Retired scripts are in `archive/scripts_legacy/`.

## Adding a dataset

One folder, no code:

```
data/<level>/<name>/instruction.txt     <<{word}>> where the stimulus goes
data/<level>/<name>/ratings.csv         unit,mean,std,n,individual_ratings
data/<level>/<name>/metadata.json       {"task": "<name>", "source": "...", "level": "<level>"}
```

`individual_ratings` is what each rater answered. With it, model and human
*distributions* can be compared and the raters' reliability is known. Without
it, only the item means can — still a real comparison; the pages then show the
model's distribution alone.

Run `pipeline/selftest_end_to_end.sh` to see this proved end to end.
