#!/usr/bin/env python
"""Summarise the regression approach next to the ratings approach.

Reads analysis/regress/<model>.csv (one row per model x task x N, from
regress_pilot.py) and writes, in analysis/regress/:

    summary.txt         per level: regression r, ratings r, human reliability,
                        number of tasks; plus where in the network the best
                        layer sits
    fig_regress_vs_ratings.png   per level, regression (N=200 / 300) beside
                        ratings, each divided by the task's split-half reliability
    fig_task_scatter.png   one dot per model x task: ratings r vs regression r
    fig_layers.png      relative depth of the chosen layer, per level

    python pipeline/regress_summary.py
"""

import csv
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_ratings import task_meta  # noqa: E402

LV = ["sentence_semantics", "syntax", "discourse", "lexical_semantics", "subword", "pragmatics"]
LAB = task_meta.LEVEL_LABEL
COL = dict(zip(LV, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]))
INK, INK2, MUTED, SF = "#0b0b0b", "#52514e", "#898781", "#fcfcfb"


def load():
    rows = []
    for f in glob.glob("analysis/regress/*.csv"):
        for r in csv.DictReader(open(f)):
            for k in ("n", "test_r_mean", "test_r_sd", "best_layer", "n_layers", "alpha",
                      "ratings_pearson", "ratings_spearman", "ratings_mass", "human_rho_sb"):
                r[k] = float(r[k]) if r[k] not in ("", None) else np.nan
            r["dev_curve"] = json.loads(r["dev_curve"])
            rows.append(r)
    return rows


