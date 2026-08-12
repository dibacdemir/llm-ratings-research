'''
Expected-rating experiments over norm datasets with trial-level human data.

Goals:
1. Getting the expected rating approach for some models
2. Testing whether for datasets with the full distribution of human ratings,
   models and humans produce similar distributions of responses (besides showing similar means)

How a model is scored (the "expected rating" approach):
  For each item we build the prompt from the dataset's instruction file, run ONE
  forward pass, take the next-token distribution, keep only the probability mass
  sitting on the scale digits, and renormalize. That gives a PMF over the rating
  scale. The expected rating is sum(k * p_k). No sampling, no generation.

The logic for delta: two halves of the same human data differ bc of
sampling noise, so that split-half distance is a tolerance level for
asking whether two distributions come from the same place.

Per item:
1. Build the human counts as a vector over the scale (how many 1s, 2s, ... 7s)
   and the model's probabilities from the expected-rating pass.
2. Get delta with split_half_delta(human_counts)["delta"]
3. Call equivalence_test(llm_p, human_counts, delta=delta).
   If similar: True, that item's model and human distributions match within sampling noise.
4. Then across a whole dataset, pass a list of pairs of llm_p, human_counts to alignment_score(items).
   It returns three numbers: the model-human distance, a null floor from shuffling which model goes
   with which item (chance), and a noise ceiling. The ceiling is the best a perfect model could do,
   limited by the fact that human ratings come from a finite number of raters with noise.
   The code draws human samples of the same size and tests how far they are from the full human
   distribution (note: this is not exactly standard, ok for now).
   The normalized score says where the model are between floor and ceiling
   (1: as close as a perfect model, 0: chance).

Usage:
    python experiments.py --list
    python experiments.py --model llama8b --dataset dentella2023_grammaticality
    python experiments.py --model llama8b --dataset all --limit 500
'''

import argparse
import ast
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

def _find_repo_root(start):
    '''Walk up until we find the data directories.

    Keeps the scripts runnable whether they sit at the repo root or in
    pipeline/, and regardless of the working directory they are invoked from.
    '''
    for d in (start, *start.parents):
        if (d / "norm_datasets").is_dir() and (d / "instructions").is_dir():
            return d
    raise SystemExit(
        f"could not locate norm_datasets/ and instructions/ above {start}. "
        "Run from inside the repo."
    )


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
DATA_ROOT = REPO_ROOT / "norm_datasets"
INSTRUCTION_ROOT = REPO_ROOT / "instructions"


# --------------------------------------------------------------------------
# Dataset registry: only datasets whose CSV carries trial-level responses
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class DatasetSpec:
    key: str
    csv_path: Path
    instruction_path: Path
    lo: int
    hi: int
    placeholder: str

    @property
    def n_levels(self):
        return self.hi - self.lo + 1

    @property
    def levels(self):
        return np.arange(self.lo, self.hi + 1)


def _spec(source, task, lo, hi, placeholder):
    key = f"{source}_{task}"
    return DatasetSpec(
        key=key,
        csv_path=DATA_ROOT / f"{source}_data" / f"{key}.csv",
        instruction_path=INSTRUCTION_ROOT / f"{source}_instructions" / f"{key}_i.txt",
        lo=lo,
        hi=hi,
        placeholder=placeholder,
    )


_LANCASTER_TASKS = [
    "auditory", "foot_leg", "gustatory", "hand_arm", "haptic", "head",
    "interoceptive", "mouth", "olfactory", "torso", "visual",
]

DATASETS = {
    s.key: s
    for s in [
        _spec("amouyal2024", "plausibility", 1, 7, "sentence"),
        _spec("dentella2023", "grammaticality", 0, 1, "sentence"),
        _spec("diveica2023", "socialness", 1, 7, "word"),
        _spec("edwards2024", "spelling_to_pronunciation_transparency", 1, 6, "word"),
        _spec("giurgea2025", "motivation", 1, 7, "word"),
        _spec("muraki2023", "concreteness", 1, 5, "expression"),
        *[_spec("lancaster2020", t, 0, 5, "word") for t in _LANCASTER_TASKS],
    ]
}

