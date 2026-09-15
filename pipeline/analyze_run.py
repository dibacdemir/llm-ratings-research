#!/usr/bin/env python
"""Three questions about one run, answered with numbers.

  1. Is the logprob read clean?   -> option_mass, and whether any single option
                                     swallows the item (degenerate PMFs)
  2. How well do the means match? -> Pearson/Spearman, sd ratio, OLS slope
  3. How well do the distributions match?
                                  -> entropy vs humans, the marginal PMF over
                                     the whole task, and the argmax histogram

The marginal PMF and the argmax histogram are the scale-usage bias check: a
model can correlate well with human means while only ever answering 4 or 6.

    python pipeline/analyze_run.py result/<model>/<task>.jsonl
    python pipeline/analyze_run.py result/*/amouyal2024_plausibility.jsonl
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import data, dist  # noqa: E402


def entropy(p):
    return -(p * np.log2(np.clip(p, 1e-12, 1))).sum(axis=-1)


def w1_decompose(model_p, human_p):
    """Split W1 into a location part and a shape part.

    For distributions on the line, W1 = integral |F - G| >= |integral (F - G)|
    = |mean difference|, so

        W1 = |E_model - E_human|  +  shape_excess,   shape_excess >= 0.

    The location term is what a mean-level correlation already sees. The shape
    excess is the part of the mismatch that only a distributional comparison
    can detect -- the number that justifies doing any of this.
    """
    cm = np.cumsum(model_p, axis=-1)[..., :-1]
    ch = np.cumsum(human_p, axis=-1)[..., :-1]
    w1 = np.abs(cm - ch).sum(axis=-1)
    loc = np.abs((ch - cm).sum(axis=-1))  # == |mean_model - mean_human|
    return w1, loc, np.maximum(w1 - loc, 0.0)


def analyze(path, quiet=False):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    meta_path = path + ".meta.json"
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    task = meta.get("task") or os.path.basename(path).split(".jsonl")[0]
    lo, hi = meta.get("scale", [None, None])

    loc = data.find_task(task)
    items = {it["unit"]: it for it in data.load_items(loc["csv"])}
    if lo is None:
        from llm_ratings.prompt import read_instructions
        lo, hi = data.resolve_scale(read_instructions(loc["instructions"]),
                                    list(items.values()))
    vals = np.arange(lo, hi + 1)

    P = np.array([r["probs"] for r in rows], float)
    mass = np.array([r.get("option_mass", np.nan) for r in rows], float)
    E = np.array([r["expected"] for r in rows], float)
    H = np.array([r["human_mean"] if r["human_mean"] is not None else np.nan
                  for r in rows], float)

    keep = [i for i, r in enumerate(rows) if items.get(r["unit"], {}).get("individual")]
    Hp = None
    if keep:
        Hc = np.array([data.human_counts(items[rows[i]["unit"]]["individual"], lo, hi)[0]
                       for i in keep], float)
        Hp = Hc / np.clip(Hc.sum(1, keepdims=True), 1, None)

    ok = np.isfinite(E) & np.isfinite(H)
    res = {
        "run": os.path.basename(path).split(".jsonl")[0],
        "model": meta.get("model") or os.path.basename(os.path.dirname(path)),
        "task": task, "scale": [int(lo), int(hi)], "n_items": len(rows),
        "mass_min": float(np.nanmin(mass)), "mass_median": float(np.nanmedian(mass)),
        "mass_frac_below_0.9": float(np.mean(mass < 0.9)),
        "model_maxprob_median": float(np.median(P.max(1))),
        "model_frac_maxprob_above_0.9": float(np.mean(P.max(1) > 0.9)),
        "model_entropy_median": float(np.median(entropy(P))),
        "pearson": dist.pearson(E[ok], H[ok]), "spearman": dist.spearman(E[ok], H[ok]),
        "model_sd": float(E[ok].std()), "human_sd": float(H[ok].std()),
        "ols_slope_human_on_model": float(np.polyfit(E[ok], H[ok], 1)[0])
                                    if ok.sum() > 2 else float("nan"),
        "model_marginal": [round(float(x), 3) for x in P.mean(0)],
        "model_argmax_counts": np.bincount(P.argmax(1), minlength=len(vals)).tolist(),
        "unused_modes": [int(v) for v, c in
                         zip(vals, np.bincount(P.argmax(1), minlength=len(vals))) if c == 0],
    }
    if Hp is not None:
        Pk = P[keep]
        w1, loc, shape = w1_decompose(Pk, Hp)
        res.update({
            "human_maxprob_median": float(np.median(Hp.max(1))),
            "human_entropy_median": float(np.median(entropy(Hp))),
            "human_marginal": [round(float(x), 3) for x in Hp.mean(0)],
            "human_argmax_counts": np.bincount(Hp.argmax(1),
                                               minlength=len(vals)).tolist(),
            # means, not medians: the decomposition is additive per item, and
            # median(W1) != median(loc) + median(shape).
            "W1_mean": float(np.mean(w1)),
            "W1_location_mean": float(np.mean(loc)),
            "W1_shape_mean": float(np.mean(shape)),
            "shape_share_of_W1": float(np.mean(shape) / max(np.mean(w1), 1e-12)),
            "shape_share_median_per_item": float(
                np.median(shape / np.clip(w1, 1e-12, None))),
        })

    if not quiet:
        w = "  " + " ".join("%5d" % v for v in vals)
        print("=" * 76)
        print("%s   |   %s" % (res["run"], res["model"]))
        print("=" * 76)
        print("logprob read   mass: min %.3f  median %.3f   below 0.9: %.1f%%"
              % (res["mass_min"], res["mass_median"],
                 100 * res["mass_frac_below_0.9"]))
        print("               model max-prob median %.3f (>0.9 on %.1f%% of items)"
              % (res["model_maxprob_median"],
                 100 * res["model_frac_maxprob_above_0.9"]))
        if Hp is not None:
            print("               human max-prob median %.3f"
                  % res["human_maxprob_median"])
        # n matters: run_dist_eval caps at --max-items, this does not, so the
        # two report different Pearsons for the same run on big tasks.
        print("means          pearson %.3f  spearman %.3f   sd %.2f vs human %.2f"
              "   OLS slope %.2f   [all %d items]"
              % (res["pearson"], res["spearman"], res["model_sd"], res["human_sd"],
                 res["ols_slope_human_on_model"], int(ok.sum())))
        if Hp is not None:
            print("spread         entropy %.3f bits vs human %.3f (max %.3f)"
                  % (res["model_entropy_median"], res["human_entropy_median"],
                     np.log2(len(vals))))
            print("W1 split       mean %.3f = location %.3f + shape %.3f"
                  "   shape is %.0f%% of the gap (per-item median %.0f%%)"
                  % (res["W1_mean"], res["W1_location_mean"],
                     res["W1_shape_mean"], 100 * res["shape_share_of_W1"],
                     100 * res["shape_share_median_per_item"]))
        print("scale usage" + w)
        print("  model  P   " + " ".join("%5.3f" % x for x in res["model_marginal"]))
        if Hp is not None:
            print("  human  P   " + " ".join("%5.3f" % x for x in res["human_marginal"]))
        print("  model mode" + " ".join("%6d" % c for c in res["model_argmax_counts"]))
        if Hp is not None:
            print("  human mode" + " ".join("%6d" % c
                                            for c in res["human_argmax_counts"]))
        if res["unused_modes"]:
            print("  !! never the model's mode: %s" % res["unused_modes"])
        print()
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="one or more .jsonl run files")
    ap.add_argument("--json", help="write all results as JSON here")
    args = ap.parse_args(argv)
    out = []
    for path in args.runs:
        try:
            out.append(analyze(path))
        except Exception as exc:
            print("skip %s: %s: %s" % (path, type(exc).__name__, exc), file=sys.stderr)
    if args.json:
        json.dump(out, open(args.json, "w"), indent=2)
        print("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
