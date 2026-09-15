#!/usr/bin/env python
"""What the human data looks like: metadata/catalog.csv, the figures, a README.

Everything is generated from data/<level>/<task>/metadata.json (run
pipeline/human_reliability.py first so the reliability column is filled).
No number in metadata/ is typed by hand.

    python pipeline/build_metadata.py

Writes
    metadata/catalog.csv            one row per dataset, every metadata field flattened
    metadata/fig_levels.{png,pdf}   tasks, items and ratings per level
    metadata/fig_reliability.*      split-half reliability of the raters, per level
    metadata/fig_size.*             items x raters per item, one dot per dataset
    metadata/README.md              the headline numbers, and the figures
"""

import csv
import json
import os
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, task_meta  # noqa: E402

# the reference palette from the dataviz guidance; one hue for magnitude,
# fixed categorical order for the three sources
INK, INK2, MUTED, SURFACE = "#0b0b0b", "#52514e", "#898781", "#fcfcfb"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SOURCE_COLOR = {"published": BLUE, "surveyor": ORANGE, "mturk": AQUA}
SOURCE_LABEL = {"published": "Published norms", "surveyor": "TedLab surveyor",
                "mturk": "TedLab MTurk"}
LEVELS = task_meta.LEVEL_ORDER
LABEL = task_meta.LEVEL_LABEL

COLUMNS = ["task", "level", "sublevel", "source", "language", "scale",
           "n_items", "n_ratings", "ratings_per_item_min", "ratings_per_item_median",
           "ratings_per_item_max", "has_individual_ratings",
           "human_r_sb", "human_rho_sb", "reliability_items_used",
           "level_decided_by", "level_blind_check_agrees", "level_rationale",
           "merged_from", "question_wording", "path"]


def load():
    root = data.repo_root()
    rows = []
    for task, source, csv_path, _ in data.list_tasks():
        d = os.path.dirname(csv_path)
        with open(os.path.join(d, "metadata.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        rel = m.get("human_reliability") or {}
        rows.append({
            "task": task, "level": m.get("level", ""), "sublevel": m.get("sublevel") or "",
            "source": source, "language": m.get("language", ""),
            "scale": "%d-%d" % tuple(m["scale"]) if m.get("scale") else "",
            "n_items": m.get("n_items"), "n_ratings": m.get("n_ratings"),
            "ratings_per_item_min": m.get("ratings_per_item_min"),
            "ratings_per_item_median": m.get("ratings_per_item_median"),
            "ratings_per_item_max": m.get("ratings_per_item_max"),
            "has_individual_ratings": bool(m.get("has_individual_ratings")),
            "human_r_sb": rel.get("pearson_sb"), "human_rho_sb": rel.get("spearman_sb"),
            "reliability_items_used": rel.get("n_items_used"),
            "level_decided_by": m.get("level_decided_by", ""),
            "level_blind_check_agrees": m.get("level_blind_check_agrees"),
            "level_rationale": m.get("level_rationale", ""),
            "merged_from": ";".join(m.get("merged_from", [])),
            "question_wording": (m.get("provenance") or {}).get("question_wording", ""),
            "path": os.path.relpath(d, root),
        })
    rows.sort(key=lambda r: (LEVELS.index(r["level"]) if r["level"] in LEVELS else 99, r["task"]))
    return rows


def write_catalog(rows, out):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in COLUMNS})


def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=INK2, labelsize=9, length=3, color=MUTED)
    ax.set_facecolor(SURFACE)
    ax.grid(False)


