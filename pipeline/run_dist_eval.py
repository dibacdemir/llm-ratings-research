#!/usr/bin/env python
"""Do model and human *distributions* match, not just their means?

Takes the .jsonl written by run_expected_rating.py, rebuilds each item's human
count vector from `individual_ratings`, and runs Ted's pipeline:

  per item   delta = split_half_delta(counts)["delta"]     (human sampling noise)
             equivalence_test(llm_p, counts, delta)        -> similar: True/False
  per task   alignment_score([(llm_p, counts), ...])       -> model / null / ceiling

    python pipeline/run_dist_eval.py --ratings runs/amouyal_qwen3-8b.jsonl \
        --out runs/amouyal_qwen3-8b.dist.csv

No torch needed — numpy only.
"""

import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import data, dist  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ratings", required=True, help="jsonl from run_expected_rating.py")
    p.add_argument("--out", help="per-item CSV (default: <ratings>.dist.csv)")
    p.add_argument("--task", help="override the task recorded in the .meta.json")
    p.add_argument("--scale", help="override the scale, e.g. 1-7")

    p.add_argument("--n-splits", type=int, default=2000,
                   help="split-half resamples per item for delta (Ted's default 10000)")
    p.add_argument("--n-boot", type=int, default=2000,
                   help="bootstrap draws per item in the equivalence test")
    p.add_argument("--align-boot", type=int, default=2000,
                   help="bootstrap draws for the ceiling/null in alignment_score")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=0)

    p.add_argument("--min-n", type=int, default=4,
                   help="skip items with fewer than this many human raters")
    p.add_argument("--min-option-mass", type=float, default=0.0,
                   help="skip items where the model put less than this much "
                        "probability on the valid options before renormalising")
    p.add_argument("--max-items", type=int,
                   help="evaluate only the first N usable items")
    return p.parse_args(argv)


def load_ratings(path):
    rows = [json.loads(line) for line in open(path) if line.strip()]
    meta_path = path + ".meta.json"
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    return rows, meta


