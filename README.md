# LLM ratings research

Do LLMs reproduce human psycholinguistic norms? This repo pairs published rating
datasets with the code to score language models on the same items and compare
them to humans — at the level of both means and full response distributions.

## Layout

| Path | Contents |
| --- | --- |
| `pipeline/` | **The code.** Scoring, analysis, Slurm runner. See [`pipeline/README.md`](pipeline/README.md). |
| `norm_datasets/` | 20 published norm sources, one CSV per task: `unit, mean, std, n, individual_ratings`. |
| `instructions/` | One prompt template per dataset, with a `{word}` / `{sentence}` / `{expression}` placeholder. |
| `surveyor_norms/` | TedLab Prolific norms, 2023–2026. 100 datasets, same schema plus an `item_type` (test/filler) column. |
| `mturk_norms/` | TedLab MTurk norms, 2011–2021. 169 datasets (153 usable, 16 blocked on missing wording), same schema. |
| `presentation/` | Dataset catalog and figures. |
| `audit/` | Deep audit of the TedLab conversions (2026-08-19), the 2026-08-20 repair, blocked datasets, and remaining fixes. |

Run everything from the repo root:

```bash
python pipeline/experiments.py --list
```

## Quick start

```bash
module load miniforge && eval "$(conda shell.bash hook)" && conda create -n llm-ratings python=3.11 -y && conda activate llm-ratings
```

```bash
pip install torch transformers accelerate numpy scipy tqdm
```

Grab a GPU, then smoke test on the smallest dataset:

```bash
python pipeline/experiments.py --model qwen17b --dataset dentella2023_grammaticality --show-prompt
```

Check `scale_mass` in the output before trusting anything — near 1.0 means the
model answered with a rating digit; low means it answered with something else
and the numbers are noise. Full details in [`pipeline/README.md`](pipeline/README.md).

## What gets measured

Each item is scored in a **single forward pass**: the next-token distribution is
restricted to the rating-scale digits and renormalized, giving a probability
distribution over the scale plus an expected rating. No sampling, no generation.

That yields two levels of comparison:

- **Means** — does `model_expected` correlate with `human_mean`, relative to the
  ceiling set by human split-half reliability?
- **Distributions** — does the model *spread* its answers the way people do?

These can disagree sharply, which is the point of keeping trial-level human
responses rather than just published averages.

## Status

Working: 17 datasets in `norm_datasets/` with trial-level responses, scored
end-to-end on MIT Engaging.

Not yet wired up: the 269 TedLab datasets in `surveyor_norms/` and
`mturk_norms/` (audited and repaired 2026-08-20, see `audit/`; 16 mturk sets
remain blocked on missing wording). Same schema (surveyor adds an `item_type`
column), and each ships an `a_index.csv` carrying the rating scale and
instruction provenance, so the hardcoded registry in `pipeline/experiments.py`
could be replaced with auto-discovery. Note `std` in these two trees is sample
SD (ddof=1).
