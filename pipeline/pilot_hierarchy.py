#!/usr/bin/env python
"""Pilot: is there an implicational hierarchy across levels of language?

For every (model, task): Spearman rho between the model's expected rating and
the human item means, divided by the raters' own split-half reliability
(Spearman-Brown), i.e. the share of the human ceiling the model reaches. Tasks
without individual ratings have no ceiling and are left out; runs whose median
option_mass is below 0.9 are left out (the model did not answer with a digit).

Per (model, level): the median of that share over the level's tasks.

Outputs, in analysis/pilot_hierarchy/:
    pairs.csv         one row per model x task
    levels.csv        one row per model x level
    fig_hierarchy.png models x levels, share of the human ceiling; levels ordered
                      by how many models pass, models by how many levels they pass
    fig_scale.png     one panel per level, one line per family, size on the x-axis
    guttman.txt       reproducibility / scalability of the pass-fail matrix at
                      several thresholds, with a label-permutation baseline

    python pipeline/pilot_hierarchy.py
"""

import csv
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, task_meta  # noqa: E402
from human_reliability import _pearson, _rank  # noqa: E402

LEVELS = ["subword", "lexical_semantics", "syntax", "sentence_semantics",
          "pragmatics", "discourse"]          # 'other' is not a level
LABEL = task_meta.LEVEL_LABEL

# family, parameters in billions (the Hub's count); see models.md
MODELS = {
    "Qwen2.5-0.5B-Instruct": ("Qwen2.5", 0.5), "Qwen2.5-1.5B-Instruct": ("Qwen2.5", 1.5),
    "Qwen2.5-3B-Instruct": ("Qwen2.5", 3.1), "Qwen2.5-7B-Instruct": ("Qwen2.5", 7.6),
    "Qwen2.5-14B-Instruct": ("Qwen2.5", 14.8), "Qwen2.5-32B-Instruct": ("Qwen2.5", 32.8),
    "Qwen3-0.6B": ("Qwen3", 0.8), "Qwen3-1.7B": ("Qwen3", 2.0), "Qwen3-4B": ("Qwen3", 4.0),
    "Qwen3-8B": ("Qwen3", 8.2), "Qwen3-14B": ("Qwen3", 14.8), "Qwen3-32B": ("Qwen3", 32.8),
    "Llama-3.2-1B-Instruct": ("Llama 3", 1.2), "Llama-3.2-3B-Instruct": ("Llama 3", 3.2),
    "Meta-Llama-3.1-8B-Instruct": ("Llama 3", 8.0),
    "gemma-3-1b-it": ("Gemma 3", 1.0), "gemma-3-4b-it": ("Gemma 3", 4.3),
    "gemma-3-12b-it": ("Gemma 3", 12.2), "gemma-3-27b-it": ("Gemma 3", 27.4),
    "OLMo-2-0425-1B-Instruct": ("OLMo 2", 1.5), "OLMo-2-1124-7B-Instruct": ("OLMo 2", 7.3),
    "OLMo-2-1124-13B-Instruct": ("OLMo 2", 13.7), "OLMo-2-0325-32B-Instruct": ("OLMo 2", 32.2),
    "Yi-1.5-6B-Chat": ("Yi 1.5", 6.1), "Yi-1.5-9B-Chat": ("Yi 1.5", 8.8),
    "Yi-1.5-34B-Chat": ("Yi 1.5", 34.4),
    "Falcon3-1B-Instruct": ("Falcon 3", 1.7), "Falcon3-3B-Instruct": ("Falcon 3", 3.2),
    "Falcon3-7B-Instruct": ("Falcon 3", 7.5), "Falcon3-10B-Instruct": ("Falcon 3", 10.3),
    "Qwen1.5-7B-Chat": ("other", 7.7), "Qwen2-7B-Instruct": ("other", 7.6),
    "Ministral-8B-Instruct-2410": ("other", 8.0), "OLMo-3-7B-Instruct": ("other", 7.3),
    "Qwen3.5-9B": ("other", 9.7), "MiniCPM5-2B": ("other", 2.5),
    "SmolLM-1.7B-Instruct": ("other", 1.7), "SmolLM-360M-Instruct": ("other", 0.4),
    "SmolLM2-135M-Instruct": ("other", 0.1),
}
FAMILY_COLOR = {"Qwen2.5": "#2a78d6", "Qwen3": "#eb6834", "Llama 3": "#1baf7a",
                "Gemma 3": "#eda100", "OLMo 2": "#e87ba4", "Yi 1.5": "#008300",
                "Falcon 3": "#4a3aa7"}
