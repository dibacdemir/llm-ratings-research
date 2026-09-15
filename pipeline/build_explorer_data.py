#!/usr/bin/env python
"""Per-item data for the item inspector page: prompt, model answer, human answer.

For each model x task it stores the exact prompt split around the stimulus
(prefix + item + suffix reconstructs, character for character, what the model
was fed), summary statistics over *all* items, and a sample of individual items
with both distributions.

    python pipeline/build_explorer_data.py       # -> result/explorer_data.json
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import data
from llm_ratings import task_meta  # noqa: E402
from llm_ratings import prompt as prompt_mod  # noqa: E402



def entropy(p):
    return float(-(p * np.log2(np.clip(p, 1e-12, 1))).sum())


def mark_prompt(example, unit, style):
    """(prompt, spans): the prompt as fed, and where the stimulus sits in it.

    Two things make this harder than a single split. The stimulus is written
    into the prompt wrapped by whatever placeholder style was probed for this
    model and task, so a bare search for the unit also matches it as a
    substring of ordinary words -- the "A" of "Answer" was being mistaken for
    the one-letter stimulus "A", which lost the prompt for every lancaster2020
    run. And an instruction file may contain several ``<<{...}>>`` slots, so
    the stimulus can legitimately appear more than once: devarda2023 writes the
    target word into four places. Spans, rather than a prefix/suffix pair,
    represent both cases.
    """
    if not example or not unit:
        return None, None
    marker = {"angle": "<<%s>>", "quote": '"%s"'}.get(style, "%s") % unit
    spans, i = [], example.find(marker)
    while i >= 0:
        spans.append([i, i + len(marker)])
        i = example.find(marker, i + len(marker))
    if not spans:                      # style recorded does not match the text
        return None, None
    return example, spans


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="result")
    ap.add_argument("--out", default="result/explorer_data.json")
    ap.add_argument("--tasks", default="all",
                    help="comma-separated task names, or 'all' for every task "
                         "that has been scored (the default, so newly run "
                         "tasks appear without editing anything)")
    ap.add_argument("--sample", type=int, default=120,
                    help="items kept per pair, spread evenly through the set")
    ap.add_argument("--split-dir", default="result/data",
                    help="also write an index plus one file per pair, so the "
                         "page can load item data on demand instead of "
                         "carrying every pair at once")
    ap.add_argument("--max-inline-pairs", type=int, default=0,
                    help="pairs whose items are embedded uncompressed in "
                         "explorer_data.json. Normally 0: "
                         "pack_inspector_data.py rewrites that file and adds "
                         "a compressed blob holding every pair's items")
    args = ap.parse_args(argv)

    want = None if args.tasks.strip() == "all" else \
        [t.strip() for t in args.tasks.split(",")]
    best = {}
    for path in sorted(glob.glob(os.path.join(args.root, "*", "*.jsonl"))):
        if path.endswith(".meta.json"):
            continue
        stem = os.path.basename(path).split(".jsonl")[0]
        task = stem.split("__")[0]
        if want is not None and task not in want:
            continue
        if task in task_meta.BROKEN:      # see task_meta.BROKEN for the reason
            continue
        model = os.path.basename(os.path.dirname(path))
        key = (model, task)
        # an --auto-format rerun supersedes the original
        if key in best and "__autofmt" not in stem:
            continue
        best[key] = path

    pairs, task_info = [], {}
    # task-major, so the same CSV is read once instead of once per model
    for (model, task), path in sorted(best.items(), key=lambda kv: kv[0][::-1]):
        rows = [json.loads(l) for l in open(path) if l.strip()]
        if not rows:
            continue
        meta = json.load(open(path + ".meta.json"))
        lo, hi = meta["scale"]
        vals = np.arange(lo, hi + 1)
        items = data.load_items(meta["csv"])
        by = {it["unit"]: it for it in items}

        # Most norming studies release item means only. Those still support the
        # comparison this project is about -- does the model rate items the way
        # people did -- so they are kept, with the human side reduced to its
        # mean. Everything that needs a human *distribution* (the per-item
        # spread, the distance between distributions, the raters' entropy) is
        # left out for them rather than faked from the mean.
        rec, trial = [], False
        for r in rows:
            it = by.get(r["unit"])
            if not it:
                continue
            p = np.asarray(r["probs"], float)
            row = {"u": r["unit"], "p": [round(float(x), 4) for x in p],
                   "e": round(float(np.dot(p, vals)), 3),
                   "m": round(float(r.get("option_mass", 1)), 3)}
            if it["individual"]:
                counts, _ = data.human_counts(it["individual"], lo, hi)
                n = sum(counts)
                if n >= 2:
                    trial = True
                    h = np.asarray(counts, float) / n
                    cp, ch = np.cumsum(p)[:-1], np.cumsum(h)[:-1]
                    row.update({"h": counts, "n": n,
                                "hm": round(float(np.dot(h, vals)), 3),
                                "w1": round(float(np.abs(cp - ch).sum()), 3)})
            if "hm" not in row:
                if it.get("mean") is None:
                    continue
                row["hm"] = round(float(it["mean"]), 3)
                row["n"] = it.get("n") or 0
            rec.append(row)
        if not rec:
            continue

        # statistics over every item, not just the sample kept for browsing
        E = np.array([x["e"] for x in rec])
        H = np.array([x["hm"] for x in rec])
        P = np.array([x["p"] for x in rec])
        HP = np.array([np.asarray(x["h"], float) / sum(x["h"])
                       for x in rec if "h" in x]) if trial else None
        rx, ry = E - E.mean(), H - H.mean()
        pear = float((rx * ry).sum() / np.sqrt((rx ** 2).sum() * (ry ** 2).sum())) \
            if rx.any() and ry.any() else float("nan")
        # Average ranks for ties, which is the standard definition and what
        # scipy.stats.spearmanr returns. Human item means do tie -- two items
        # can draw the same count vector from the raters -- and consecutive
        # ranks for tied values shift the coefficient slightly.
        def ranks(a):
            order = np.argsort(a, kind="mergesort")
            r = np.empty(len(a), float)
            r[order] = np.arange(len(a), dtype=float)
            _, first, counts = np.unique(a[order], return_index=True,
                                         return_counts=True)
            for f, c in zip(first, counts):
                if c > 1:
                    r[order[f:f + c]] = r[order[f:f + c]].mean()
            return r
        rE, rH = ranks(E), ranks(H)
        sx, sy = rE - rE.mean(), rH - rH.mean()
        denom = np.sqrt((sx ** 2).sum() * (sy ** 2).sum())
        spear = float((sx * sy).sum() / denom) if denom else float("nan")

        TM = task_meta.meta_of(task)
        if task not in task_info:
            try:
                loc = data.find_task(task)
                task_info[task] = {"instruction":
                                   prompt_mod.read_instructions(loc["instructions"])}
            except Exception:
                task_info[task] = {"instruction": ""}
        ptxt, pspans = mark_prompt(meta.get("example_prompt"),
                                   rows[0]["unit"],
                                   meta.get("placeholder_style"))
        step = max(1, len(rec) // args.sample)
        shown = rec[::step][:args.sample]

        pairs.append({
            "model": model, "model_id": meta.get("model"), "task": task,
            "task_label": TM["label"], "domain": TM["level_label"],
            "level": TM["level"], "level_confirmed": TM["level_confirmed"],
            "source": TM["source"], "gloss": TM["gloss"], "note": TM["note"],
            "sublevel": TM["sublevel"], "sublevel_label": TM["sublevel_label"],
            "level_decided_by": TM["level_decided_by"],
            "level_rationale": TM["level_rationale"],
            "dataset_n_items": TM["n_items"], "dataset_n_ratings": TM["n_ratings"],
            "ratings_per_item": TM["ratings_per_item"],
            "merged_from": TM["merged_from"], "language": TM["language"],
            # the ceiling a model-human correlation can reach on this task
            "human_r_sb": TM["human_reliability"].get("pearson_sb"),
            "human_rho_sb": TM["human_reliability"].get("spearman_sb"),
            "scale": [lo, hi], "n_items": len(rec), "n_shown": len(shown),
            "human_trial_level": trial,
            "prompt_text": ptxt, "prompt_spans": pspans,
            "prompt_unit": rows[0]["unit"],
            "fmt_style": meta.get("placeholder_style"),
            "fmt_suffix": meta.get("suffix"), "dtype": meta.get("dtype"),
            "run_date": (meta.get("started") or "")[:10],
            "stats": {
                "model_mean": round(float(E.mean()), 3),
                "human_mean": round(float(H.mean()), 3),
                "model_sd": round(float(E.std()), 3),
                "human_sd": round(float(H.std()), 3),
                "pearson": round(pear, 3), "spearman": round(spear, 3),
                "w1_mean": round(float(np.mean([x["w1"] for x in rec
                                                if "w1" in x])), 3) if trial else None,
                "model_entropy": round(entropy(P.mean(0)), 3),
                "human_entropy": round(entropy(HP.mean(0)), 3) if trial else None,
                "mass_median": round(float(np.median([x["m"] for x in rec])), 3),
                # Share of probability sitting on the two ends of the scale.
                # A model can have a healthy spread and still be treating a
                # 5- or 7-point scale as a yes/no choice; that shows up here
                # and not in the standard deviation. The human value is stored
                # alongside because for some tasks -- is this word about taste?
                # -- the raters legitimately pile onto the ends too.
                "median_n": int(np.median([x["n"] for x in rec if x.get("n")])
                                ) if any(x.get("n") for x in rec) else 0,
                "model_low": round(float(P[:, 0].mean()), 3),
                "model_high": round(float(P[:, -1].mean()), 3),
                "model_ends": round(float(P[:, 0].mean() + P[:, -1].mean()), 3),
                "human_ends": round(float(HP[:, 0].mean() + HP[:, -1].mean()), 3)
                              if trial else None,
            },
            "items": shown,
        })

    ORDER = task_meta.LEVEL_ORDER + ["form", "semantic", "lexical"]
    tasks = sorted({p["task"] for p in pairs},
                   key=lambda t: (ORDER.index(task_meta.level_of(t)[0])
                                  if task_meta.level_of(t)[0] in ORDER else 99, t))
    models = sorted({p["model"] for p in pairs})

    # --- split form: a small index the page always loads, plus one file per
    # pair fetched only when that pair is selected. This is what keeps the page
    # fast as the number of models and tasks grows.
    if args.split_dir:
        os.makedirs(args.split_dir, exist_ok=True)
        # only the per-pair files and the index belong to this builder; the
        # directory also holds prompts.json, which is written elsewhere
        keep = {"prompts.json", "explorer.pack.json"}
        for old in glob.glob(os.path.join(args.split_dir, "*.json")):
            if os.path.basename(old) not in keep:
                os.remove(old)
        heavy = ("items", "prompt_text", "prompt_spans", "prompt_unit")
        index = []
        for p in pairs:
            slug = "%s__%s" % (p["model"], p["task"])
            with open(os.path.join(args.split_dir, slug + ".json"), "w") as fh:
                json.dump({k: p[k] for k in heavy}, fh, separators=(",", ":"))
            index.append({k: v for k, v in p.items() if k not in heavy})
        with open(os.path.join(args.split_dir, "index.json"), "w") as fh:
            json.dump({"pairs": index, "tasks": tasks, "models": models,
                       "task_info": task_info}, fh, separators=(",", ":"))
        idx_kb = os.path.getsize(os.path.join(args.split_dir, "index.json")) / 1024
        print("wrote %s/: index %.0f KB + %d pair files"
              % (args.split_dir, idx_kb, len(pairs)))

    # --- standalone form: one self-contained file. Every pair keeps its
    # statistics, so the comparison table and the heatmap are complete no matter
    # how many models were run; the per-item data, which is what actually makes
    # the file big, is kept only for the first --max-inline-pairs. Beyond that
    # the page says so rather than showing an empty item list.
    inline, with_items = [], 0
    for p in pairs:
        if with_items < args.max_inline_pairs:
            inline.append(p)
            with_items += 1
        else:
            inline.append({k: v for k, v in p.items() if k not in
                           ("items", "prompt_text", "prompt_spans",
                            "prompt_unit")})
    out = {"pairs": inline, "tasks": tasks, "models": models,
           "task_info": task_info,
           "n_pairs_total": len(pairs), "n_pairs_with_items": with_items}
    with open(args.out, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("wrote %s: %d pairs, %d with items, %.0f KB"
          % (args.out, len(inline), with_items,
             os.path.getsize(args.out) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
