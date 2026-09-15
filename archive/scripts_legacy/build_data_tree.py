#!/usr/bin/env python
"""Generate data/<level>/<task>/ from the three source trees and Andrea's levels.

    data/
      syntax/
        locative_topicalization_survey/
          instruction.txt      the wording, <<{...}>> where the stimulus goes
          ratings.csv          unit,mean,std,n,individual_ratings
          metadata.json        where it came from, how big it is, what it probes
      lexical_semantics/
      ...
      INDEX.csv                one row per dataset, for grep and spreadsheets

Why a generated view rather than a move. The level a dataset sits under is a
judgement -- Andrea's own note says the scheme may change if reviewers push
back -- while the source trees (norm_datasets/, surveyor_norms/, mturk_norms/)
are facts and are what the collaborators maintain and audit. Baking a
judgement into a directory name would mean that reclassifying one dataset
moves its folder and breaks every path that pointed at it. So the source trees
stay exactly as they are, audit/dataset_levels.csv is the single place a level
is decided, and this script rebuilds data/ from both. Change a level there and
rerun; never move a folder by hand.

    python scripts/build_data_tree.py            # rebuild data/ from scratch
    python scripts/build_data_tree.py --check    # report only, write nothing
"""

import argparse
import csv
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, prompt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(REPO, "audit", "dataset_levels.csv")
MERGES = [os.path.join(REPO, "audit", "evidence", "merges_exact.json"),
          os.path.join(REPO, "audit", "evidence", "merges_near.json")]
OUT = os.path.join(REPO, "data")

# fixed file names inside every dataset folder, so tooling never guesses
F_INSTR, F_RATINGS, F_META = "instruction.txt", "ratings.csv", "metadata.json"


def merged_from():
    """task -> the batches Andrea pooled into it (2026-08-22 merge)."""
    out = {}
    for path in MERGES:
        if not os.path.exists(path):
            continue
        for m in json.load(open(path, encoding="utf-8")):
            out.setdefault(m["keep"], []).extend(m.get("absorbed", []))
    return out


def provenance():
    """Per-task provenance from the collections' own indexes."""
    out = {}
    p = os.path.join(REPO, "mturk_norms", "a_index.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            out[r["file"]] = {
                "question_wording": (r.get("question_provenance") or "").strip(),
                "scale_labels": (r.get("scale_source") or "").strip(),
                "quality_flag": (r.get("quality_flag") or "").strip(),
            }
    p = os.path.join(REPO, "surveyor_norms", "a_index.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            out[r["file"]] = {
                "survey_id": r.get("survey_id", ""),
                "owner": r.get("user", ""),
                "participants": int(r["participants"]) if r.get("participants") else None,
                "n_test": int(r["n_test"]) if r.get("n_test") else None,
                "n_filler": int(r["n_filler"]) if r.get("n_filler") else None,
                "n_practice": int(r["n_practice"]) if r.get("n_practice") else None,
                "anchors_dropped": int(r["anchors_dropped"]) if r.get("anchors_dropped") else None,
            }
    return out


