#!/usr/bin/env python
"""Which tasks can the pipeline actually score, and what blocks the rest?

Run this on any new drop of rating data *before* asking for a GPU. For each
task it checks the four things a run needs:

  1. the CSV loads and has items with parseable `individual_ratings`
  2. the instruction file exists and contains a `<<{...}>>` placeholder
  3. a discrete rating scale can be resolved
  4. every human response falls inside that scale — the sharpest check, since
     a mis-resolved scale shows up here rather than as a silently wrong PMF

    python pipeline/check_tasks.py                       # everything
    python pipeline/check_tasks.py --sources surveyor,mturk
    python pipeline/check_tasks.py --list-blocked        # names, not just counts
"""

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, prompt as P  # noqa: E402


def check(task, csv_path, instr_path, probe=200, require_individual=True):
    """(ok, detail) for one task."""
    try:
        items = data.load_items(csv_path, limit=probe,
                                require_individual=require_individual)
    except Exception as exc:
        return False, "CSV unreadable: %s" % type(exc).__name__
    if not items:
        return False, ("no items with individual_ratings" if require_individual
                       else "no items")
    if not os.path.exists(instr_path):
        return False, "instruction file missing"
    text = P.read_instructions(instr_path)
    if not P.placeholders(text):
        return False, "instruction has no <<{...}>> placeholder"
    try:
        lo, hi = data.resolve_scale(text, items)
    except Exception:
        return False, "no discrete scale (free-numeric task?)"
    if require_individual:
        outside = sum(data.human_counts(i["individual"], lo, hi)[1] for i in items)
        if outside:
            return False, "%d responses outside the resolved %d-%d scale" % (
                outside, lo, hi)
    try:
        P.build_prompt(text, items[0]["unit"], lo, hi)
    except Exception as exc:
        return False, "prompt build failed: %s" % exc
    return True, "%d-%d" % (lo, hi)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="published,surveyor,mturk")
    ap.add_argument("--probe", type=int, default=200,
                    help="items inspected per task (default 200)")
    ap.add_argument("--allow-no-individual", action="store_true",
                    help="accept tasks that only have means (no distribution "
                         "test possible, but the model can still be scored)")
    ap.add_argument("--list-blocked", action="store_true")
    args = ap.parse_args(argv)

    rows = data.list_tasks(sources=tuple(s.strip()
                                         for s in args.sources.split(",")))
    scales = collections.Counter()
    blocked = collections.defaultdict(list)
    by_source = collections.Counter()
    ok = 0
    for task, source, csv_path, instr_path in rows:
        good, detail = check(task, csv_path, instr_path, args.probe,
                             not args.allow_no_individual)
        if good:
            ok += 1
            scales[detail] += 1
            by_source[source] += 1
        else:
            blocked[detail].append("%s/%s" % (source, task))

    with_ind = sum(1 for t, *_ in rows
                   if data.task_metadata(t).get("has_individual_ratings"))
    print("%d tasks checked, %d scorable (%.0f%%), %d with individual ratings"
          % (len(rows), ok, 100.0 * ok / max(len(rows), 1), with_ind))
    print("  scorable by source: %s" % dict(by_source.most_common()))
    print("  scales:          %s" % dict(scales.most_common()))
    if blocked:
        print("\nblocked:")
        for reason, names in sorted(blocked.items(), key=lambda kv: -len(kv[1])):
            print("  %-52s %4d" % (reason[:52], len(names)))
            if args.list_blocked:
                for n in names:
                    print("      " + n)
            else:
                print("      e.g. %s" % ", ".join(names[:3]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