def fig_levels(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    by = defaultdict(list)
    for r in rows:
        by[r["level"]].append(r)
    levels = [lv for lv in LEVELS if by[lv]]
    panels = [("Rating tasks", [len(by[lv]) for lv in levels], "{:,}"),
              ("Items (words or sentences)", [sum(r["n_items"] or 0 for r in by[lv]) for lv in levels], "{:,}"),
              ("Individual human ratings", [sum(r["n_ratings"] or 0 for r in by[lv]) for lv in levels], "{:,}")]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), facecolor=SURFACE)
    y = list(range(len(levels)))[::-1]
    for ax, (title, vals, fmt) in zip(axes, panels):
        _style(ax)
        ax.barh(y, vals, color=BLUE, height=0.62)
        ax.set_yticks(y)
        ax.set_yticklabels([LABEL.get(lv, lv) for lv in levels], color=INK)
        ax.set_title(title, loc="left", fontsize=10.5, color=INK, pad=8)
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
        xmax = max(vals) or 1
        for yi, v in zip(y, vals):
            ax.text(v + xmax * 0.02, yi, fmt.format(v), va="center", fontsize=8.5, color=INK2)
        ax.set_xlim(0, xmax * 1.25)
        if ax is not axes[0]:
            ax.set_yticklabels([])
            ax.tick_params(axis="y", length=0)
    fig.tight_layout(w_pad=1.5)
    fig.savefig(out + ".png", dpi=300)
    fig.savefig(out + ".pdf")
    plt.close(fig)


