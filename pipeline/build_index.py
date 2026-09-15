#!/usr/bin/env python
"""Regenerate data/INDEX.csv from the metadata.json files: one row per task.

The metadata files are the source of truth; INDEX.csv is a flat view of them
for grep and spreadsheets. Run after anything that edits metadata
(pipeline/human_reliability.py does it for you).

    python pipeline/build_index.py
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, task_meta  # noqa: E402

COLUMNS = ["task", "level", "sublevel", "source", "language", "scale",
           "n_items", "n_ratings", "ratings_per_item", "individual_ratings",
           "human_r_sb", "human_rho_sb", "merged_from", "path"]


def rows():
    root = data.repo_root()
    for task, source, csv_path, _ in data.list_tasks():
        d = os.path.dirname(csv_path)
        with open(os.path.join(d, "metadata.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        rel = m.get("human_reliability") or {}
        yield {
            "task": task, "level": m.get("level", ""),
            "sublevel": m.get("sublevel") or "", "source": source,
            "language": m.get("language", ""),
            "scale": "%d-%d" % tuple(m["scale"]) if m.get("scale") else "",
            "n_items": m.get("n_items", ""), "n_ratings": m.get("n_ratings", ""),
            "ratings_per_item": m.get("ratings_per_item_median") or "",
            "individual_ratings": "yes" if m.get("has_individual_ratings") else "no",
            "human_r_sb": rel.get("pearson_sb") if rel.get("pearson_sb") is not None else "",
            "human_rho_sb": rel.get("spearman_sb") if rel.get("spearman_sb") is not None else "",
            "merged_from": ";".join(m.get("merged_from", [])),
            "path": os.path.relpath(d, root),
        }


def main(argv=None):
    root = data.repo_root()
    out = os.path.join(root, data.DATA_DIR, "INDEX.csv")
    rs = sorted(rows(), key=lambda r: (task_meta.LEVEL_ORDER.index(r["level"])
                                       if r["level"] in task_meta.LEVEL_ORDER else 99,
                                       r["task"]))
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rs)
    print("wrote %s: %d tasks" % (os.path.relpath(out, root), len(rs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
