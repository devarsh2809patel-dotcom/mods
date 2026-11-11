#!/usr/bin/env bash
# Start the multi-agent observability dashboard (server + web page).
#   start.sh               start it and wait until it is ready
#   start.sh --background  return at once; start it in the background if it is not running
# Upstream code is fetched at a pinned commit into a cache folder, not copied into this repo.
set -euo pipefail

REPO_URL="https://github.com/disler/claude-code-hooks-multi-agent-observability.git"
PINNED_COMMIT="8a6e5cf795df50767cea7123703751282a819697"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${OBS_DIR:-$HOME/.cache/mods/observability}"
SRC="$DIR/upstream"
LOGS="$DIR/logs"
LOCK="$DIR/start.lock"
export SERVER_PORT="${SERVER_PORT:-4000}" CLIENT_PORT="${CLIENT_PORT:-5173}"

running() {
  curl -fsS -m 2 "http://127.0.0.1:$SERVER_PORT/events/filter-options" >/dev/null 2>&1 &&
  curl -fsS -m 2 "http://127.0.0.1:$CLIENT_PORT" >/dev/null 2>&1
}

mkdir -p "$DIR" "$LOGS"

if [ "${1:-}" = "--background" ]; then
  running && exit 0
  command -v bun >/dev/null || exit 0   # no bun: stay silent, never bother the session
  setsid nohup "$0" </dev/null >"$LOGS/start.log" 2>&1 &
  exit 0
fi

if running; then
  echo "Dashboard already running: http://localhost:$CLIENT_PORT"
  exit 0
fi

# One starter at a time (several sessions can start together). Stale locks expire after 5 minutes.
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +5 2>/dev/null)" ]; then
    rm -rf "$LOCK"; mkdir "$LOCK"
  else
    echo "Dashboard is already starting; try again in a minute." >&2
    exit 0
  fi
fi
trap 'rm -rf "$LOCK"' EXIT

command -v bun >/dev/null || { echo "bun is required: https://bun.sh" >&2; exit 1; }

if [ ! -d "$SRC/.git" ]; then
  git clone --quiet "$REPO_URL" "$SRC"
fi
git -C "$SRC" cat-file -e "$PINNED_COMMIT" 2>/dev/null || git -C "$SRC" fetch --quiet origin
git -C "$SRC" checkout --quiet --force "$PINNED_COMMIT"

# Keep the API server private to this machine: the web page reaches it through its own proxy.
sed -i "s|port: parseInt(process.env.SERVER_PORT \|\| '4000'),|port: parseInt(process.env.SERVER_PORT \|\| '4000'), hostname: '127.0.0.1',|" "$SRC/apps/server/src/index.ts"
cp "$HERE/vite.mods.config.ts" "$SRC/apps/client/vite.mods.config.ts"

(cd "$SRC/apps/server" && bun install --silent)
(cd "$SRC/apps/client" && bun install --silent)

"$HERE/stop.sh" >/dev/null 2>&1 || true

(cd "$SRC/apps/server" && setsid nohup bun src/index.ts </dev/null >"$LOGS/server.log" 2>&1 & echo $! >"$LOGS/server.pid")
(cd "$SRC/apps/client" && setsid nohup bunx vite --config vite.mods.config.ts </dev/null >"$LOGS/client.log" 2>&1 & echo $! >"$LOGS/client.pid")

for _ in $(seq 1 60); do
  if running; then
    # Replay events sent while the dashboard was still starting
    if [ -s "$DIR/pending.jsonl" ]; then
      mv "$DIR/pending.jsonl" "$DIR/replaying.jsonl"
      python3 - "$DIR/replaying.jsonl" "$SERVER_PORT" <<'PY' || true
import sys, urllib.request
path, port = sys.argv[1], sys.argv[2]
for line in open(path, encoding="utf-8"):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/events", data=line.encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).close()
    except Exception:
        pass
PY
      rm -f "$DIR/replaying.jsonl"
    fi
    echo "Dashboard:  http://localhost:$CLIENT_PORT"
    echo "Logs:       $LOGS"
    exit 0
  fi
  sleep 1
done
echo "Dashboard did not start in 60s. See logs in $LOGS" >&2
exit 1