def style(ax):
    ax.set_facecolor(SF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=8)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    R = load()
    models = sorted({r["model"] for r in R})
    L = ["Regression approach (ridge on hidden states) next to the ratings approach",
         "%d models: %s" % (len(models), ", ".join(models)),
         "tasks: English, split-half reliability >= 0.7, >= 200 items; r = Pearson on a held-out 15%,",
         "averaged over 10 resamples; 'share' = r / split-half reliability (Spearman-Brown)", ""]

    # per level, per N
    agg = {}
    for n in (200, 300):
        L.append("N = %d" % n)
        L.append("   %-19s %6s %10s %10s %10s %10s" % ("level", "tasks", "regr r", "regr/ceil", "ratings r", "rat/ceil"))
        for lv in LV:
            rr = [r for r in R if r["level"] == lv and r["n"] == n and np.isfinite(r["test_r_mean"]) and r["ratings_mass"] >= 0.9]
            if not rr:
                continue
            # median over tasks of the per-model value, then mean over models
            per_model = defaultdict(list)
            for r in rr:
                per_model[r["model"]].append((r["test_r_mean"], r["test_r_mean"] / r["human_rho_sb"],
                                              r["ratings_pearson"], r["ratings_pearson"] / r["human_rho_sb"]))
            med = np.array([np.median(np.array(v), 0) for v in per_model.values()])
            m = med.mean(0)
            agg[(lv, n)] = m
            L.append("   %-19s %6d %10.2f %10.2f %10.2f %10.2f" % (LAB[lv], len({r["task"] for r in rr}), *m))
        L.append("")

    # layers
    L.append("Where the chosen layer sits (relative depth, 0 = embeddings, 1 = last layer), N = 300 where available else 200:")
    depth = defaultdict(list)
    for r in R:
        if r["ratings_mass"] < 0.9:
            continue
        depth[(r["level"], r["model"], r["task"])] = r["best_layer"] / r["n_layers"] if r["n"] == 300 else depth.get((r["level"], r["model"], r["task"]), r["best_layer"] / r["n_layers"])
    by_lv = defaultdict(list)
    for (lv, _, _), d in depth.items():
        by_lv[lv].append(d)
    for lv in LV:
        if by_lv[lv]:
            L.append("   %-19s median %.2f   IQR %.2f-%.2f   (n=%d)" % (
                LAB[lv], np.median(by_lv[lv]), *np.percentile(by_lv[lv], [25, 75]), len(by_lv[lv])))
    L.append("")

    # gap: tasks where regression >> ratings
    L.append("Largest gaps, regression share minus ratings share (N=300 or 200, mean over models):")
    gap = defaultdict(list)
    for r in R:
        if r["ratings_mass"] >= 0.9 and np.isfinite(r["test_r_mean"]):
            gap[(r["task"], r["level"])].append((r["test_r_mean"] - r["ratings_pearson"]) / r["human_rho_sb"])
    g = sorted(((np.mean(v), t, lv) for (t, lv), v in gap.items()), reverse=True)
    for v, t, lv in g[:8]:
        L.append("   %+.2f  %-50s %s" % (v, t[:50], LAB[lv]))
    L.append("   ...")
    for v, t, lv in g[-5:]:
        L.append("   %+.2f  %-50s %s" % (v, t[:50], LAB[lv]))
    open("analysis/regress/summary.txt", "w").write("\n".join(L) + "\n")
    print("\n".join(L))

    # fig 1: per level bars
    fig, ax = plt.subplots(figsize=(9, 4.4), facecolor=SF); style(ax)
    lvs = [lv for lv in LV if (lv, 200) in agg]
    x = np.arange(len(lvs)); w = 0.26
    for i, (key, lab, c) in enumerate([("rat", "ratings (ask for a number)", "#898781"), (200, "regression, N=200", "#86b6ef"), (300, "regression, N=300", "#2a78d6")]):
        vals = []
        for lv in lvs:
            if key == "rat":
                vals.append(agg[(lv, 200)][3])
            else:
                vals.append(agg[(lv, key)][1] if (lv, key) in agg else np.nan)
        ax.bar(x + (i - 1) * w, vals, w, color=c, label=lab, edgecolor=SF)
        for xi, v in zip(x, vals):
            if np.isfinite(v):
                ax.text(xi + (i - 1) * w, v + 0.01, "%.2f" % v, ha="center", fontsize=6.5, color=INK2)
    ax.set_xticks(x); ax.set_xticklabels([LAB[lv].replace(" ", "\n") for lv in lvs], fontsize=8.5, color=INK)
    ax.set_ylim(0, 1.05); ax.axhline(1, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.set_ylabel("share of the human ceiling\n(r ÷ split-half reliability)", fontsize=8.5, color=INK2)
    ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0))
    ax.set_title("What the model encodes (regression) vs what it reports (ratings), %d models at 7-12B" % len(models), loc="left", fontsize=10, color=INK, pad=22)
    fig.tight_layout(); fig.savefig("analysis/regress/fig_regress_vs_ratings.png", dpi=220); plt.close(fig)

    # fig 2: scatter
    fig, ax = plt.subplots(figsize=(6, 6), facecolor=SF); style(ax)
    for lv in LV:
        pts = [(r["ratings_pearson"], r["test_r_mean"]) for r in R if r["level"] == lv and r["n"] == 200 and r["ratings_mass"] >= 0.9]
        if pts:
            ax.scatter(*zip(*pts), s=16, color=COL[lv], alpha=0.65, linewidths=0, label="%s (%d)" % (LAB[lv], len(pts)))
    ax.plot([-0.2, 1], [-0.2, 1], color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.set_xlim(-0.2, 1); ax.set_ylim(-0.2, 1)
    ax.set_xlabel("ratings: r(expected rating, human mean)", fontsize=9, color=INK2)
    ax.set_ylabel("regression: r(predicted, human mean), N=200", fontsize=9, color=INK2)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    ax.set_title("One dot per model × task", loc="left", fontsize=10, color=INK)
    fig.tight_layout(); fig.savefig("analysis/regress/fig_task_scatter.png", dpi=220); plt.close(fig)

    # fig 3: layer depth
    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SF); style(ax)
    rng = np.random.default_rng(0)
    for i, lv in enumerate([lv for lv in LV if by_lv[lv]]):
        v = np.array(by_lv[lv]); ax.scatter(v, i + rng.uniform(-0.2, 0.2, len(v)), s=12, color=COL[lv], alpha=0.5, linewidths=0)
        ax.plot([np.median(v)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
    ax.set_yticks(range(len([lv for lv in LV if by_lv[lv]]))); ax.set_yticklabels([LAB[lv] for lv in LV if by_lv[lv]], fontsize=8.5, color=INK)
    ax.invert_yaxis(); ax.set_xlim(0, 1)
    ax.set_xlabel("relative depth of the best layer (0 = embeddings, 1 = last layer)", fontsize=9, color=INK2)
    ax.set_title("Which layer predicts the human ratings best", loc="left", fontsize=10, color=INK)
    fig.tight_layout(); fig.savefig("analysis/regress/fig_layers.png", dpi=220); plt.close(fig)
    print("\nwrote analysis/regress/")


if __name__ == "__main__":
    main()