def fig_reliability(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    by = defaultdict(list)
    for r in rows:
        if r["human_rho_sb"] is not None:
            by[r["level"]].append(r["human_rho_sb"])
    levels = [lv for lv in LEVELS if by[lv]]
    fig, ax = plt.subplots(figsize=(7.5, 3.8), facecolor=SURFACE)
    _style(ax)
    rng = np.random.default_rng(0)
    for i, lv in enumerate(levels):
        vals = np.array(by[lv])
        jitter = rng.uniform(-0.18, 0.18, len(vals))
        ax.scatter(vals, i + jitter, s=14, color=BLUE, alpha=0.55, linewidths=0)
        med = float(np.median(vals))
        ax.plot([med, med], [i - 0.3, i + 0.3], color=INK, linewidth=2)
        ax.text(1.02, i, "median %.2f · n=%d" % (med, len(vals)), va="center",
                fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(levels)))
    ax.set_yticklabels([LABEL.get(lv, lv) for lv in levels], color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("split-half reliability of the raters' item means (Spearman ρ, Spearman-Brown corrected)",
                  fontsize=9, color=INK2)
    ax.set_title("How much the raters agree with each other — the ceiling for any model",
                 loc="left", fontsize=10.5, color=INK, pad=8)
    n_none = sum(1 for r in rows if r["human_rho_sb"] is None)
    ax.text(0.0, -0.22, "%d datasets with item means only are not shown" % n_none,
            transform=ax.transAxes, fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(out + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)


def fig_size(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.2), facecolor=SURFACE)
    _style(ax)
    for src in ("published", "surveyor", "mturk"):
        xs = [r["n_items"] for r in rows if r["source"] == src and r["ratings_per_item_median"]]
        ys = [r["ratings_per_item_median"] for r in rows if r["source"] == src and r["ratings_per_item_median"]]
        ax.scatter(xs, ys, s=22, color=SOURCE_COLOR[src], alpha=0.75, linewidths=0.8,
                   edgecolors=SURFACE, label="%s (%d)" % (SOURCE_LABEL[src], len(xs)))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("items in the dataset", fontsize=9, color=INK2)
    ax.set_ylabel("raters per item (median)", fontsize=9, color=INK2)
    ax.set_title("Two kinds of dataset: large published norms, small lab experiments",
                 loc="left", fontsize=10.5, color=INK, pad=8)
    leg = ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    for t in leg.get_texts():
        t.set_color(INK2)
    n_none = sum(1 for r in rows if not r["ratings_per_item_median"])
    if n_none:
        ax.text(0.0, -0.16, "%d datasets with item means only (no rater counts) are not shown" % n_none,
                transform=ax.transAxes, fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(out + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(out + ".pdf", bbox_inches="tight")
    plt.close(fig)


def readme(rows):
    by_level = defaultdict(list)
    by_source = defaultdict(list)
    for r in rows:
        by_level[r["level"]].append(r)
        by_source[r["source"]].append(r)
    rel = [r["human_rho_sb"] for r in rows if r["human_rho_sb"] is not None]
    relp = [r["human_r_sb"] for r in rows if r["human_r_sb"] is not None]

    def sums(rs):
        return (len(rs), sum(r["n_items"] or 0 for r in rs), sum(r["n_ratings"] or 0 for r in rs))

    L = ["# metadata/", "",
         "What the human data looks like. Generated by `pipeline/build_metadata.py` from",
         "`data/*/*/metadata.json`; do not edit by hand.", "",
         "- `catalog.csv` — one row per dataset: level, source, size, scale, split-half",
         "  reliability, who decided the level and why.",
         "- `fig_levels` — tasks, items and ratings per level.",
         "- `fig_reliability` — the raters' split-half reliability per level, the ceiling",
         "  any model-human correlation can reach.",
         "- `fig_size` — items × raters per item, one dot per dataset.", "",
         "## Headline numbers", ""]
    n, it, ra = sums(rows)
    L.append("**%d rating tasks** across 7 levels, **%s items** (words or sentences × property), "
             "**%s individual human ratings**." % (n, "{:,}".format(it), "{:,}".format(ra)))
    L.append("Human data is reliable: median split-half **ρ = %.2f** (Spearman-Brown corrected; "
             "Pearson r = %.2f) over the %d tasks with individual responses."
             % (st.median(rel), st.median(relp), len(rel)))
    L += ["", "### By level", "", "| level | tasks | items | ratings | items / task (median) | raters / item (median) | median reliability ρ |",
          "|---|--:|--:|--:|--:|--:|--:|"]
    for lv in LEVELS:
        rs = by_level.get(lv, [])
        if not rs:
            continue
        n, it, ra = sums(rs)
        rpi = [r["ratings_per_item_median"] for r in rs if r["ratings_per_item_median"]]
        rr = [r["human_rho_sb"] for r in rs if r["human_rho_sb"] is not None]
        L.append("| %s | %d | %s | %s | %d | %s | %s |" % (
            LABEL.get(lv, lv), n, "{:,}".format(it), "{:,}".format(ra),
            st.median([r["n_items"] for r in rs]),
            ("%d" % st.median(rpi)) if rpi else "—",
            ("%.2f (n=%d)" % (st.median(rr), len(rr))) if rr else "—"))
    L += ["", "### By source", "", "| source | tasks | items | ratings | with individual ratings |", "|---|--:|--:|--:|--:|"]
    for src in ("published", "surveyor", "mturk"):
        rs = by_source.get(src, [])
        n, it, ra = sums(rs)
        L.append("| %s | %d | %s | %s | %d |" % (SOURCE_LABEL[src], n, "{:,}".format(it),
                                                "{:,}".format(ra), sum(1 for r in rs if r["has_individual_ratings"])))
    L += ["", "## Figures", "",
          "![tasks, items and ratings per level](fig_levels.png)", "",
          "![split-half reliability per level](fig_reliability.png)", "",
          "![items x raters per item](fig_size.png)", "",
          "## Reliability, defined", "",
          "For each dataset with individual ratings, the raters of every item are split at",
          "random into two halves; the two halves' item means are correlated across items",
          "(Pearson and Spearman) and Spearman-Brown corrected, 2r/(1+r), to estimate the",
          "reliability of the full sample. The median over 100 random splits is kept.",
          "Same definition as Diba's summer 2026 catalog (`archive/presentation_2026_summer`).",
          "A model's rank correlation with the human means cannot be expected to exceed",
          "the Spearman value; the Item Inspector shows it as the human ceiling.", ""]
    return "\n".join(L)


def main(argv=None):
    root = data.repo_root()
    out = os.path.join(root, "metadata")
    os.makedirs(out, exist_ok=True)
    rows = load()
    write_catalog(rows, os.path.join(out, "catalog.csv"))
    fig_levels(rows, os.path.join(out, "fig_levels"))
    fig_reliability(rows, os.path.join(out, "fig_reliability"))
    fig_size(rows, os.path.join(out, "fig_size"))
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme(rows))
    print("wrote metadata/: catalog.csv (%d rows), 3 figures, README.md" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