INK, INK2, MUTED, SURFACE = "#0b0b0b", "#52514e", "#898781", "#fcfcfb"


def pairs(root):
    out = []
    meta = {t: data.task_metadata(t) for t, *_ in data.list_tasks()}
    for model in sorted(MODELS):
        files = sorted(glob.glob(os.path.join(root, "result", model, "*__autofmt.jsonl")))
        for f in files:
            task = os.path.basename(f)[:-len("__autofmt.jsonl")]
            m = meta.get(task) or {}
            level = m.get("level")
            ceil = (m.get("human_reliability") or {}).get("spearman_sb")
            if level not in LEVELS or not ceil or ceil <= 0:
                continue
            e, h, mass = [], [], []
            for line in open(f):
                r = json.loads(line)
                if r.get("human_mean") is None:
                    continue
                e.append(r["expected"]); h.append(r["human_mean"]); mass.append(r["option_mass"])
            if len(e) < 8:
                continue
            e, h = np.array(e, float), np.array(h, float)
            rho = _pearson(_rank(e), _rank(h))
            out.append({"model": model, "family": MODELS[model][0], "params_b": MODELS[model][1],
                        "task": task, "level": level, "n_items": len(e),
                        "rho": round(rho, 4), "ceiling": ceil,
                        "share": round(rho / ceil, 4) if np.isfinite(rho) else None,
                        "mass_median": round(float(np.median(mass)), 4)})
        print("read %-32s %d tasks" % (model, sum(1 for p in out if p["model"] == model)), flush=True)
    return out


def by_level(P):
    rows = []
    for model in sorted({p["model"] for p in P}):
        mine = [p for p in P if p["model"] == model]
        trusted_share = np.mean([p["mass_median"] >= 0.9 for p in mine])
        for lv in LEVELS:
            ok = [p["share"] for p in mine if p["level"] == lv and p["mass_median"] >= 0.9
                  and p["share"] is not None]
            rows.append({"model": model, "family": MODELS[model][0], "params_b": MODELS[model][1],
                         "level": lv, "n_tasks": len(ok),
                         "share_median": round(float(np.median(ok)), 4) if len(ok) >= 3 else None,
                         "model_trusted_frac": round(float(trusted_share), 3)})
    return rows


def guttman(M):
    """M: models x levels, 0/1, columns already ordered easiest -> hardest.
    Goodenough-Edwards errors: deviations from the ideal pattern implied by each
    row's total."""
    n, k = M.shape
    errors = 0
    for row in M:
        ideal = np.zeros(k, int); ideal[: int(row.sum())] = 1
        errors += int((row != ideal).sum())
    cr = 1 - errors / (n * k)
    mmr = np.mean([max(c.mean(), 1 - c.mean()) for c in M.T])
    scal = (cr - mmr) / (1 - mmr) if mmr < 1 else float("nan")
    return cr, mmr, scal, errors


