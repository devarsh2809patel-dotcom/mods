#!/usr/bin/env bash
# Start the multi-agent observability dashboard (server + web client).
# Upstream code is fetched at a pinned commit into a cache folder, not copied into this repo.
set -euo pipefail

REPO_URL="https://github.com/disler/claude-code-hooks-multi-agent-observability.git"
PINNED_COMMIT="8a6e5cf795df50767cea7123703751282a819697"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${OBS_DIR:-$HOME/.cache/mods/observability}"
LOGS="$DIR/logs"
export SERVER_PORT="${SERVER_PORT:-4000}" CLIENT_PORT="${CLIENT_PORT:-5173}"

command -v bun >/dev/null || { echo "bun is required: https://bun.sh" >&2; exit 1; }

if [ ! -d "$DIR/.git" ]; then
  mkdir -p "$(dirname "$DIR")"
  git clone --quiet "$REPO_URL" "$DIR"
fi
git -C "$DIR" fetch --quiet origin "$PINNED_COMMIT" 2>/dev/null || true
git -C "$DIR" checkout --quiet "$PINNED_COMMIT"

(cd "$DIR/apps/server" && bun install --silent)
(cd "$DIR/apps/client" && bun install --silent)
cp "$HERE/vite.mods.config.ts" "$DIR/apps/client/vite.mods.config.ts"

"$HERE/stop.sh" >/dev/null 2>&1 || true
mkdir -p "$LOGS"

(cd "$DIR/apps/server" && setsid nohup bun src/index.ts </dev/null >"$LOGS/server.log" 2>&1 & echo $! >"$LOGS/server.pid")
(cd "$DIR/apps/client" && setsid nohup bunx vite --config vite.mods.config.ts </dev/null >"$LOGS/client.log" 2>&1 & echo $! >"$LOGS/client.pid")

for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:$SERVER_PORT/events/filter-options" >/dev/null 2>&1 \
     && curl -fsS "http://localhost:$CLIENT_PORT" >/dev/null 2>&1; then
    echo "Dashboard:  http://localhost:$CLIENT_PORT"
    echo "Server API: http://localhost:$SERVER_PORT"
    echo "Logs:       $LOGS"
    exit 0
  fi
  sleep 1
done
echo "Dashboard did not start in 30s. See logs in $LOGS" >&2
exit 1