def main(argv=None):
    args = parse_args(argv)
    rows, meta = load_ratings(args.ratings)
    task = args.task or meta.get("task")
    if not task:
        print("error: no task in meta, pass --task", file=sys.stderr)
        return 2

    loc = data.find_task(task)
    items = data.load_items(loc["csv"])
    by_unit = {}
    for it in items:
        by_unit.setdefault(it["unit"], it)

    if args.scale:
        lo, hi = data.resolve_scale(None, None, override=args.scale)
    elif meta.get("scale"):
        lo, hi = meta["scale"]
    else:
        from llm_ratings.prompt import read_instructions
        lo, hi = data.resolve_scale(read_instructions(loc["instructions"]), items)
    k = hi - lo + 1

    pairs, records, skipped = [], [], {"no_human": 0, "few_raters": 0, "low_mass": 0,
                                       "unmatched": 0, "width": 0}
    for r in rows:
        it = by_unit.get(r["unit"])
        if it is None:
            skipped["unmatched"] += 1
            continue
        if not it["individual"]:
            skipped["no_human"] += 1
            continue
        if r.get("option_mass", 1.0) < args.min_option_mass:
            skipped["low_mass"] += 1
            continue
        counts, _dropped = data.human_counts(it["individual"], lo, hi)
        if sum(counts) < args.min_n:
            skipped["few_raters"] += 1
            continue
        p = np.asarray(r["probs"], float)
        if len(p) != k:
            skipped["width"] += 1
            continue
        records.append((r, it, counts, p))
        if args.max_items and len(records) >= args.max_items:
            break

    if not records:
        print("no usable items: %s" % skipped, file=sys.stderr)
        return 1

    out_path = args.out or (args.ratings + ".dist.csv")
    outdir = os.path.dirname(os.path.abspath(out_path))
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    t0 = time.time()
    W1, DELTA, UPPER, SIM = [], [], [], []
    with open(out_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["idx", "unit", "n_raters", "human_mean", "expected",
                    "W1", "delta", "W1_over_delta", "upper_95", "similar",
                    "option_mass"])
        for i, (r, it, counts, p) in enumerate(records):
            res = dist.per_item(p, counts, n_splits=args.n_splits,
                                n_boot=args.n_boot, alpha=args.alpha, seed=args.seed)
            W1.append(res["W1"]); DELTA.append(res["delta"])
            UPPER.append(res["upper_95"]); SIM.append(res["similar"])
            ratio = (float(res["W1"]) / float(res["delta"])
                     if res["delta"] and np.isfinite(res["delta"])
                     and res["delta"] > 0 else float("nan"))
            w.writerow([r["idx"], it["unit"], res["n"], it["mean"], r["expected"],
                        round(float(res["W1"]), 5), round(float(res["delta"]), 5),
                        round(ratio, 4), round(float(res["upper_95"]), 5),
                        res["similar"], r.get("option_mass")])
            if (i + 1) % 200 == 0:
                print("  %d/%d items" % (i + 1, len(records)), flush=True)
            pairs.append((p, counts))

    print("per-item results -> %s  [%.1fs]" % (out_path, time.time() - t0))

    print("computing alignment_score (n_boot=%d) ..." % args.align_boot, flush=True)
    align = dist.alignment_score(pairs, n_boot=args.align_boot, seed=args.seed)

    exp = [r["expected"] for r, _it, _c, _p in records]
    hum = [it["mean"] for _r, it, _c, _p in records]
    summary = {
        "task": task, "model": meta.get("model"), "scale": [lo, hi],
        "n_items_scored": len(rows), "n_items_evaluated": len(records),
        "skipped": skipped,
        "median_n_raters": float(np.median([sum(c) for _r, _i, c, _p in records])),
        "frac_similar": float(np.mean([s is True for s in SIM])),
        "median_W1": float(np.nanmedian(W1)),
        "median_delta": float(np.nanmedian(DELTA)),
        # Interpretable and free of the null-inflation that distorts
        # `alignment.normalized`: 1.0 means the model sits as far from the
        # human distribution as one half of the raters sits from the other.
        "median_W1_over_delta": float(np.nanmedian(
            [w / d for w, d in zip(W1, DELTA)
             if d and np.isfinite(d) and d > 0 and np.isfinite(w)] or [np.nan])),
        "median_upper_95": float(np.nanmedian(UPPER)),
        "alignment": align,
        "mean_level_pearson_r": round(dist.pearson(exp, hum), 4),
        "mean_level_spearman_r": round(dist.spearman(exp, hum), 4),
        "mean_option_mass": round(
            float(np.mean([r.get("option_mass", float("nan"))
                           for r, _i, _c, _p in records])), 4),
        "settings": {"n_splits": args.n_splits, "n_boot": args.n_boot,
                     "align_boot": args.align_boot, "alpha": args.alpha,
                     "seed": args.seed, "min_n": args.min_n,
                     "min_option_mass": args.min_option_mass},
    }
    with open(out_path + ".summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    print()
    print("== %s | %s ==" % (task, meta.get("model")))
    print("items evaluated      %d  (median %d raters)"
          % (summary["n_items_evaluated"], summary["median_n_raters"]))
    print("mean-level r         pearson %.3f / spearman %.3f"
          % (summary["mean_level_pearson_r"], summary["mean_level_spearman_r"]))
    print("distribution-level   median W1 %.3f   vs median split-half delta %.3f"
          "   (ratio %.2fx human noise)"
          % (summary["median_W1"], summary["median_delta"],
             summary["median_W1_over_delta"]))
    print("equivalent items     %.1f%% (upper_95 < delta)"
          % (100 * summary["frac_similar"]))
    print("alignment            model %.3f | ceiling %.3f | null %.3f -> "
          "normalized %.3f"
          % (align["model"], align["ceiling"], align["null"], align["normalized"]))
    print("option mass (mean)   %.3f" % summary["mean_option_mass"])
    print("summary -> %s" % (out_path + ".summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
