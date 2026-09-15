#!/usr/bin/env python
"""Pack every pair's item data into one compressed blob for the standalone page.

Served locally, inspector.html loads result/data/index.json and fetches one
small file per pair on demand. Opened as a lone file, or published as an
artifact, no fetch is possible, so the page has to carry the items itself.
Uncompressed that is ~100 MB for 16 models x 285 tasks; gzip brings it to a
few MB because prompts and stimuli repeat across models. The page inflates it
with the browser's DecompressionStream.

    result/data/explorer.pack.json   a JSON string: base64(gzip(json))
    result/explorer_data.json        the stubs (statistics, no items)

Items per pair are trimmed from --sample down until the blob fits --budget-mb,
so the page stays publishable however many models are added; the page shows
"n of N items" from n_shown so nobody mistakes the sample for the whole.
"""

import argparse
import base64
import gzip
import json
import os

HEAVY = ("items", "prompt_text", "prompt_spans", "prompt_unit")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-dir", default="result/data")
    ap.add_argument("--out", default="result/data/explorer.pack.json")
    ap.add_argument("--stubs", default="result/explorer_data.json")
    ap.add_argument("--budget-mb", type=float, default=11.0,
                    help="cap on the base64 blob (the page must stay <16 MB)")
    ap.add_argument("--sample", type=int, default=120)
    args = ap.parse_args(argv)

    idx = json.load(open(os.path.join(args.split_dir, "index.json")))
    pairs = []
    for stub in idx["pairs"]:
        slug = "%s__%s.json" % (stub["model"], stub["task"])
        p = dict(stub)
        try:
            p.update(json.load(open(os.path.join(args.split_dir, slug))))
        except FileNotFoundError:
            pass
        pairs.append(p)

    blob, k_used = None, None
    for k in [k for k in (args.sample, 100, 80, 60, 40, 30, 20, 10)
              if k <= args.sample]:
        for p in pairs:
            if "items" in p:
                p["items"] = p["items"][:k]
                p["n_shown"] = len(p["items"])
        raw = json.dumps({"pairs": pairs, "tasks": idx["tasks"],
                          "models": idx["models"],
                          "task_info": idx.get("task_info", {}),
                          "items_per_pair": k},
                         separators=(",", ":")).encode("utf-8")
        b64 = base64.b64encode(gzip.compress(raw, 9)).decode("ascii")
        if len(b64) <= args.budget_mb * 1e6:
            blob, k_used = b64, k
            break
    if blob is None:
        raise SystemExit("cannot fit the pack in %.0f MB even at 10 items"
                         % args.budget_mb)

    with open(args.out, "w") as fh:
        json.dump(blob, fh)
    # the page inflates the pack for everything; the stubs file only has to
    # carry what the first paint needs (the task list), not 4,000 stat rows
    stubs = {"pairs": [],
             "tasks": idx["tasks"], "models": idx["models"],
             "task_info": idx.get("task_info", {}),
             "n_pairs_total": len(pairs), "packed": True}
    with open(args.stubs, "w") as fh:
        json.dump(stubs, fh, separators=(",", ":"))
    print("wrote %s: %d pairs, %d items per pair, %.1f MB (raw %.0f MB)"
          % (args.out, len(pairs), k_used, len(blob) / 1e6, len(raw) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
