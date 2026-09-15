"""Locate and load rating tasks from data/.

A *task* is one folder:

    data/<level>/<task>/
        instruction.txt    the wording, "<<{word}>>" (or sentence/expression/item) where the stimulus goes
        ratings.csv        unit, mean, std, n, individual_ratings
        metadata.json      source, size, scale, level, provenance, human reliability

The level in the path is a judgement (audit/dataset_levels.csv); everything
else about the task is read from the files, never from the path.
"""

import csv
import functools
import json
import os
import re
import sys

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Options beyond this and we assume it is not a discrete rating scale
# (e.g. kuperman age-of-acquisition, which is free numeric years).
MAX_SCALE_POINTS = 12


def repo_root(start=None):
    """Walk up from this file until we see data/ and audit/."""
    d = os.path.dirname(os.path.abspath(start or __file__))
    while d != "/":
        if os.path.isdir(os.path.join(d, DATA_DIR)) and os.path.isdir(
            os.path.join(d, "audit")
        ):
            return d
        d = os.path.dirname(d)
    raise RuntimeError("could not locate repo root (no data/ + audit/)")


DATA_DIR = "data"          # data/<level>/<task>/
_META_CACHE = {}


def _pairs_data_tree(root, sources):
    """Walk data/<level>/<task>/. The source (published/surveyor/mturk) is read
    from metadata.json, not from the path, because the path encodes the level."""
    base = os.path.join(root, DATA_DIR)
    if not os.path.isdir(base):
        return
    for level in sorted(os.listdir(base)):
        ldir = os.path.join(base, level)
        if not os.path.isdir(ldir):
            continue
        for task in sorted(os.listdir(ldir)):
            d = os.path.join(ldir, task)
            csvp, insp, metap = (os.path.join(d, "ratings.csv"),
                                 os.path.join(d, "instruction.txt"),
                                 os.path.join(d, "metadata.json"))
            if not (os.path.isfile(csvp) and os.path.isfile(insp)):
                continue
            src = ""
            if os.path.isfile(metap):
                try:
                    with open(metap, encoding="utf-8") as fh:
                        m = json.load(fh)
                    _META_CACHE[task] = m
                    src = m.get("source", "")
                except Exception:
                    pass
            if src in sources:
                yield task, src, csvp, insp


def task_metadata(task, root=None):
    """The metadata.json of a task in data/, or {} when there is none."""
    if task in _META_CACHE:
        return _META_CACHE[task]
    root = root or repo_root()
    base = os.path.join(root, DATA_DIR)
    if os.path.isdir(base):
        for level in os.listdir(base):
            metap = os.path.join(base, level, task, "metadata.json")
            if os.path.isfile(metap):
                try:
                    with open(metap, encoding="utf-8") as fh:
                        _META_CACHE[task] = json.load(fh)
                    return _META_CACHE[task]
                except Exception:
                    break
    _META_CACHE[task] = {}
    return {}


def list_tasks(root=None, sources=("published", "surveyor", "mturk")):
    """[(task, source, csv_path, instruction_path)] for every task in data/."""
    root = root or repo_root()
    return list(_pairs_data_tree(root, sources))


def find_task(task, root=None):
    """Resolve a task name (or a direct path to its CSV) to its file pair."""
    root = root or repo_root()
    if task.endswith(".csv") and os.path.exists(task):
        task = os.path.basename(task)[:-4]
    hits = [t for t in list_tasks(root) if t[0] == task]
    if not hits:
        raise KeyError("unknown task %r (see --list)" % task)
    if len(hits) > 1:
        raise KeyError(
            "ambiguous task %r, present in: %s" % (task, [h[1] for h in hits])
        )
    name, source, csv_path, instr_path = hits[0]
    if not os.path.exists(instr_path):
        raise FileNotFoundError("no instruction file for %r at %s" % (name, instr_path))
    return {"task": name, "source": source, "csv": csv_path, "instructions": instr_path}


def _parse_individual(raw):
    if not raw or not raw.strip():
        return None
    try:
        vals = json.loads(raw)
    except Exception:
        try:
            import ast

            vals = ast.literal_eval(raw)
        except Exception:
            return None
    if not isinstance(vals, (list, tuple)):
        return None
    return [float(v) for v in vals if v is not None and v != ""]


@functools.lru_cache(maxsize=4)
def _load_items_cached(csv_path, limit, require_individual):
    return tuple(_load_items(csv_path, limit, require_individual))


def load_items(csv_path, limit=None, require_individual=False):
    """Rows of the norm CSV. Repeated calls for the same file are served from
    a small cache: the builders walk every model against the same task, and
    re-parsing a 66k-row CSV once per model made a page rebuild take minutes."""
    return list(_load_items_cached(csv_path, limit, require_individual))


