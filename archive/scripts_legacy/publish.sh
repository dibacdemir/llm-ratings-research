#!/bin/bash
# Rebuild, encrypt, and stage the site — then you decide whether to push.
#
#   scripts/publish.sh                 rebuild, encrypt, preview locally
#   scripts/publish.sh --push          ...and push to GitHub Pages
#   PASSPHRASE=... scripts/publish.sh  non-interactive
#
# Nothing leaves the machine until --push. The preview it prints is the same
# file that would be published, gate and all, so what you approve is what ships.

set -euo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"

echo "== 1. what is on disk =="
BEFORE=$(find result -name '*__autofmt.jsonl' | wc -l)
echo "   $BEFORE scored runs"

echo
echo "== 2. rebuild the pages =="
scripts/refresh_pages.sh >/tmp/publish_build.log 2>&1 || {
    tail -20 /tmp/publish_build.log; exit 1; }
grep -E '^wrote' /tmp/publish_build.log | sed 's/^/   /'

echo
echo "== 3. encrypt =="
"$PY" scripts/publish_site.py ${PASSPHRASE:+--passphrase "$PASSPHRASE"} | sed 's/^/   /'

echo
echo "== 4. preview =="
PORT=${PORT:-8080}
echo "   on your laptop:  ssh -N -L $PORT:$(hostname):$PORT $USER@$(hostname).mit.edu"
echo "   then open:       http://localhost:$PORT/"
echo "   (Ctrl-C stops the preview; nothing has been pushed)"

if [ "${1:-}" = "--push" ]; then
    echo
    echo "== 5. push =="
    git add docs
    git commit -m "site: $BEFORE runs" || echo "   nothing changed"
    git push
    URL=$(git remote get-url origin | sed -E 's#.*github.com[:/]([^/]+)/(.+?)(\.git)?$#https://\1.github.io/\2/#')
    echo "   live in a minute or two at: $URL"
    exit 0
fi

cd docs && exec "$PY" -m http.server "$PORT"
