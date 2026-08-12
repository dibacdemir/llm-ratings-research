# Pipeline

Runs LLMs over psycholinguistic norming datasets and compares model rating
distributions against human ones.

| File | Purpose |
| --- | --- |
| `experiments.py` | Dataset registry, prompt building, model scoring, distribution analysis. Writes per-item CSVs and per-dataset JSON summaries. |
| `reliability_correlation.py` | Split-half reliability (Spearman-Brown corrected) of the human norms, plus model-human correlation against that ceiling. |
| `run_experiment.sbatch` | Slurm wrapper. Submit from the repo root. |

Run everything **from the repo root**, not from inside `pipeline/`:

```bash
python pipeline/experiments.py --list
```

## How a model is scored

For each item the instruction template is filled with the item text and pushed
through the model in a **single forward pass**. The next-token distribution is
restricted to the digits of that dataset's rating scale and renormalized, giving
a PMF over the scale. The expected rating is `sum(k * p_k)`.

No sampling, no generation, no output parsing — one forward pass per item,
batched. Roughly 50–80 items/second for a 1.7B model on one GPU.

## `scale_mass` — read this before any result

`scale_mass` is the probability the model placed on the scale digits *before*
renormalizing. Renormalizing **always** yields a clean-looking distribution, so
this is the only signal that separates a real rating from noise.

- `~1.0` — the model answered with a digit. Results are meaningful.
- `< 0.5` — the model wanted to emit something else. The run prints a warning
  and dumps the top next-tokens so you can see what.

Check `min_scale_mass` too, not just the mean: a few broken items can hide
inside a healthy average.

## Known traps

**Reasoning models.** Qwen3 and friends open a `<think>` block, so the first
next-token is `<think>` and *zero* mass reaches the digits. The chat template is
called with `enable_thinking=False` by default, which fixes it. `--enable-thinking`
restores the default behaviour if you want to study it.

**muraki2023.** Its instruction is the only one of the 17 with no "answer with
one digit" directive, and it explicitly invites a prose answer ("or answer 'I
don't know the meaning of this expression'"). Qwen3-1.7B responds with `'The'` at
p≈0.998 and `scale_mass` collapses to 0.011. Workaround:

```bash
python pipeline/experiments.py --model qwen17b --dataset muraki2023_concreteness --answer-prefix "Answer: "
```

The cleaner fix is to add the digit directive to the instruction file so all 17
share one response format — but that edits a stimulus, so it is a research
decision, not a bug fix.

## Runnable datasets

Only datasets whose CSV carries `individual_ratings` (trial-level human
responses) support reliability and distribution analysis. 17 qualify:

```bash
python pipeline/experiments.py --list
```

`amouyal2024_plausibility` (1–7), `dentella2023_grammaticality` (0–1),
`diveica2023_socialness` (1–7), `edwards2024_spelling_to_pronunciation_transparency` (1–6),
`giurgea2025_motivation` (1–7), `muraki2023_concreteness` (1–5),
`lancaster2020_*` (0–5, 11 tasks).

Excluded despite having trial-level data:

- `devarda2023_predictability` — the prompt needs `{sentence_fragment}`, but the
  CSV only stores the target word, so the context cannot be reconstructed.
- `green2025_aoa_reading` / `green2025_aoa_writing` — responses are continuous
  ages on a 0–20 range, not a small integer scale, so single-token digit scoring
  and the discrete-PMF analysis do not apply.

The remaining `norm_datasets/` sources ship aggregate means only, so they can be
scored for mean correlation but carry no reliability or distribution ceiling.