def main():
    root = data.repo_root()
    out = os.path.join(root, "analysis", "pilot_hierarchy")
    os.makedirs(out, exist_ok=True)
    P = pairs(root)
    with open(os.path.join(out, "pairs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(P[0]), lineterminator="\n"); w.writeheader(); w.writerows(P)
    L = by_level(P)
    with open(os.path.join(out, "levels.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(L[0]), lineterminator="\n"); w.writeheader(); w.writerows(L)

    # models that answer with a digit on most tasks
    keep = sorted({r["model"] for r in L if r["model_trusted_frac"] >= 0.5})
    dropped = sorted({r["model"] for r in L} - set(keep))
    S = {(r["model"], r["level"]): r["share_median"] for r in L}
    A = np.array([[S[(m, lv)] if S[(m, lv)] is not None else np.nan for lv in LEVELS] for m in keep])

    lines = ["Pilot: implicational hierarchy across levels of language",
             "%d models (%d dropped: did not answer with a digit on most tasks: %s)"
             % (len(keep), len(dropped), ", ".join(dropped)),
             "cell = median over the level's tasks of rho / human split-half rho", ""]
    lines.append("mean share of the human ceiling per level, all kept models:")
    order = np.argsort(-np.nanmean(A, axis=0))
    for j in order:
        lines.append("   %-20s %.2f" % (LABEL[LEVELS[j]], np.nanmean(A[:, j])))
    lines.append("")
    rng = np.random.default_rng(0)
    for tau in (0.5, 0.6, 0.7, 0.8):
        B = (np.nan_to_num(A, nan=-1) >= tau).astype(int)
        col = np.argsort(-B.mean(axis=0), kind="stable")
        cr, mmr, scal, err = guttman(B[:, col])
        # baseline: shuffle each model's level labels independently
        base = []
        for _ in range(2000):
            Bs = np.array([rng.permutation(r) for r in B])
            c = np.argsort(-Bs.mean(axis=0), kind="stable")
            base.append(guttman(Bs[:, c])[0])
        p = float(np.mean(np.array(base) >= cr))
        lines.append("threshold %.1f  order (passed by most -> fewest): %s"
                     % (tau, " > ".join(LABEL[LEVELS[j]] for j in col)))
        lines.append("   reproducibility %.3f  (errors %d/%d)  minimal marginal %.3f  scalability %.3f"
                     "  | shuffled-label baseline %.3f, p = %.4f"
                     % (cr, err, B.size, mmr, scal, float(np.mean(base)), p))
    open(os.path.join(out, "guttman.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))

    figures(A, keep, out)
    print("\nwrote", os.path.relpath(out, root))


def figures(A, keep, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    tau = 0.7
    col = np.argsort(-np.nanmean(A, axis=0))                      # easiest level first
    passed = (np.nan_to_num(A, nan=-1) >= tau).sum(axis=1)
    row = np.lexsort((np.nanmean(A, axis=1), passed))            # fewest levels passed first
    M = A[row][:, col]
    names = [keep[i] for i in row]
    cmap = LinearSegmentedColormap.from_list("seq", ["#eef3fa", "#86b6ef", "#2a78d6", "#0d366b"])

    fig, ax = plt.subplots(figsize=(7.2, 0.27 * len(names) + 1.9), facecolor=SURFACE)
    im = ax.imshow(np.clip(M, 0, 1), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, "%.2f" % v, ha="center", va="center", fontsize=7,
                    color="white" if v > 0.55 else INK)
            if v >= tau:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec=INK, lw=1.1))
    ax.set_xticks(range(len(col)))
    ax.set_xticklabels([LABEL[LEVELS[j]].replace(" ", "\n") for j in col], fontsize=8.5, color=INK)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(["%s  (%.1fB)" % (n, MODELS[n][1]) for n in names], fontsize=7.5, color=INK2)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Share of the human ceiling reached, by level of language\n"
                 "outlined = at least %.0f%% of the raters' own reliability" % (100 * tau),
                 fontsize=10, color=INK, loc="left", pad=34)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.ax.tick_params(labelsize=7, colors=INK2); cb.outline.set_visible(False)
    fig.text(0.01, 0.005, "levels ordered left to right by mean share; models top to bottom by levels passed. "
             "Pilot, %d models." % len(names), fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(os.path.join(out, "fig_hierarchy.png"), dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6), facecolor=SURFACE, sharex=True, sharey=True)
    for ax, j in zip(axes.ravel(), col):
        ax.set_facecolor(SURFACE)
        for fam, color in FAMILY_COLOR.items():
            pts = sorted((MODELS[m][1], A[i, j]) for i, m in enumerate(keep)
                         if MODELS[m][0] == fam and not np.isnan(A[i, j]))
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], "-o", color=color, lw=1.8,
                        ms=4, label=fam, mec=SURFACE, mew=0.8)
        ax.axhline(1.0, color=MUTED, lw=0.8, ls=(0, (4, 3)))
        ax.set_xscale("log"); ax.set_ylim(-0.1, 1.1)
        ax.set_title(LABEL[LEVELS[j]], fontsize=10, color=INK, loc="left")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(MUTED)
        ax.tick_params(colors=INK2, labelsize=8)
    axes[1, 1].set_xlabel("parameters (billions, log scale)", fontsize=9, color=INK2)
    axes[0, 0].set_ylabel("share of human ceiling", fontsize=9, color=INK2)
    axes[1, 0].set_ylabel("share of human ceiling", fontsize=9, color=INK2)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=7, frameon=False, fontsize=8.5)
    fig.suptitle("Scale curves by level: model-human rank correlation as a share of the raters' own reliability "
                 "(dashed = human ceiling)", fontsize=10, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(out, "fig_scale.png"), dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
