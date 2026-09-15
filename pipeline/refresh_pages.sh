#!/bin/bash
# Rebuild both HTML pages from whatever runs currently exist in result/.
# Run this after any new scoring job; nothing else needs touching.
#
#   pipeline/refresh_pages.sh              rebuild the two pages
#   pipeline/refresh_pages.sh --serve      rebuild, then serve them on :8000
#
# Both pages are self-contained (data inlined, no network), so they also open
# straight from disk with file:// or VS Code's preview.

set -euo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"

# Several sweep jobs can finish at once and each rebuilds at exit; without a
# lock they interleave writes to the same files and produce a truncated page.
# Re-exec once under flock, waiting rather than failing.
if [ -z "${_PAGES_LOCKED:-}" ]; then
    export _PAGES_LOCKED=1
    exec flock "$REPO/result/.pages.lock" "$0" "$@"
fi

echo "== gathering runs =="
"$PY" pipeline/build_report_data.py
"$PY" pipeline/build_explorer_data.py
# every pair's items, compressed, so the standalone/artifact copy has them too
"$PY" pipeline/pack_inspector_data.py
# the dataset catalogue: every dataset's prompt, whether or not it was scored
"$PY" pipeline/build_prompt_data.py

echo
echo "== rendering =="
"$PY" pipeline/build_report.py \
    --data result/report_data.json \
    --template result/report_template.html \
    --out result/report.html
"$PY" pipeline/build_report.py \
    --data result/explorer_data.json \
    --template result/inspector_template.html \
    --extra PROMPTS=result/data/prompts.json \
    --extra PACK=result/data/explorer.pack.json \
    --out result/inspector.html

# index.html so that opening the server root lands somewhere useful instead of
# a directory listing of every model folder
NRUNS=$("$PY" -c "import json;print(json.load(open('result/report_data.json'))['n_runs'])")
NPAIRS=$("$PY" -c "import json;print(len(json.load(open('result/explorer_data.json'))['pairs']))")
cat > result/index.html <<HTML
<meta charset="utf-8">
<title>LLM ratings</title>
<style>
:root{--bg:#f3f5f7;--fg:#15181d;--dim:#68717e;--card:#fff;--rule:#dde2e8;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root{--bg:#0f1216;--fg:#e8ebef;--dim:#8d97a4;
  --card:#171b21;--rule:#28303a;--accent:#3987e5}}
body{margin:0;background:var(--bg);color:var(--fg);min-height:100vh;display:grid;
  place-items:center;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{width:min(560px,90vw);padding:32px 0}
h1{font-family:ui-serif,Georgia,serif;font-size:26px;margin:0 0 6px}
p.sub{color:var(--dim);margin:0 0 26px;font-size:14.5px}
a.card{display:block;background:var(--card);border:1px solid var(--rule);border-radius:10px;
  padding:18px 20px;margin-bottom:12px;text-decoration:none;color:inherit}
a.card:hover{border-color:var(--accent)}
a.card b{display:block;font-size:17px;color:var(--accent);margin-bottom:3px}
a.card span{color:var(--dim);font-size:14px}
footer{color:var(--dim);font-size:12.5px;margin-top:22px}
code{background:var(--bg);border:1px solid var(--rule);padding:1px 5px;border-radius:3px;font-size:12px}
</style>
<main>
  <h1>LLM ratings vs human raters</h1>
  <p class="sub">$NRUNS runs · $NPAIRS model-task pairs · rebuilt $(date '+%Y-%m-%d %H:%M')</p>
  <a class="card" href="inspector.html"><b>Item Inspector →</b>
     <span>Pick a task and a model: the exact prompt, its answer, the raters' answers,
     item by item. Second tab has the model × task heatmap.</span></a>
  <a class="card" href="report.html"><b>Analysis →</b>
     <span>Every run together: scale usage, diagnostics, cross-model comparison.</span></a>
  <footer>Regenerate with <code>pipeline/refresh_pages.sh</code>.</footer>
</main>
HTML

echo
echo "Open locally:"
echo "  $REPO/result/index.html       (start here)"
echo "  $REPO/result/inspector.html   (pick a task + model, see prompts and items)"
echo "  $REPO/result/report.html      (cross-model analysis)"

if [ "${1:-}" = "--serve" ]; then
    PORT=${PORT:-8000}
    echo
    echo "  1. on your laptop:  ssh -N -L $PORT:$(hostname):$PORT $USER@$(hostname).mit.edu"
    echo "  2. then open:       http://localhost:$PORT/"
    echo
    echo "Ctrl-C here stops the server."
    cd result && exec "$PY" -m http.server "$PORT"
fi
