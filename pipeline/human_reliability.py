#!/usr/bin/env python
"""Split-half reliability of the human ratings, written into each task's metadata.

For every task in data/ that has individual ratings, the raters of each item
are split at random into two halves, the item means of the two halves are
correlated across items, and the correlation is Spearman-Brown corrected
(2r / (1 + r)) to estimate the reliability of the full sample. The median over
--n-splits random splits is kept. Both Pearson and Spearman are reported: the
Spearman one is the ceiling for the model-human rank correlation on the pages.

Same definition as Diba's presentation/build_catalog.py from summer 2026
(archive/presentation_2026_summer), vectorised so the 40k-item norms run in
seconds.

    python pipeline/human_reliability.py            # writes metadata.json + data/INDEX.csv
    python pipeline/human_reliability.py --dry-run  # print only

Result, in data/<level>/<task>/metadata.json:

    "human_reliability": {"pearson_sb": 0.93, "spearman_sb": 0.92,
                          "n_items_used": 853, "min_raters": 2,
                          "n_splits": 100, "method": "split-half, Spearman-Brown"}
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data  # noqa: E402


def _rank(a):
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(1, len(a) + 1)
    # average ties, so this matches scipy.stats.rankdata
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    return sums[inv] / counts[inv]


def _pearson(x, y):
    x = x - x.mean()
    y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else float("nan")


def split_half(ratings, n_splits=100, seed=0, min_raters=2):
    """ratings: list of 1-d arrays, one per item. Returns the summary dict.

    Items are grouped by their number of raters so each group is a dense
    (items x raters) matrix; one item with 16,000 raters (lancaster2020) would
    otherwise pad every row to that width and need gigabytes."""
    items = [np.asarray(r, float) for r in ratings if len(r) >= min_raters]
    if len(items) < 3:
        return None
    n = np.array([len(r) for r in items])
    groups = {}
    for i, k in enumerate(n):
        groups.setdefault(int(k), []).append(i)
    mats = {k: (np.array(idx), np.stack([items[i] for i in idx])) for k, idx in groups.items()}
    rng = np.random.default_rng(seed)
    pear, spear = [], []
    a = np.empty(len(items))
    b = np.empty(len(items))
    for _ in range(n_splits):
        for k, (idx, M) in mats.items():
            # a random permutation of each item's raters; the first floor(k/2)
            # form half A, the rest half B
            order = np.argsort(rng.random(M.shape), axis=1)
            P = np.take_along_axis(M, order, axis=1)
            h = k // 2
            a[idx] = P[:, :h].mean(axis=1)
            b[idx] = P[:, h:].mean(axis=1)
        r = _pearson(a, b)
        rho = _pearson(_rank(a), _rank(b))
        pear.append(2 * r / (1 + r) if r > -1 else float("nan"))
        spear.append(2 * rho / (1 + rho) if rho > -1 else float("nan"))
    return {"pearson_sb": round(float(np.nanmedian(pear)), 3),
            "spearman_sb": round(float(np.nanmedian(spear)), 3),
            "n_items_used": int(len(items)), "min_raters": min_raters,
            "n_splits": n_splits, "method": "split-half, Spearman-Brown"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-splits", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="one task name")
    args = ap.parse_args(argv)

    done, skipped = 0, 0
    for task, source, csv_path, _ in data.list_tasks():
        if args.only and task != args.only:
            continue
        items = data.load_items(csv_path)
        trial = [it["individual"] for it in items if it["individual"]]
        rel = split_half(trial, n_splits=args.n_splits) if trial else None
        metap = os.path.join(os.path.dirname(csv_path), "metadata.json")
        if rel is None:
            skipped += 1
            print("%-52s %-9s  no individual ratings" % (task, source))
            rel = {"pearson_sb": None, "spearman_sb": None, "n_items_used": 0,
                   "min_raters": 2, "n_splits": 0,
                   "method": "not computable: means only"}
        else:
            done += 1
            print("%-52s %-9s  r_sb %.3f  rho_sb %.3f  (%d items)"
                  % (task, source, rel["pearson_sb"], rel["spearman_sb"],
                     rel["n_items_used"]))
        if not args.dry_run:
            with open(metap, encoding="utf-8") as fh:
                meta = json.load(fh)
            meta["human_reliability"] = rel
            with open(metap, "w", encoding="utf-8") as fh:
                json.dump(meta, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
    print("\n%d tasks with reliability, %d means-only" % (done, skipped))
    if not args.dry_run and not args.only:
        import build_index
        build_index.main([])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
