#!/usr/bin/env python
"""Pilot: is there a "g" of language, and what is left once it is removed?

Matrix: models (rows) x tasks (columns), each cell the model's rank correlation
with the human means divided by the task's split-half reliability. Same numbers
as pilot_hierarchy (analysis/pilot_hierarchy/pairs.csv).

Restrictions, so that scale does not swamp everything and noise does not fake
structure: models >= 7B that answer with a digit on most tasks; tasks with
reliability >= 0.7; tasks from one study that ask the same kind of question
(lancaster2020_*, troche2014_*, ...) are averaged into one column.

Steps
  1. g: first principal component of the model x task matrix. Variance
     explained, and every task's loading on it.
  2. after g: each row is centred (the model's mean over tasks removed), which
     takes out the general factor; then PCA again. Parallel analysis (random
     matrices of the same shape) says how many components are above chance.
  3. structure vs Andrea's levels: hierarchical clustering of the tasks on the
     residual correlations, cut into k = number of levels; adjusted Rand index
     against the level labels, with a permutation baseline.

Outputs in analysis/pilot_factors/: loadings.csv, summary.txt, fig_scree.png,
fig_pcs.png (tasks on the first two residual components, coloured by level),
fig_corr.png (residual task correlations ordered by cluster).
"""

import csv
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_ratings import data, task_meta  # noqa: E402

LEVELS = ["subword", "lexical_semantics", "syntax", "sentence_semantics", "pragmatics", "discourse"]
LEVEL_COLOR = dict(zip(LEVELS, ["#e87ba4", "#eda100", "#eb6834", "#2a78d6", "#4a3aa7", "#1baf7a"]))
INK, INK2, MUTED, SURFACE = "#0b0b0b", "#52514e", "#898781", "#fcfcfb"
MIN_PARAMS, MIN_REL = 7.0, 0.7
# columns to merge: tasks sharing this prefix are one study asking one kind of question
MERGE_PREFIXES = ["lancaster2020_", "troche2014_", "scott2018_", "warriner2013_", "massive_mem_",
                  "tuckute2024_", "discourse_", "coherence_survey_", "pronouns_following_verbs",
                  "richard_islands_", "acd_project_", "sentence_naturalness_survey_for_",
                  "huang_response_", "lexical_frame_adjectives_", "gatti2024_", "winter20"]


def column_of(task):
    for p in MERGE_PREFIXES:
        if task.startswith(p):
            return p.rstrip("_")
    return task


def load(root):
    rows = list(csv.DictReader(open(os.path.join(root, "analysis/pilot_hierarchy/pairs.csv"))))
    for r in rows:
        for k in ("rho", "ceiling", "share", "mass_median", "params_b"):
            r[k] = float(r[k]) if r[k] not in ("", "None") else np.nan
    ok = [r for r in rows if r["mass_median"] >= 0.9 and np.isfinite(r["share"])
          and r["ceiling"] >= MIN_REL and r["params_b"] >= MIN_PARAMS and r["level"] in LEVELS]
    # models answering on most of their tasks
    tot = defaultdict(int); good = defaultdict(int)
    for r in rows:
        tot[r["model"]] += 1
    for r in ok:
        good[r["model"]] += 1
    models = sorted(m for m in good if good[m] / tot[m] >= 0.5)
    cols = sorted({column_of(r["task"]) for r in ok})
    level_of = {}
    cell = defaultdict(list)
    for r in ok:
        if r["model"] in models:
            cell[(r["model"], column_of(r["task"]))].append(r["share"])
            level_of.setdefault(column_of(r["task"]), r["level"])
    M = np.full((len(models), len(cols)), np.nan)
    for i, m in enumerate(models):
        for j, c in enumerate(cols):
            v = cell.get((m, c))
            if v:
                M[i, j] = np.mean(v)
    # drop columns missing for more than a quarter of the models, then fill the rest with the column mean
    keep = np.isnan(M).mean(axis=0) <= 0.25
    M, cols = M[:, keep], [c for c, k in zip(cols, keep) if k]
    colmean = np.nanmean(M, axis=0)
    M = np.where(np.isnan(M), colmean[None, :], M)
    return M, models, cols, [level_of[c] for c in cols]


def pca(X):
    Xc = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = S ** 2 / (S ** 2).sum()
    return var, Vt, U * S