**Not yet wired up:** `mturk_norms/` and `surveyor_norms/` (Ted's data) add ~271
datasets in the same schema, each with a `scale` / `scale_inferred` column in
`a_index.csv`. The registry is currently hardcoded; auto-discovery from those
index files is the obvious next extension. Note some surveyor scale strings are
reversed (`5-Very Natural .. 1-Very Unnatural`), so a parser must take min/max of
the digits rather than first/second.

## Cluster setup (MIT Engaging)

```bash
module load miniforge && eval "$(conda shell.bash hook)" && conda create -n llm-ratings python=3.11 -y && conda activate llm-ratings
```

```bash
pip install torch transformers accelerate numpy scipy tqdm
```

Model weights must not land in `$HOME`. Point `SCRATCH_DIR` at real scratch, or
at pool if no scratch mount exists — `run_experiment.sbatch` refuses to start if
it is unset:

```bash
export POOL_DIR=$HOME/orcd/pool/llm-ratings-research
export SCRATCH_DIR=$HOME/orcd/pool
export HF_TOKEN=hf_...   # only needed for gated repos (Llama)
```

Gated models also require clicking through the licence on the model page; the
token alone is not enough. Qwen3 is not gated.

## Running

Interactive GPU:

```bash
srun -p mit_normal_gpu --gres=gpu:1 --mem=32G --time=1:00:00 --pty bash
```

Smoke test (80 items, prints the prompt):

```bash
python pipeline/experiments.py --model qwen17b --dataset dentella2023_grammaticality --show-prompt
```

Batch:

```bash
EXTRA="--limit 300" sbatch -p mit_normal_gpu pipeline/run_experiment.sbatch qwen17b all
```

**Always cap `--limit` unless you mean it.** The 17 datasets total ~550,000
items (`lancaster2020_*` is ~40k each, `muraki2023` is 66k). Uncapped will not
finish inside a 4-hour wall time.

Model aliases: `qwen06b`, `qwen17b`, `qwen4b`, `qwen8b`, `qwen25-7b`, `llama8b`,
`llama70b`, `glm9b`, `glm32b`. Any Hugging Face model id works directly.
**The GLM aliases are unverified guesses** — confirm the checkpoint id before
relying on them.

Reruns skip datasets that already have an items CSV; pass `--overwrite` to force.

## Outputs

Written to `results/<model_slug>/`:

- `<dataset>_items.csv` — `unit, n_raters, human_mean, model_expected, scale_mass, p_<k>..., hcount_<k>...`
- `<dataset>_summary.json` — model/human means, Pearson + Spearman, alignment score, equivalence rate
- `all_summaries.json` — every dataset for that model
- `reliability.json` — split-half reliability and model-vs-human correlation

`p_<k>` is the model's probability for scale point k; `hcount_<k>` is how many
humans chose it. Comparing those two blocks — not just the means — is the point
of the whole exercise.

## Interpreting results

**Mean level.** `pearson_r` between `model_expected` and `human_mean`, and
`r_over_ceiling` from `reliability_correlation.py`, which divides by
`sqrt(human reliability)`. Humans do not perfectly agree with each other, so raw
correlation understates the model.

**Distribution level.** `alignment` reports Wasserstein-1 distances: `model`
(model vs humans), `null` (model paired with the wrong items — chance), and
`ceiling` (finite-rater noise). If `model` is not clearly below `null`, there is
no signal. `equivalence.prop_similar` is the fraction of items whose model
distribution matches humans within split-half sampling noise.

Two caveats. `alignment.normalized` depends on the `ceiling` estimate, which is
**known to need revision** — prefer the raw `model` / `null` / `ceiling`
distances. And `equivalence` compares a 95th percentile against a median, so it
is conservative by construction; low `prop_similar` is expected even for decent
models.

**The two levels can disagree, and that is the interesting part.** In the first
real run, Qwen3-1.7B on `diveica2023_socialness` (n=300) scored `r=0.515`
against a human ceiling of `0.879` — respectable at the mean level. But it put
73% of its modal responses on "4", never chose 6 or 7, and had mean entropy of
0.45 bits versus 2.31 for humans. `prop_similar` was 0.0. Mean-level correlation
substantially overstated alignment.

## Cost knobs

Bootstrap analyses are the expensive part and run on a subsample by default:
`--align-items 300 --align-boot 200 --equiv-items 100 --equiv-boot 2000`. Set
`--align-items 0` to use every item.