# Trial-level data exists but the item cannot be scored as-is:
#   devarda2023_predictability -> prompt needs {sentence_fragment}, the CSV only
#     stores the target word, so the context is unrecoverable from this repo.
#   green2025_aoa_reading / _writing -> responses are continuous ages (4.42, 9.5,
#     ...) on a 0-20 range, not a small integer scale, so single-token digit
#     scoring and the discrete-PMF analysis do not apply.
EXCLUDED = {
    "devarda2023_predictability": "instruction needs {sentence_fragment}, absent from CSV",
    "green2025_aoa_reading": "continuous 0-20 responses, not a discrete digit scale",
    "green2025_aoa_writing": "continuous 0-20 responses, not a discrete digit scale",
}

# Aliases are a convenience only; any HF repo id can be passed to --model directly.
# Sizes are the released Qwen3 sizes (there is no 2.7B); start small, the task
# needs no reasoning, and small models make the whole sweep cheap.
MODEL_ALIASES = {
    "qwen06b": "Qwen/Qwen3-0.6B",
    "qwen17b": "Qwen/Qwen3-1.7B",
    "qwen4b": "Qwen/Qwen3-4B",
    "qwen8b": "Qwen/Qwen3-8B",
    "qwen25-7b": "Qwen/Qwen2.5-7B-Instruct",
    "llama8b": "meta-llama/Llama-3.1-8B-Instruct",   # gated, needs HF_TOKEN
    "llama70b": "meta-llama/Llama-3.3-70B-Instruct",  # gated, needs HF_TOKEN
    "glm9b": "THUDM/glm-4-9b-chat",
    "glm32b": "THUDM/GLM-4-32B-0414",
}


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

@dataclass
class Item:
    unit: str
    counts: np.ndarray      # length n_levels, integer counts per scale point
    n_raters: int
    human_mean: float
    ratings: list           # raw trial-level responses, kept for reliability