def parallel_analysis(X, n_iter=500, seed=0):
    rng = np.random.default_rng(seed)
    n, p = X.shape
    out = []
    for _ in range(n_iter):
        R = rng.standard_normal((n, p))
        out.append(pca(R)[0][:min(n, p)])
    return np.percentile(np.array(out), 95, axis=0)


def cluster(C, k):
    """Average-linkage hierarchical clustering on 1 - correlation."""
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    D = 1 - C
    np.fill_diagonal(D, 0)
    D = np.clip((D + D.T) / 2, 0, 2)
    Z = linkage(squareform(D, checks=False), method="average")
    return fcluster(Z, k, criterion="maxclust"), Z


def ari(a, b):
    from sklearn.metrics import adjusted_rand_score
    return adjusted_rand_score(a, b)


def main():
    root = data.repo_root()
    out = os.path.join(root, "analysis", "pilot_factors")
    os.makedirs(out, exist_ok=True)
    M, models, cols, levels = load(root)
    n, p = M.shape
    L = ["Pilot: latent factors behind model differences",
         "%d models (>= %.0fB, answer on most tasks) x %d task columns (reliability >= %.1f, studies merged)"
         % (n, MIN_PARAMS, p, MIN_REL), ""]

    # 1. g
    var, Vt, scores = pca(M)
    C_raw = np.corrcoef(M.T)
    off = C_raw[np.triu_indices(p, 1)]
    L += ["1. A general factor",
          "   mean pairwise task correlation across models: %.2f (%.0f%% of pairs positive)"
          % (off.mean(), 100 * (off > 0).mean()),
          "   PC1 explains %.0f%% of the variance; PC2 %.0f%%, PC3 %.0f%%" % tuple(100 * var[:3]),
          "   PC1 loadings all the same sign: %s (min %.2f, max %.2f)"
          % ("yes" if (np.sign(Vt[0]) == np.sign(Vt[0][0])).all() else "no", Vt[0].min(), Vt[0].max()),
          "   -> the first component is a 'g': every task moves together with model capability", ""]
    g_by_level = defaultdict(list)
    for c, lv, ld in zip(cols, levels, Vt[0] * np.sign(Vt[0].mean())):
        g_by_level[lv].append(ld)
    L.append("   mean |g loading| by level: " + ", ".join(
        "%s %.2f" % (task_meta.LEVEL_LABEL[lv], np.mean(g_by_level[lv])) for lv in LEVELS if g_by_level[lv]))
    L.append("")

    # 2. after g
    R = M - M.mean(axis=1, keepdims=True)
    var_r, Vt_r, scores_r = pca(R)
    pa = parallel_analysis(R)
    n_sig = int(np.sum(var_r[:len(pa)] > pa))
    L += ["2. After removing each model's general level (row-centred)",
          "   residual PC1 %.0f%%, PC2 %.0f%%, PC3 %.0f%%, PC4 %.0f%%" % tuple(100 * var_r[:4]),
          "   parallel analysis (95th percentile of random): %d component(s) above chance" % n_sig, ""]

    # 3. clusters vs levels
    C_res = np.corrcoef(R.T)
    k = len(set(levels))
    lab, Z = cluster(C_res, k)
    a = ari(levels, lab)
    rng = np.random.default_rng(0)
    base = np.array([ari(rng.permutation(levels), lab) for _ in range(2000)])
    L += ["3. Do the residual clusters follow Andrea's levels?",
          "   %d clusters (one per level present); adjusted Rand index vs levels = %.3f" % (k, a),
          "   shuffled-label baseline: mean %.3f, 95th pct %.3f, p = %.3f" % (base.mean(), np.percentile(base, 95), (base >= a).mean()), ""]
    # which level dominates each cluster
    for ci in range(1, k + 1):
        members = [(c, lv) for c, lv, l in zip(cols, levels, lab) if l == ci]
        cnt = defaultdict(int)
        for _, lv in members:
            cnt[lv] += 1
        top = max(cnt.items(), key=lambda kv: kv[1])
        L.append("   cluster %d (%2d tasks): %s %d/%d   e.g. %s" % (
            ci, len(members), task_meta.LEVEL_LABEL[top[0]], top[1], len(members),
            ", ".join(c for c, _ in members[:4])))
    # within-level vs between-level residual correlation
    same = [C_res[i, j] for i in range(p) for j in range(i + 1, p) if levels[i] == levels[j]]
    diff = [C_res[i, j] for i in range(p) for j in range(i + 1, p) if levels[i] != levels[j]]
    L += ["", "   residual correlation, same level: %.3f; different level: %.3f" % (np.mean(same), np.mean(diff))]
    L.append("   by level (same-level mean): " + ", ".join(
        "%s %.2f" % (task_meta.LEVEL_LABEL[lv], np.mean([C_res[i, j] for i in range(p) for j in range(i + 1, p)
                                                          if levels[i] == lv and levels[j] == lv]))
        for lv in LEVELS if sum(1 for l in levels if l == lv) >= 2))

    with open(os.path.join(out, "loadings.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["task_column", "level", "g_loading", "resid_pc1", "resid_pc2", "cluster"])
        s = np.sign(Vt[0].mean())
        for j, c in enumerate(cols):
            w.writerow([c, levels[j], round(s * Vt[0][j], 4), round(Vt_r[0][j], 4), round(Vt_r[1][j], 4), int(lab[j])])
    open(os.path.join(out, "summary.txt"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    figures(out, var, var_r, pa, Vt_r, cols, levels, C_res, Z, lab)
    print("\nwrote", os.path.relpath(out, root))


def figures(out, var, var_r, pa, Vt_r, cols, levels, C_res, Z, lab):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import leaves_list

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), facecolor=SURFACE)
    for ax, v, title in ((axes[0], var, "raw: model x task"), (axes[1], var_r, "after removing each model's mean")):
        ax.set_facecolor(SURFACE)
        kk = min(10, len(v))
        ax.plot(range(1, kk + 1), 100 * v[:kk], "-o", color="#2a78d6", ms=4, lw=1.8, label="data")
        if ax is axes[1]:
            ax.plot(range(1, kk + 1), 100 * pa[:kk], "--", color=MUTED, lw=1.2, label="random (95th pct)")
            ax.legend(frameon=False, fontsize=8)
        ax.set_title(title, loc="left", fontsize=9.5, color=INK)
        ax.set_xlabel("component", fontsize=8.5, color=INK2); ax.set_ylabel("% variance", fontsize=8.5, color=INK2)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=INK2, labelsize=8)
    fig.suptitle("Scree: one general factor, then what?", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(os.path.join(out, "fig_scree.png"), dpi=220); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 6), facecolor=SURFACE); ax.set_facecolor(SURFACE)
    for lv in LEVELS:
        idx = [j for j, l in enumerate(levels) if l == lv]
        if not idx:
            continue
        ax.scatter(Vt_r[0][idx], Vt_r[1][idx], s=42, color=LEVEL_COLOR[lv], alpha=0.85,
                   edgecolors=SURFACE, linewidths=0.8, label="%s (%d)" % (task_meta.LEVEL_LABEL[lv], len(idx)))
    for j, c in enumerate(cols):
        if abs(Vt_r[0][j]) > np.percentile(np.abs(Vt_r[0]), 85) or abs(Vt_r[1][j]) > np.percentile(np.abs(Vt_r[1]), 85):
            ax.annotate(c[:28], (Vt_r[0][j], Vt_r[1][j]), fontsize=6, color=INK2, xytext=(3, 3), textcoords="offset points")
    ax.axhline(0, color=MUTED, lw=0.6); ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_xlabel("residual component 1 (%.0f%%)" % (100 * var_r[0]), fontsize=9, color=INK2)
    ax.set_ylabel("residual component 2 (%.0f%%)" % (100 * var_r[1]), fontsize=9, color=INK2)
    ax.set_title("Tasks in the space of model differences, after the general factor\ncolour = Andrea's level", loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="best")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_pcs.png"), dpi=220); plt.close(fig)

    order = leaves_list(Z)
    fig, ax = plt.subplots(figsize=(8, 7.2), facecolor=SURFACE)
    im = ax.imshow(C_res[np.ix_(order, order)], cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks([]); ax.set_yticks(range(len(order)))
    ax.set_yticklabels([cols[j][:30] for j in order], fontsize=5.5)
    for t, j in zip(ax.get_yticklabels(), order):
        t.set_color(LEVEL_COLOR[levels[j]])
    ax.set_title("Residual task correlations across models, ordered by cluster\nlabel colour = level", loc="left", fontsize=10, color=INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.ax.tick_params(labelsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig_corr.png"), dpi=220); plt.close(fig)


if __name__ == "__main__":
    main()
