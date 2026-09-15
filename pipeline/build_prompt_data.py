#!/usr/bin/env python
"""Every dataset's prompt, for browsing without having scored anything.

The item inspector needs a model run before it can show a task. Checking that a
prompt reads correctly should not need one: a dataset the collaborators have
just cleaned ought to be readable the moment it lands. This writes one entry per
dataset -- instruction text, where the stimulus goes, a handful of real stimuli,
and the facts that decide whether it is worth scoring.

    python pipeline/build_prompt_data.py           # -> result/data/prompts.json
"""

import argparse
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import data, prompt, task_meta
from llm_ratings import facts as facts_mod  # noqa: E402
from show_prompts import mojibake_of, wired_tasks, EXCLUDED  # noqa: E402

# names that suggest a teaching or pilot survey rather than collected data
DEMO_HINTS = ("demo", "class_", "_test", "test_", "sandbox", "practice", "example")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="published,surveyor,mturk")
    ap.add_argument("--out", default="result/data/prompts.json")
    ap.add_argument("--samples", type=int, default=4,
                    help="stimuli kept per dataset (default 4)")
    args = ap.parse_args(argv)

    srcs = tuple(s.strip() for s in args.sources.split(","))
    wired = {t for t, _c, _i in wired_tasks(srcs)}   # also fills EXCLUDED
    out = []
    for task, source, csv_path, instr in data.list_tasks(sources=srcs):
        if not os.path.exists(instr):
            out.append({"task": task, "source": source, "error":
                        "no instruction file at %s" % os.path.relpath(instr)})
            continue
        text = prompt.read_instructions(instr)
        fields = sorted(set(prompt.placeholders(text)))

        F = facts_mod.facts(csv_path, samples=args.samples)
        n_trial = F["n_trial_items"]
        lo = hi = None
        if F["all_integer"] and F["n_distinct_values"] <= 12 and F["distinct_values"]:
            lo, hi = int(F["distinct_values"][0]), int(F["distinct_values"][-1])
        ns_few, ns_total = F["few_rater_items"], F["n_trial_items"]
        picks = F["units"]

        problems = []
        if not n_trial and F["n_items"]:
            notes_only = "item means only -- the model's distribution is shown alone"
        else:
            notes_only = ""
        if len(fields) > 1:
            problems.append("instruction needs %d different fields (%s); a run "
                            "supplies one stimulus, so it cannot be filled"
                            % (len(fields), ", ".join(fields)))
        if not fields:
            problems.append("instruction has no <<{...}>> placeholder")
        if lo is None and n_trial:
            problems.append("responses are not a small integer scale")
        if ns_total and ns_few > 0.2 * ns_total:
            problems.append("%d%% of items have fewer than 5 raters"
                            % round(100 * ns_few / ns_total))
        if any(k in task.lower() for k in DEMO_HINTS):
            problems.append("name suggests a demo or pilot survey, not "
                            "collected data -- worth confirming before use")
        if task in EXCLUDED:
            problems.append(EXCLUDED[task])

        tm = task_meta.meta_of(task)
        out.append({
            "task": task, "source": source,
            "variant": "non_english" if tm["language"] == "non-english" else "",
            "csv": os.path.relpath(csv_path),
            "instr": os.path.relpath(instr),
            "label": tm["label"], "level": tm["level"],
            "level_label": tm["level_label"],
            "sublevel": tm["sublevel"], "sublevel_label": tm["sublevel_label"],
            "level_decided_by": tm["level_decided_by"],
            "level_rationale": tm["level_rationale"],
            "level_confirmed": tm["level_confirmed"],
            "merged_from": tm["merged_from"],
            "ratings_per_item": tm["ratings_per_item"],
            "n_ratings": tm["n_ratings"],
            "language": tm["language"] or "english",
            "gloss": tm["gloss"],
            "note": tm["note"],
            "fields": fields,
            "instruction": text,
            "samples": picks,
            "scale": [lo, hi] if lo is not None else None,
            "n_items": F["n_items"], "n_trial_items": n_trial,
            "median_raters": F["median_raters"],
            "min_raters": F["min_raters"],
            "instr_non_ascii": sorted({c for c in text if ord(c) > 127}),
            "scorable": task in wired,
            "problems": problems,
            "note_means_only": notes_only,
        })

    facts_mod.save()
    out.sort(key=lambda r: (r["source"], r.get("variant", ""), r["task"]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump({"datasets": out}, fh, separators=(",", ":"))
    ok = sum(1 for r in out if r.get("scorable"))
    print("wrote %s: %d datasets, %d scorable, %.0f KB"
          % (args.out, len(out), ok, os.path.getsize(args.out) / 1024))
    by = {}
    for r in out:
        by.setdefault(r["source"], [0, 0])
        by[r["source"]][0] += 1
        by[r["source"]][1] += bool(r.get("scorable"))
    for s, (n, k) in sorted(by.items()):
        print("   %-10s %3d datasets, %3d scorable" % (s, n, k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