def load_items(spec, limit=None):
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    items = []
    skipped = 0
    with open(spec.csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            raw = (row.get("individual_ratings") or "").strip()
            unit = (row.get("unit") or "").strip()
            if not raw or raw == "[]" or not unit:
                skipped += 1
                continue
            try:
                ratings = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                skipped += 1
                continue

            counts = np.zeros(spec.n_levels, dtype=int)
            usable = []
            for value in ratings:
                try:
                    k = int(round(float(value)))
                except (TypeError, ValueError):
                    continue
                if spec.lo <= k <= spec.hi:
                    counts[k - spec.lo] += 1
                    usable.append(k)
            if counts.sum() < 2:
                skipped += 1
                continue

            items.append(Item(
                unit=unit,
                counts=counts,
                n_raters=int(counts.sum()),
                human_mean=float(np.dot(counts, spec.levels) / counts.sum()),
                ratings=usable,
            ))
            if limit and len(items) >= limit:
                break
    return items, skipped


def build_prompt(template, spec, unit):
    return template.replace("{" + spec.placeholder + "}", unit)


# --------------------------------------------------------------------------
# Model scoring
# --------------------------------------------------------------------------

class RatingScorer:
    '''Next-token probability over the scale digits, one forward pass per item.'''

    def __init__(self, model_name, dtype="bfloat16", device_map="auto",
                 batch_size=16, max_length=2048, answer_prefix=None,
                 enable_thinking=False):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.model_name = MODEL_ALIASES.get(model_name, model_name)
        self.batch_size = batch_size
        self.max_length = max_length
        # Reasoning models (Qwen3, and anything else whose template opens a
        # <think> block) emit reasoning tokens before the answer, so the FIRST
        # next-token distribution sits on <think> and carries no rating mass at
        # all. Templates that support it get enable_thinking=False, which closes
        # the think block in the prompt so the answer is genuinely next.
        self.enable_thinking = enable_thinking

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, trust_remote_code=True, padding_side="left"
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # transformers renamed torch_dtype -> dtype; support both.
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, dtype=getattr(torch, dtype),
                device_map=device_map, trust_remote_code=True,
            )
        except TypeError:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, torch_dtype=getattr(torch, dtype),
                device_map=device_map, trust_remote_code=True,
            )
        self.model.eval()

        self.use_chat_template = getattr(self.tokenizer, "chat_template", None) is not None
        if answer_prefix is not None:
            self.answer_prefix = answer_prefix
        else:
            self.answer_prefix = "" if self.use_chat_template else "\nAnswer:"

    def _render(self, prompt):
        text = prompt.strip()
        if self.use_chat_template:
            messages = [{"role": "user", "content": text}]
            kwargs = dict(tokenize=False, add_generation_prompt=True)
            try:
                rendered = self.tokenizer.apply_chat_template(
                    messages, enable_thinking=self.enable_thinking, **kwargs
                )
            except TypeError:
                # template does not take enable_thinking; nothing to disable
                rendered = self.tokenizer.apply_chat_template(messages, **kwargs)
            return rendered + self.answer_prefix
        return text + self.answer_prefix

    def top_tokens(self, prompt, k=8):
        '''Most likely next tokens for one prompt. Used to explain low scale mass.'''
        torch = self.torch
        batch = self.tokenizer(
            [self._render(prompt)], return_tensors="pt", truncation=True,
            max_length=self.max_length, add_special_tokens=not self.use_chat_template,
        ).to(self.model.device)
        with torch.no_grad():
            logits = self.model(**batch).logits[0, -1, :].float()
        probs = torch.softmax(logits, dim=-1)
        top = torch.topk(probs, k)
        return [(repr(self.tokenizer.decode([i])), round(float(p), 4))
                for i, p in zip(top.indices.tolist(), top.values.tolist())]

    def scale_token_ids(self, spec):
        '''Candidate single-token ids for each scale point, with and without a leading space.'''
        ids_per_level = []
        for k in range(spec.lo, spec.hi + 1):
            candidates = set()
            for surface in (str(k), " " + str(k)):
                encoded = self.tokenizer.encode(surface, add_special_tokens=False)
                if len(encoded) == 1:
                    candidates.add(encoded[0])
            if not candidates:
                raise ValueError(
                    f"scale point {k} is not a single token for {self.model_name}"
                )
            ids_per_level.append(sorted(candidates))
        return ids_per_level

    def score(self, prompts, spec, progress_every=200):
        torch = self.torch
        ids_per_level = self.scale_token_ids(spec)
        flat_ids = [i for level in ids_per_level for i in level]
        level_of = np.concatenate(
            [np.full(len(level), j) for j, level in enumerate(ids_per_level)]
        )
        index = torch.tensor(flat_ids, device=self.model.device)

        pmfs = np.zeros((len(prompts), spec.n_levels))
        masses = np.zeros(len(prompts))

        start = time.time()
        for begin in range(0, len(prompts), self.batch_size):
            chunk = [self._render(p) for p in prompts[begin:begin + self.batch_size]]
            batch = self.tokenizer(
                chunk, return_tensors="pt", padding=True,
                truncation=True, max_length=self.max_length,
                add_special_tokens=not self.use_chat_template,
            ).to(self.model.device)

            with torch.no_grad():
                logits = self.model(**batch).logits[:, -1, :].float()
            probs = torch.softmax(logits, dim=-1).index_select(1, index).cpu().numpy()

            for j in range(spec.n_levels):
                pmfs[begin:begin + len(chunk), j] = probs[:, level_of == j].sum(axis=1)
            masses[begin:begin + len(chunk)] = probs.sum(axis=1)

            done = begin + len(chunk)
            if progress_every and (done % progress_every < self.batch_size or done == len(prompts)):
                rate = done / max(time.time() - start, 1e-9)
                print(f"    {done}/{len(prompts)} items ({rate:.1f}/s)", flush=True)

        pmfs = pmfs / np.clip(pmfs.sum(axis=1, keepdims=True), 1e-12, None)
        return pmfs, masses


# --------------------------------------------------------------------------
# Distribution analysis
# --------------------------------------------------------------------------

def wasserstein1_pmf(p, q):
    # p, q: PMFs on evenly spaced scale points
    # W1 = L1 distance between CDFs at the interior cut points
    cp = np.cumsum(p)[:-1]
    cq = np.cumsum(q)[:-1]
    return np.sum(np.abs(cp - cq))


