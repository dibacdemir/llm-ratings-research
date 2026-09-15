"""What a norm CSV contains, computed once and remembered.

The page builders each needed the same handful of numbers per dataset -- how
many items, how many raters, which values appear, a few stimuli -- and each was
re-parsing every CSV to get them. With 331 datasets, some 66k rows long, that
made a rebuild take minutes, which is the difference between looking at results
while you work and not bothering.

The facts are small (about a kilobyte per dataset) and change only when a file
changes, so they are cached on disk keyed by the file's size and modification
time. A dataset the collaborators edit is re-read; the rest are free.
"""

import json
import os

CACHE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "result", ".facts.json")
_MEM = None


def _stamp(path):
    st = os.stat(path)
    return "%d:%d" % (st.st_size, st.st_mtime_ns)


def _load():
    global _MEM
    if _MEM is None:
        try:
            with open(CACHE, encoding="utf-8") as fh:
                _MEM = json.load(fh)
        except Exception:
            _MEM = {}
    return _MEM


def save():
    """Write the cache. Safe to skip; the next run just recomputes."""
    if _MEM is None:
        return
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        tmp = CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_MEM, fh, separators=(",", ":"))
        os.replace(tmp, CACHE)
    except OSError:
        pass


def facts(csv_path, samples=4):
    """Summary of one norm CSV, from cache when the file has not changed."""
    mem = _load()
    key = os.path.abspath(csv_path)
    stamp = _stamp(csv_path)
    hit = mem.get(key)
    if hit and hit.get("stamp") == stamp and hit.get("samples", 0) >= samples:
        return hit

    from llm_ratings import data
    items = data.load_items(csv_path)
    trial = [it for it in items if it["individual"]]
    ns = [len(it["individual"]) for it in trial]
    vals = sorted({round(float(v), 6)
                   for it in trial[:600] for v in it["individual"]})
    means = [it["mean"] for it in items if it.get("mean") is not None]

    picks = []
    if items:
        step = max(1, len(items) // samples)
        picks = [items[min(i * step, len(items) - 1)]["unit"]
                 for i in range(min(samples, len(items)))]
        odd = next((it["unit"] for it in items
                    if any(ord(c) > 127 for c in it["unit"])), None)
        if odd and odd not in picks:
            picks[-1] = odd

    out = {
        "stamp": stamp, "samples": samples,
        "n_items": len(items),
        "n_trial_items": len(trial),
        "median_raters": int(sorted(ns)[len(ns) // 2]) if ns else None,
        "min_raters": min(ns) if ns else None,
        "few_rater_items": sum(1 for n in ns if n < 5),
        "distinct_values": vals[:40],
        "n_distinct_values": len(vals),
        "all_integer": bool(vals) and all(abs(v - round(v)) < 1e-9 for v in vals),
        "mean_range": [min(means), max(means)] if means else None,
        "units": picks,
        "units_non_ascii": [u for u in picks if any(ord(c) > 127 for c in u)],
    }
    mem[key] = out
    return out
