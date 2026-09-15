#!/usr/bin/env python
"""Scan every dataset for text that was decoded with the wrong codec.

UTF-8 read as Latin-1 leaves a signature that cannot occur in real text: the
C1 control range (U+0080-U+009F) appears mid-word, so "can't" arrives as
"canâ€™t". A model reading that sees different characters than the humans did.

    python pipeline/check_encoding.py                 # all three trees
    python pipeline/check_encoding.py --sources mturk
    python pipeline/check_encoding.py --fix-report out.csv
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, prompt  # noqa: E402
from show_prompts import mojibake_of  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="published,surveyor,mturk")
    ap.add_argument("--fix-report", help="write the affected rows to this CSV")
    args = ap.parse_args(argv)

    srcs = tuple(s.strip() for s in args.sources.split(","))
    rows, n_tasks, n_items = [], 0, 0
    for task, source, csv_path, instr in data.list_tasks(sources=srcs):
        n_tasks += 1
        hits = []
        for it in data.load_items(csv_path):
            n_items += 1
            fixed = mojibake_of(it["unit"])
            if fixed:
                hits.append((it["unit"], fixed))
        text = prompt.read_instructions(instr)
        instr_fixed = mojibake_of(text)
        if instr_fixed:
            hits.append(("<instruction file>", "(instruction is affected)"))
        for bad, good in hits:
            rows.append({"source": source, "task": task,
                         "csv": os.path.relpath(csv_path),
                         "reads": bad, "should_be": good})

    print("%d datasets, %d items scanned" % (n_tasks, n_items))
    if not rows:
        print("no double-encoded text found")
        return 0

    by_task = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    print("\n%d affected item(s) across %d dataset(s):" % (len(rows), len(by_task)))
    for task, rs in by_task.items():
        print("\n  %s  (%s, %d item%s)"
              % (task, rs[0]["source"], len(rs), "" if len(rs) == 1 else "s"))
        print("      %s" % rs[0]["csv"])
        for r in rs[:2]:
            print("      reads     %r" % r["reads"][:66])
            print("      should be %r" % r["should_be"][:66])

    if args.fix_report:
        with open(args.fix_report, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print("\nwrote %s (%d rows) -- send this to whoever owns the data"
              % (args.fix_report, len(rows)))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
