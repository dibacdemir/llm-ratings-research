#!/usr/bin/env python
"""Collate every result/<model>/<task>.summary.json into one table.

    python scripts/collate.py                  # printed table
    python scripts/collate.py --csv out.csv    # and a CSV

Columns: the mean-level correlations everyone reports, next to the
distribution-level numbers, so it is obvious when a model tracks the human
means but not the human distributions.
"""

import argparse
import csv
import glob
import json
import os
import sys

COLS = [
    ("model", "{}", 26),
    ("task", "{}", 42),
    ("n", "{}", 6),
    ("med_n", "{:.0f}", 6),
    ("pearson", "{:.3f}", 8),
    ("spearman", "{:.3f}", 9),
    ("W1", "{:.3f}", 7),
    ("delta", "{:.3f}", 7),
    ("W1/dlt", "{:.2f}", 7),
    ("similar", "{:.0%}", 8),
    ("align", "{:.3f}", 7),
    ("mass", "{:.3f}", 6),
]


def rows(root):
    for path in sorted(glob.glob(os.path.join(root, "*", "*.summary.json"))):
        try:
            s = json.load(open(path))
        except Exception as exc:
            print("skip %s: %s" % (path, exc), file=sys.stderr)
            continue
        a = s.get("alignment") or {}
        # The file stem, not summary["task"]: the same task can be run more than
        # once under different prompt formats (foo__autofmt.jsonl) and those
        # rows have to stay distinguishable.
        stem = os.path.basename(path).split(".jsonl")[0]
        yield {
            "model": os.path.basename(os.path.dirname(path)),
            "task": stem or s.get("task", "?"),
            "n": s.get("n_items_evaluated"),
            "med_n": s.get("median_n_raters"),
            "pearson": s.get("mean_level_pearson_r"),
            "spearman": s.get("mean_level_spearman_r"),
            "W1": s.get("median_W1"),
            "delta": s.get("median_delta"),
            # only present in runs scored after the ratio was added; fall back
            # to the quotient of the two medians so older rows still show one
            "W1/dlt": s.get("median_W1_over_delta") or (
                (s["median_W1"] / s["median_delta"])
                if s.get("median_W1") and s.get("median_delta") else None),
            "similar": s.get("frac_similar"),
            "align": a.get("normalized"),
            "mass": s.get("mean_option_mass"),
            "_path": path,
        }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="result")
    ap.add_argument("--csv", help="also write a CSV here")
    args = ap.parse_args(argv)

    data = list(rows(args.root))
    if not data:
        print("no summaries under %s/" % args.root, file=sys.stderr)
        return 1

    header = "  ".join(("%-*s" % (w, name)) for name, _f, w in COLS)
    print(header)
    print("-" * len(header))
    for r in data:
        cells = []
        for name, fmt, w in COLS:
            v = r.get(name)
            try:
                s = fmt.format(v)
            except (TypeError, ValueError):
                s = "-" if v is None else str(v)
            cells.append("%-*s" % (w, s[:w]))
        print("  ".join(cells))

    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=[c[0] for c in COLS] + ["_path"])
            w.writeheader()
            w.writerows(data)
        print("\nwrote %s" % args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
