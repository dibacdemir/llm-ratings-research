#!/bin/bash
# One link that always shows the latest results.
#
#   pipeline/serve.sh          start it (or report the one already running)
#   pipeline/serve.sh --stop   stop it
#
# The server stays up across sweeps and serves result/ straight from disk, so a
# rebuild is visible on a browser reload -- the link never changes. In VS Code
# the port is forwarded to your laptop automatically, so http://localhost:PORT
# works there with no ssh command.

set -euo pipefail
PY=${PY:-$HOME/.conda/envs/compressibility/bin/python}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO"
PORT=${PORT:-8000}
PIDF=result/.serve.pid

alive () { [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }

if [ "${1:-}" = "--stop" ]; then
    if alive; then kill "$(cat "$PIDF")"; rm -f "$PIDF"; echo "stopped"
    else echo "not running"; fi
    exit 0
fi

# a server from an earlier session can still hold the port without our pid file
if ! alive && ss -ltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
    OWNER=$(ss -ltnp "sport = :$PORT" 2>/dev/null | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
    if [ -n "$OWNER" ] && [ "$(ps -o user= -p "$OWNER" 2>/dev/null)" = "$USER" ]; then
        echo "port $PORT held by an older server of yours (pid $OWNER); reusing it"
        echo "$OWNER" > "$PIDF"
    else
        echo "port $PORT is taken by someone else; set PORT=... " >&2; exit 1
    fi
fi

if alive; then
    echo "already serving (pid $(cat "$PIDF"))"
else
    mkdir -p result/logs
    (cd result && nohup "$PY" -m http.server "$PORT" \
        >../result/logs/serve.log 2>&1 & echo $! > "$REPO/$PIDF")
    sleep 1
    alive || { echo "failed to start; see result/logs/serve.log" >&2; exit 1; }
    echo "started (pid $(cat "$PIDF"))"
fi

echo
echo "   http://localhost:$PORT/"
echo
echo "   In VS Code that link works as-is -- the port is forwarded for you."
echo "   Elsewhere, first run on your laptop:"
echo "     ssh -N -L $PORT:$(hostname):$PORT $USER@$(hostname).mit.edu"
