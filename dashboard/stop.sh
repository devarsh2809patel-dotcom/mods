#!/usr/bin/env bash
# Stop the observability dashboard started by start.sh.
LOGS="${OBS_DIR:-$HOME/.cache/mods/observability}/logs"
for name in server client; do
  pidfile="$LOGS/$name.pid"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile")"
    # start.sh runs each process in its own session, so kill the whole group
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null
    echo "Stopped $name ($pid)"
    rm -f "$pidfile"
  fi
done