def _load_items(csv_path, limit=None, require_individual=False):
    """Rows of the norm CSV as dicts: unit, mean, std, n, individual (list|None)."""
    items = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            unit = (row.get("unit") or "").strip()
            if not unit:
                continue
            try:
                mean = float(row["mean"]) if row.get("mean") else None
            except ValueError:
                # 4 rows in each tuckute2024 file have broken CSV quoting
                # (a comma inside an unquoted sentence shifts the columns).
                continue
            ind = _parse_individual(row.get("individual_ratings"))
            if require_individual and not ind:
                continue
            try:
                n = int(float(row["n"])) if row.get("n") else (len(ind) if ind else None)
            except ValueError:
                n = len(ind) if ind else None
            items.append(
                {"unit": unit, "mean": mean, "std": row.get("std") or None, "n": n,
                 "individual": ind}
            )
            if limit and len(items) >= limit:
                break
    return items


# "on a scale from 1 to 7", and equally "from 1 (disagree) to 7 (agree)":
# the anchor wording carries a parenthesised label often enough that requiring
# the endpoints to be adjacent silently rejected 23 of the 64 published sets.
_SCALE_RE = re.compile(
    r"scale\s+(?:from|of)\s+(-?\d+)\s*(?:\([^)]{0,60}\)\s*)?"
    r"(?:to|-|–)\s*(-?\d+)", re.IGNORECASE
)


def _fits(items, lo, hi):
    """Do the study's own numbers sit inside the scale the text claims?

    Guards against a sentence elsewhere in the instructions being mistaken for
    the response scale. Means are allowed half a point of slack; a dataset that
    reports something on a different footing (gatti2024 publishes best-worst
    scores, not Likert means) fails this and is left to an explicit --scale.
    """
    if not items:
        return True
    vals = [v for it in items if it.get("individual") for v in it["individual"]]
    if vals:
        return min(vals) >= lo - 0.001 and max(vals) <= hi + 0.001
    means = [it["mean"] for it in items if it.get("mean") is not None]
    if not means:
        return True
    return min(means) >= lo - 0.51 and max(means) <= hi + 0.51


# A scale the text states but the published numbers cannot confirm, because the
# study reported on a different footing. Listing it here is a deliberate,
# reviewable decision rather than a silent fallback.
SCALE_OVERRIDES = {
    # Andrea rewrote these instructions as single-item 1-9 valence ratings
    # (2026-08-21). The humans did best-worst scaling, so the published column
    # is a 0-1 preference score, not a Likert mean: the model is scorable on
    # 1-9, but only the ranking is comparable across the two paradigms.
    "gatti2024_pseudoword_valence_intuitive": (1, 9),
    "gatti2024_pseudoword_valence_semantic_task": (1, 9),
}


def resolve_scale(instruction_text, items=None, override=None, task=None):
    """Return (lo, hi) integer endpoints of the response scale.

    Priority: explicit override > "scale from X to Y" in the instructions >
    the observed range of the human individual ratings.
    """
    if override:
        lo, hi = (int(x) for x in re.split(r"[-,: ]+", str(override).strip()) if x != "")
        return lo, hi
    if task and task in SCALE_OVERRIDES:
        return SCALE_OVERRIDES[task]
    if instruction_text:
        m = _SCALE_RE.search(instruction_text)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo > hi:
                lo, hi = hi, lo
            if hi - lo + 1 <= MAX_SCALE_POINTS and _fits(items, lo, hi):
                return lo, hi
    if items:
        # a scale taken from the text is only trusted if the ratings the study
        # published actually live inside it
        vals = [v for it in items if it.get("individual") for v in it["individual"]]
        if vals and all(float(v).is_integer() for v in vals):
            lo, hi = int(min(vals)), int(max(vals))
            if 1 < hi - lo + 1 <= MAX_SCALE_POINTS:
                return lo, hi
    raise ValueError(
        "could not resolve a discrete rating scale; pass --scale LO-HI explicitly "
        "(free-numeric tasks such as kuperman2012 age-of-acquisition are not "
        "scorable by option logprobs)"
    )


def human_counts(individual, lo, hi):
    """Bin one item's raw human responses into a length-(hi-lo+1) count vector."""
    k = hi - lo + 1
    counts = [0] * k
    dropped = 0
    for v in individual or []:
        iv = int(round(float(v)))
        if lo <= iv <= hi:
            counts[iv - lo] += 1
        else:
            dropped += 1
    return counts, dropped