def _w1_rows(P, Q):
    '''Row-wise W1 for stacks of PMFs, shapes (m, K) and (m, K) or (K,).'''
    P = np.atleast_2d(P)
    Q = np.atleast_2d(Q)
    cp = np.cumsum(P, axis=1)[:, :-1]
    cq = np.cumsum(Q, axis=1)[:, :-1]
    return np.abs(cp - cq).sum(axis=1)


def equivalence_test(llm_p, human_counts, delta, n_boot=10000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    llm_p = np.asarray(llm_p, float); llm_p = llm_p / llm_p.sum()
    counts = np.asarray(human_counts, float)
    N = int(counts.sum())
    human_p = counts / N
    point = wasserstein1_pmf(llm_p, human_p)
    boot = _w1_rows(llm_p[None, :], rng.multinomial(N, human_p, size=n_boot) / N)
    upper = float(np.quantile(boot, 1 - alpha))   # one-sided 95% upper bound
    return {"W1": float(point), "upper_95": upper, "delta": float(delta),
            "similar": bool(upper < delta)}


def split_half_delta(human_counts, n_splits=10000, quantile=0.5, seed=0):
    '''Median W1 between two random halves of the same human sample.

    Splitting counts into halves without replacement is exactly multivariate
    hypergeometric sampling, which numpy does vectorised.
    '''
    rng = np.random.default_rng(seed)
    counts = np.asarray(human_counts, int)
    N = int(counts.sum())
    h = N // 2
    if h < 1:
        return {"delta": float("nan"), "mean": float("nan"), "dist": np.array([])}

    a = rng.multivariate_hypergeometric(counts, h, size=n_splits).astype(float)
    b = counts[None, :] - a
    a /= a.sum(axis=1, keepdims=True)
    b /= b.sum(axis=1, keepdims=True)
    dists = _w1_rows(a, b)
    return {"delta": float(np.quantile(dists, quantile)),  # median split-half W1
            "mean": float(dists.mean()),
            "dist": dists}


def alignment_score(items, n_boot=2000, seed=0):
    # items: list of (llm_p, human_counts). Uses ALL raters; model stays clean.
    rng = np.random.default_rng(seed)
    llm = np.array([np.asarray(p, float) / np.sum(p) for p, _ in items])
    hum_c = [np.asarray(c, int) for _, c in items]
    hum_p = np.array([c / c.sum() for c in hum_c])
    Ns = [int(c.sum()) for c in hum_c]
    n = len(items)

    # model vs full-N human dist, averaged over items
    model = float(_w1_rows(llm, hum_p).mean())

    # ceiling: where a perfect clean model would sit = one-sided N-rater noise.
    # bootstrap a fresh N-rater sample per item and measure W1 back to the full dist.
    per_item_ceiling = np.array([
        _w1_rows(hum_p[i][None, :], rng.multinomial(Ns[i], hum_p[i], size=n_boot) / Ns[i]).mean()
        for i in range(n)
    ])
    ceil = float(per_item_ceiling.mean())

    # null (floor): shuffle which model dist pairs with which item
    null = float(np.mean([
        _w1_rows(llm[rng.permutation(n)], hum_p).mean()
        for _ in range(n_boot)
    ]))

    norm = (null - model) / (null - ceil) if null != ceil else float("nan")
    return {"model": round(model, 3), "null": round(null, 3),
            "ceiling": round(ceil, 3), "normalized": round(norm, 3)}


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def slugify(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def write_items_csv(path, spec, items, pmfs, masses):
    levels = list(range(spec.lo, spec.hi + 1))
    header = (["unit", "n_raters", "human_mean", "model_expected", "scale_mass"]
              + [f"p_{k}" for k in levels]
              + [f"hcount_{k}" for k in levels])
    expected = pmfs @ spec.levels
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for i, item in enumerate(items):
            writer.writerow(
                [item.unit, item.n_raters, f"{item.human_mean:.6f}",
                 f"{expected[i]:.6f}", f"{masses[i]:.6g}"]
                + [f"{p:.6g}" for p in pmfs[i]]
                + list(item.counts)
            )
    return expected


def analyse(spec, items, pmfs, expected, masses, align_items, align_boot,
            equiv_items, equiv_boot, seed):
    from scipy.stats import pearsonr, spearmanr

    human_means = np.array([it.human_mean for it in items])
    rng = np.random.default_rng(seed)

    summary = {
        "dataset": spec.key,
        "scale": [spec.lo, spec.hi],
        "n_items": len(items),
        "mean_n_raters": float(np.mean([it.n_raters for it in items])),
        "human_mean_rating": float(human_means.mean()),
        "model_mean_rating": float(expected.mean()),
        "mean_scale_mass": float(masses.mean()),
        "min_scale_mass": float(masses.min()),
    }

    if len(items) > 2 and np.std(expected) > 0 and np.std(human_means) > 0:
        r, p = pearsonr(expected, human_means)
        rho, p_rho = spearmanr(expected, human_means)
        summary["pearson_r"] = float(r)
        summary["pearson_p"] = float(p)
        summary["spearman_rho"] = float(rho)
        summary["spearman_p"] = float(p_rho)

    # Distribution work is bootstrap-heavy, so it runs on a random subsample.
    idx = np.arange(len(items))
    if align_items and len(idx) > align_items:
        idx = rng.choice(idx, align_items, replace=False)
    if len(idx) > 2:
        pairs = [(pmfs[i], items[i].counts) for i in idx]
        summary["alignment"] = alignment_score(pairs, n_boot=align_boot, seed=seed)
        summary["alignment_n_items"] = int(len(idx))

    eq_idx = idx
    if equiv_items and len(eq_idx) > equiv_items:
        eq_idx = rng.choice(eq_idx, equiv_items, replace=False)
    if len(eq_idx) > 0:
        flags, deltas, w1s = [], [], []
        for i in eq_idx:
            delta = split_half_delta(items[i].counts, n_splits=2000, seed=seed)["delta"]
            res = equivalence_test(pmfs[i], items[i].counts, delta=delta,
                                   n_boot=equiv_boot, seed=seed)
            flags.append(res["similar"]); deltas.append(delta); w1s.append(res["W1"])
        summary["equivalence"] = {
            "n_items": int(len(eq_idx)),
            "prop_similar": float(np.mean(flags)),
            "mean_delta": float(np.mean(deltas)),
            "mean_W1": float(np.mean(w1s)),
        }
    return summary


def run_dataset(spec, scorer, args, out_dir):
    print(f"\n=== {spec.key} (scale {spec.lo}-{spec.hi}) ===", flush=True)
    items, skipped = load_items(spec, limit=args.limit)
    if not items:
        print(f"  no usable trial-level rows, skipping ({skipped} skipped)")
        return None
    print(f"  {len(items)} items loaded ({skipped} rows without usable trial data)", flush=True)

    template = spec.instruction_path.read_text(encoding="utf-8")
    prompts = [build_prompt(template, spec, it.unit) for it in items]
    if args.show_prompt:
        print("  --- example prompt ---")
        print("  " + prompts[0].replace("\n", "\n  "))
        print("  ----------------------", flush=True)

    pmfs, masses = scorer.score(prompts, spec)

    # Low scale mass means the renormalised PMF is noise, not a rating. Say so
    # loudly and show what the model actually wanted to emit instead.
    if masses.mean() < 0.5:
        print(f"  WARNING: mean scale mass {masses.mean():.4g} - the model is not "
              f"answering with a scale digit.", flush=True)
        print(f"  Top next-tokens for the first item:")
        for tok, p in scorer.top_tokens(prompts[0]):
            print(f"      {tok:<24} {p}")
        print("  Everything below is unreliable. Fixes: --answer-prefix 'Answer: ', "
              "or a non-reasoning model.", flush=True)

    items_path = out_dir / f"{spec.key}_items.csv"
    expected = write_items_csv(items_path, spec, items, pmfs, masses)

    summary = analyse(spec, items, pmfs, expected, masses,
                      args.align_items, args.align_boot,
                      args.equiv_items, args.equiv_boot, args.seed)
    summary["model"] = scorer.model_name
    summary["items_csv"] = str(items_path)

    (out_dir / f"{spec.key}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"  human mean={summary['human_mean_rating']:.3f}  "
          f"model mean={summary['model_mean_rating']:.3f}  "
          f"r={summary.get('pearson_r', float('nan')):.3f}  "
          f"scale mass={summary['mean_scale_mass']:.3f}", flush=True)
    return summary


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", help="HF model id or alias: " + ", ".join(MODEL_ALIASES))
    p.add_argument("--dataset", default="all",
                   help="dataset key, comma-separated keys, a source prefix "
                        "like lancaster2020, or 'all'")
    p.add_argument("--list", action="store_true", help="list runnable datasets and exit")
    p.add_argument("--output-dir", default="results")
    p.add_argument("--limit", type=int, help="cap items per dataset (smoke tests)")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--device-map", default="auto")
    p.add_argument("--answer-prefix", default=None,
                   help="text appended after the prompt; defaults to '' for chat "
                        "models and '\\nAnswer:' otherwise")
    p.add_argument("--enable-thinking", action="store_true",
                   help="let reasoning models emit a <think> block. Off by default: "
                        "with thinking on, the first next-token is <think> and no "
                        "probability mass reaches the rating digits")
    p.add_argument("--align-items", type=int, default=300,
                   help="subsample size for alignment_score (0 = all items)")
    p.add_argument("--align-boot", type=int, default=200)
    p.add_argument("--equiv-items", type=int, default=100,
                   help="subsample size for per-item equivalence tests (0 = all)")
    p.add_argument("--equiv-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--show-prompt", action="store_true")
    p.add_argument("--overwrite", action="store_true",
                   help="re-run datasets that already have an items CSV")
    return p.parse_args(argv)


def resolve_datasets(selector):
    if selector == "all":
        return list(DATASETS.values())
    chosen = []
    for part in selector.split(","):
        part = part.strip()
        if part in DATASETS:
            chosen.append(DATASETS[part])
            continue
        prefixed = [s for k, s in DATASETS.items() if k.startswith(part)]
        if not prefixed:
            raise SystemExit(f"unknown dataset '{part}'. Try --list.")
        chosen.extend(prefixed)
    return chosen


def main(argv=None):
    args = parse_args(argv)

    if args.list:
        print("Runnable (trial-level responses present):")
        for key, spec in DATASETS.items():
            print(f"  {key:<55} scale {spec.lo}-{spec.hi}  {{{spec.placeholder}}}")
        print("\nExcluded:")
        for key, why in EXCLUDED.items():
            print(f"  {key:<55} {why}")
        return 0

    if not args.model:
        raise SystemExit("--model is required (or use --list)")

    specs = resolve_datasets(args.dataset)
    out_dir = Path(args.output_dir) / slugify(MODEL_ALIASES.get(args.model, args.model))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.overwrite:
        pending = [s for s in specs if not (out_dir / f"{s.key}_items.csv").exists()]
        for s in specs:
            if s not in pending:
                print(f"skipping {s.key} (already in {out_dir}, use --overwrite)")
        specs = pending
    if not specs:
        print("nothing to run")
        return 0

    scorer = RatingScorer(
        args.model, dtype=args.dtype, device_map=args.device_map,
        batch_size=args.batch_size, max_length=args.max_length,
        answer_prefix=args.answer_prefix,
        enable_thinking=args.enable_thinking,
    )
    print(f"model: {scorer.model_name} (chat template: {scorer.use_chat_template})", flush=True)

    summaries = [s for s in (run_dataset(spec, scorer, args, out_dir) for spec in specs) if s]

    combined = out_dir / "all_summaries.json"
    existing = json.loads(combined.read_text()) if combined.exists() else []
    by_key = {s["dataset"]: s for s in existing}
    by_key.update({s["dataset"]: s for s in summaries})
    combined.write_text(json.dumps(list(by_key.values()), indent=2), encoding="utf-8")

    print(f"\nwrote {len(summaries)} dataset summaries to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
