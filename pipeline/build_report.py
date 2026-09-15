#!/usr/bin/env python
"""Render result/report.html from the template plus report_data.json.

The page is self-contained (an artifact CSP blocks every external request), so
the data is inlined at the `/*__DATA__*/` marker rather than fetched.

    python pipeline/build_report_data.py && python pipeline/build_report.py
"""

import argparse
import json
import os
import sys


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="result/report_data.json")
    ap.add_argument("--template", default="result/report_template.html")
    ap.add_argument("--out", default="result/report.html")
    ap.add_argument("--extra", metavar="MARKER=FILE", action="append", default=[],
                    help="inline another json payload at another marker, e.g. "
                         "--extra PROMPTS=result/data/prompts.json. Skipped "
                         "silently when the file is absent, so a page can be "
                         "built before every payload exists.")
    args = ap.parse_args(argv)

    with open(args.template, encoding="utf-8") as fh:
        tpl = fh.read()
    if "/*__DATA__*/" not in tpl:
        sys.exit("template has no /*__DATA__*/ marker")
    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)

    # separators + no indent: the payload is inlined into a <script>, and the
    # page has to stay under the artifact size limit
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    # </script> inside a string literal would end the block early
    blob = blob.replace("</", "<\\/")
    html = tpl.replace("/*__DATA__*/", blob)
    for spec in args.extra:
        marker, _, path = spec.partition("=")
        token = "/*__%s__*/" % marker
        if token not in tpl:
            sys.exit("template has no %s marker" % token)
        if not os.path.exists(path):
            html = html.replace(token, "null")
            continue
        with open(path, encoding="utf-8") as fh:
            more = json.dumps(json.load(fh), separators=(",", ":"),
                              ensure_ascii=False).replace("</", "<\\/")
        html = html.replace(token, more)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    kb = os.path.getsize(args.out) / 1024
    # the same renderer serves both pages, whose payloads differ in shape
    n = data.get("n_runs", len(data.get("pairs", [])))
    what = "runs" if "n_runs" in data else "pairs"
    print("wrote %s (%.0f KB, %d %s, %d tasks)"
          % (args.out, kb, n, what, len(data.get("tasks", []))))
    if kb > 15 * 1024:
        print("warning: %.1f MB is near the 16 MB artifact limit" % (kb / 1024),
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
