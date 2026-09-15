#!/usr/bin/env python
"""Gather every run in result/ into one JSON for the report page.

Keeps the page a pure view: all numbers come from here, and re-running this
after new runs land refreshes the page without touching its HTML.

    python pipeline/build_report_data.py            # -> result/report_data.json
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from analyze_run import analyze  # noqa: E402
from llm_ratings import data
from llm_ratings import task_meta
from llm_ratings import facts as facts_mod  # noqa: E402

# model -> (family, params in B). Anything unlisted is inferred loosely.
FAMILY = [
    ("Qwen3.5", "Qwen3.5"), ("Qwen2.5", "Qwen2.5"), ("Llama-3.2", "Llama 3.2"),
    ("Meta-Llama-3.1", "Llama 3.1"), ("Llama-3.1", "Llama 3.1"),
    ("gemma-3", "Gemma 3"), ("OLMo-3", "OLMo 3"), ("OLMo-2", "OLMo 2"),
    ("Ministral", "Mistral"), ("Mistral", "Mistral"),
]


def meta_of(name):
    fam = next((f for k, f in FAMILY if k in name), name.split("-")[0])
    size = None
    for tok in name.replace("_", "-").split("-"):
        t = tok.upper()
        if t.endswith("B") and t[:-1].replace(".", "").isdigit():
            size = float(t[:-1])
            break
    return fam, size


def task_domain(task):
    return task_meta.meta_of(task)["level_label"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="result")
    ap.add_argument("--out", default="result/report_data.json")
    args = ap.parse_args(argv)

    runs = []
    # task-major: analyze() reloads the task's CSV, and walking model-major
    # meant every run missed the cache and re-parsed a file it had just read
    paths = sorted(glob.glob(os.path.join(args.root, "*", "*.jsonl")),
                   key=lambda p: (os.path.basename(p), p))
    for path in paths:
        if path.endswith(".meta.json"):
            continue
        stem = os.path.basename(path).split(".jsonl")[0]
        model_dir = os.path.basename(os.path.dirname(path))
        try:
            r = analyze(path, quiet=True)
        except Exception as exc:
            print("skip %s: %s: %s" % (path, type(exc).__name__, exc),
                  file=sys.stderr)
            continue
        mpath = path + ".meta.json"
        meta = json.load(open(mpath)) if os.path.exists(mpath) else {}
        spath = path + ".dist.csv.summary.json"
        summ = json.load(open(spath)) if os.path.exists(spath) else {}

        fam, size = meta_of(model_dir)
        variant = ""
        for tag in ("__autofmt", "__fp32", "__digits", "__yesno", "__suffix"):
            if tag in stem:
                variant = tag[2:]
        a = summ.get("alignment") or {}
        wd = summ.get("median_W1_over_delta")
        if wd is None and summ.get("median_W1") and summ.get("median_delta"):
            wd = summ["median_W1"] / summ["median_delta"]
        runs.append({
            "run": stem, "model": model_dir, "model_id": meta.get("model"),
            "family": fam, "params_b": size,
            "task": r["task"], "domain": task_domain(r["task"]),
            "variant": variant, "dtype": meta.get("dtype", "bfloat16"),
            "prompt_style": meta.get("placeholder_style"),
            "prompt_suffix": meta.get("suffix"),
            "auto_format": bool(meta.get("auto_format")),
            "scale": r["scale"], "n_items": r["n_items"],
            "mass_median": r["mass_median"], "mass_min": r["mass_min"],
            "mass_frac_below_09": r["mass_frac_below_0.9"],
            "pearson": r["pearson"], "spearman": r["spearman"],
            "model_sd": r["model_sd"], "human_sd": r["human_sd"],
            "ols_slope": r["ols_slope_human_on_model"],
            "model_entropy": r["model_entropy_median"],
            "human_entropy": r.get("human_entropy_median"),
            "model_maxprob": r["model_maxprob_median"],
            "human_maxprob": r.get("human_maxprob_median"),
            "model_marginal": r["model_marginal"],
            "human_marginal": r.get("human_marginal"),
            "model_argmax": r["model_argmax_counts"],
            "human_argmax": r.get("human_argmax_counts"),
            "unused_modes": r["unused_modes"],
            "W1_mean": r.get("W1_mean"),
            "W1_location_mean": r.get("W1_location_mean"),
            "W1_shape_mean": r.get("W1_shape_mean"),
            "shape_share": r.get("shape_share_of_W1"),
            # only present where run_dist_eval has been run
            "median_W1": summ.get("median_W1"),
            "median_delta": summ.get("median_delta"),
            "W1_over_delta": wd,
            "frac_similar": summ.get("frac_similar"),
            "align_normalized": a.get("normalized"),
            "align_model": a.get("model"), "align_null": a.get("null"),
            "align_ceiling": a.get("ceiling"),
            "median_n_raters": summ.get("median_n_raters"),
        })

    tasks = {}
    for r in runs:
        t = r["task"]
        if t in tasks:
            continue
        if t in task_meta.BROKEN:     # see task_meta.BROKEN for the reason
            continue
        loc = data.find_task(t)
        F = facts_mod.facts(loc["csv"])
        tasks[t] = {
            "task": t, "domain": r["domain"], "source": loc["source"],
            "level": task_meta.meta_of(t)["level"],
            "label": task_meta.meta_of(t)["label"],
            "gloss": task_meta.meta_of(t)["gloss"],
            "n_items_total": F["n_trial_items"] or F["n_items"],
            "median_n_raters": F["median_raters"],
            "scale": r["scale"],
            "human_entropy": r.get("human_entropy"),
            "instructions": open(loc["instructions"], encoding="utf-8").read().strip(),
        }

    facts_mod.save()
    out = {"runs": runs, "tasks": list(tasks.values()), "n_runs": len(runs)}
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print("wrote %s: %d runs, %d tasks" % (args.out, len(runs), len(tasks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
