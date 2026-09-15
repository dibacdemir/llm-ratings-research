#!/usr/bin/env python
"""Do models rank the same way on different tasks, and do the metrics agree?

Two questions a single-task result cannot answer:

  1. **Across tasks** — if Qwen3.5-9B beats OLMo-3-7B on amouyal, does it still
     beat it on lancaster? Kendall tau between the per-task model orderings.
  2. **Across metrics** — does ordering models by Pearson give the same answer
     as ordering them by W1/delta? If not, "which model is best" depends on
     which question you asked, and that is the whole point of the project.

    python scripts/rank_stability.py                      # uses result/
    python scripts/rank_stability.py --metric pearson
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import dist  # noqa: E402

METRICS = {
    # name: (key, higher_is_better)
    "pearson": ("mean_level_pearson_r", True),
    "spearman": ("mean_level_spearman_r", True),
    "W1": ("median_W1", False),
    "W1_over_delta": ("median_W1_over_delta", False),
    "align": (("alignment", "normalized"), True),
    "equiv": ("frac_similar", True),
}


def kendall_tau(x, y):
    """Tau-b on the paired vectors x, y."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 3:
        return float("nan")
    con = dis = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 and dy == 0:
                tx += 1; ty += 1
            elif dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0) == (dy > 0):
                con += 1
            else:
                dis += 1
    d = np.sqrt((con + dis + tx) * (con + dis + ty))
    return (con - dis) / d if d else float("nan")


def get(summary, key):
    if isinstance(key, tuple):
        v = summary
        for k in key:
            v = (v or {}).get(k)
        return v
    v = summary.get(key)
    if v is None and key == "median_W1_over_delta":
        w, d = summary.get("median_W1"), summary.get("median_delta")
        return (w / d) if w and d else None
    return v


def load(root, min_mass):
    """{task: {model: summary}}, dropping runs whose option_mass is too low."""
    out, dropped = {}, []
    for path in sorted(glob.glob(os.path.join(root, "*", "*.summary.json"))):
        s = json.load(open(path))
        model = os.path.basename(os.path.dirname(path))
        stem = os.path.basename(path).split(".jsonl")[0]
        task = s.get("task") or stem
        mass = s.get("mean_option_mass")
        if mass is not None and mass < min_mass:
            dropped.append("%s/%s (mass %.2f)" % (model, stem, mass))
            continue
        # prefer an __autofmt rerun of the same model+task over the original
        prev = out.setdefault(task, {}).get(model)
        if prev is not None:
            keep_new = ("__autofmt" in stem) or (
                (mass or 0) > (prev.get("mean_option_mass") or 0))
            if not keep_new:
                continue
        s["_stem"] = stem
        out[task][model] = s
    return out, dropped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="result")
    ap.add_argument("--metric", default="W1_over_delta", choices=list(METRICS))
    ap.add_argument("--min-mass", type=float, default=0.9,
                    help="ignore runs whose mean option_mass is below this")
    ap.add_argument("--min-models", type=int, default=3,
                    help="a task pair needs this many shared models to compare")
    args = ap.parse_args(argv)

    by_task, dropped = load(args.root, args.min_mass)
    if dropped:
        print("dropped %d run(s) for low option_mass:" % len(dropped))
        for d in dropped:
            print("  " + d)
        print()

    key, higher = METRICS[args.metric]
    tasks = sorted(by_task)
    print("== per-task model ordering by %s (%s is better) ==\n"
          % (args.metric, "higher" if higher else "lower"))
    for t in tasks:
        rows = [(m, get(s, key)) for m, s in by_task[t].items()]
        rows = [(m, v) for m, v in rows if v is not None]
        if not rows:
            continue
        rows.sort(key=lambda r: r[1], reverse=higher)
        print("%s (n=%d)" % (t, len(rows)))
        for m, v in rows:
            print("    %-32s %.3f" % (m, v))
        print()

    print("== Kendall tau between tasks (models shared by both) ==")
    hdr = "%-42s %6s %s" % ("task pair", "shared", "tau")
    print(hdr); print("-" * len(hdr))
    any_pair = False
    for i, a in enumerate(tasks):
        for b in tasks[i + 1:]:
            shared = sorted(set(by_task[a]) & set(by_task[b]))
            va = [get(by_task[a][m], key) for m in shared]
            vb = [get(by_task[b][m], key) for m in shared]
            pairs = [(x, y) for x, y in zip(va, vb) if x is not None and y is not None]
            if len(pairs) < args.min_models:
                continue
            any_pair = True
            tau = kendall_tau([p[0] for p in pairs], [p[1] for p in pairs])
            print("%-42s %6d %+.3f" % ("%s / %s" % (a[:18], b[:18]), len(pairs), tau))
    if not any_pair:
        print("  (no task pair shares >= %d models yet)" % args.min_models)

    print("\n== Kendall tau between metrics, within each task ==")
    hdr = "%-34s %-16s %-16s %6s %s" % ("task", "metric A", "metric B", "n", "tau")
    print(hdr); print("-" * len(hdr))
    names = list(METRICS)
    for t in tasks:
        models = sorted(by_task[t])
        if len(models) < args.min_models:
            continue
        for i, ma in enumerate(names):
            for mb in names[i + 1:]:
                ka, ha = METRICS[ma]
                kb, hb = METRICS[mb]
                xa = [get(by_task[t][m], ka) for m in models]
                xb = [get(by_task[t][m], kb) for m in models]
                pr = [(x, y) for x, y in zip(xa, xb) if x is not None and y is not None]
                if len(pr) < args.min_models:
                    continue
                # orient both so that "higher is better" before comparing
                sa = 1 if ha else -1
                sb = 1 if hb else -1
                tau = kendall_tau([sa * p[0] for p in pr], [sb * p[1] for p in pr])
                if ma == "pearson" and mb in ("W1_over_delta", "align", "equiv"):
                    print("%-34s %-16s %-16s %6d %+.3f"
                          % (t[:34], ma, mb, len(pr), tau))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