def describe(task, csv_path, instr_path):
    """The numbers a reader wants before opening the files."""
    items = data.load_items(csv_path)
    trial = [it for it in items if it["individual"]]
    ns = [len(it["individual"]) for it in trial]
    text = prompt.read_instructions(instr_path) if os.path.exists(instr_path) else ""
    try:
        lo, hi = data.resolve_scale(text, items, task=task)
        scale = [lo, hi]
    except ValueError:
        scale = None
    fields = sorted(set(prompt.placeholders(text)))
    total_ratings = sum(ns) if trial else sum(
        int(it["n"]) for it in items if it.get("n"))
    ns_sorted = sorted(ns)
    return {
        "n_items": len(items),
        "n_ratings": total_ratings,
        "ratings_per_item_median": ns_sorted[len(ns) // 2] if ns else None,
        "ratings_per_item_min": ns_sorted[0] if ns else None,
        "ratings_per_item_max": ns_sorted[-1] if ns else None,
        "has_individual_ratings": bool(trial),
        "scale": scale,
        "placeholder": fields[0] if len(fields) == 1 else fields,
        "unit_non_ascii": sum(1 for it in items
                              if any(ord(c) > 127 for c in it["unit"])),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="write nothing")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    rows = list(csv.DictReader(open(LEVELS, encoding="utf-8")))
    merges, prov = merged_from(), provenance()

    if not args.check:
        # a generated view: rebuild from nothing so a removed dataset disappears
        if os.path.isdir(args.out):
            shutil.rmtree(args.out)
        os.makedirs(args.out)

    index, missing, by_level = [], [], {}
    for r in rows:
        task, level = r["id"], r["level"]
        src_csv = os.path.join(REPO, r["csv_path"])
        src_ins = os.path.join(REPO, r["instruction_path"])
        if not os.path.exists(src_csv) or not os.path.exists(src_ins):
            missing.append((task, r["csv_path"] if not os.path.exists(src_csv)
                            else r["instruction_path"]))
            continue

        meta = {
            "task": task,
            "source": r["collection"],
            "level": level,
            "sublevel": r.get("sublevel") or None,
            "level_decided_by": r.get("decided_by", ""),
            "level_rationale": r.get("rationale", ""),
            "level_blind_check_agrees": (r.get("blind_agrees") == "yes"),
            "language": prov.get(task, {}).get("language") or
                        ("non-english" if "non_english" in r["csv_path"] else "english"),
        }
        meta.update(describe(task, src_csv, src_ins))
        meta["merged_from"] = merges.get(task, [])
        meta["provenance"] = prov.get(task, {})
        meta["original"] = {"ratings": r["csv_path"], "instruction": r["instruction_path"]}
        if r.get("note"):
            meta["note"] = r["note"]

        by_level[level] = by_level.get(level, 0) + 1
        index.append({
            "task": task, "level": level, "sublevel": meta["sublevel"] or "",
            "source": meta["source"], "language": meta["language"],
            "scale": "%d-%d" % tuple(meta["scale"]) if meta["scale"] else "",
            "n_items": meta["n_items"], "n_ratings": meta["n_ratings"],
            "ratings_per_item": meta["ratings_per_item_median"] or "",
            "individual_ratings": "yes" if meta["has_individual_ratings"] else "no",
            "merged_from": ";".join(meta["merged_from"]),
            "path": "data/%s/%s" % (level, task),
        })

        if args.check:
            continue
        d = os.path.join(args.out, level, task)
        os.makedirs(d)
        shutil.copyfile(src_csv, os.path.join(d, F_RATINGS))
        shutil.copyfile(src_ins, os.path.join(d, F_INSTR))
        with open(os.path.join(d, F_META), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    if not args.check:
        with open(os.path.join(args.out, "INDEX.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(index[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(index)
        with open(os.path.join(args.out, "README.md"), "w", encoding="utf-8") as fh:
            fh.write(README % {"n": len(index)})

    print("%s%d datasets under data/, by level:" % (
        "would write " if args.check else "wrote ", len(index)))
    for lv, n in sorted(by_level.items(), key=lambda kv: -kv[1]):
        print("   %-20s %3d" % (lv, n))
    if missing:
        print("\n%d rows in dataset_levels.csv point at files that do not exist:"
              % len(missing))
        for t, p in missing:
            print("   %-46s %s" % (t, p))
        return 1
    return 0


README = """# data/

One folder per dataset, grouped by the level of language it probes. %(n)d
datasets. This tree is **generated** -- do not edit it by hand.

    data/<level>/<task>/
        instruction.txt     the wording the model is given, <<{...}>> where the stimulus goes
        ratings.csv         unit,mean,std,n,individual_ratings
        metadata.json       source, size, scale, level, provenance, what it was merged from
    data/INDEX.csv          one row per dataset

## Where it comes from

The files are copied from the three source trees the collaborators maintain --
`norm_datasets/` (published norms), `surveyor_norms/`, `mturk_norms/` -- and the
level each dataset sits under is read from `audit/dataset_levels.csv`. Nothing
here is decided here.

To change a dataset's level, edit `audit/dataset_levels.csv` and run

    python scripts/build_data_tree.py

Never move a folder by hand: the next rebuild would put it back.

## Levels

subword, lexical_semantics (affective / perceptual_motor / conceptual), syntax,
sentence_semantics (plausibility / affective / conceptual_content), pragmatics,
discourse, and `other` for rating variables that are linguistic but not a level
(age of acquisition, familiarity, frequency, cloze). Sublevels are in
`metadata.json`, not in the path.
"""


if __name__ == "__main__":
    raise SystemExit(main())
