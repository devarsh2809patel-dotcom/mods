#!/usr/bin/env python3
"""Send a Claude Code hook event to the local observability server.

Minimal, dependency-free sender compatible with the event format of
github.com/disler/claude-code-hooks-multi-agent-observability.
Never blocks Claude: any failure exits 0 silently. Events sent before the
dashboard is up are queued and replayed by dashboard/start.sh.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

CACHE = os.path.join(os.path.expanduser("~"), ".cache", "mods", "observability")
PENDING = os.path.join(CACHE, "pending.jsonl")
PENDING_MAX_BYTES = 20 * 1024 * 1024

FORWARDED_FIELDS = (
    "tool_name", "tool_use_id", "error", "is_interrupt", "permission_suggestions",
    "agent_id", "agent_type", "agent_transcript_path", "stop_hook_active",
    "notification_type", "custom_instructions", "source", "reason",
)


def model_from_transcript(path):
    """Find the latest assistant model name by reading only the end of the transcript."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 256 * 1024))
            lines = f.read().decode("utf-8", "ignore").splitlines()
        for line in reversed(lines):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") == "assistant":
                model = (entry.get("message") or {}).get("model")
                if model:
                    return model
    except OSError:
        pass
    return ""


def read_chat(path):
    chat = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    chat.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return chat


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--event-type", required=True)
    p.add_argument("--source-app", default=os.environ.get("OBS_SOURCE_APP"))
    p.add_argument("--server-url", default=os.environ.get("OBS_SERVER_URL", "http://127.0.0.1:4000/events"))
    p.add_argument("--add-chat", action="store_true")
    args = p.parse_args()

    try:
        data = json.load(sys.stdin)
    except ValueError:
        return

    transcript = data.get("transcript_path") or ""
    # Label events with the project folder name unless told otherwise
    source_app = args.source_app or os.path.basename((data.get("cwd") or os.getcwd()).rstrip("/")) or "claude"
    event = {
        "source_app": source_app,
        "session_id": data.get("session_id", "unknown"),
        "hook_event_type": args.event_type,
        "payload": data,
        "timestamp": int(time.time() * 1000),
        "model_name": model_from_transcript(transcript) if transcript else "",
    }
    for key in FORWARDED_FIELDS:
        if key in data:
            event[key] = data[key]
    if args.add_chat and transcript:
        event["chat"] = read_chat(transcript)

    req = urllib.request.Request(
        args.server_url,
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=2).close()
    except Exception:
        queue(event)  # dashboard not up yet: keep it for start.sh to replay


def queue(event):
    """Save an event the dashboard could not take yet. Never raises."""
    try:
        os.makedirs(CACHE, exist_ok=True)
        if os.path.exists(PENDING) and os.path.getsize(PENDING) > PENDING_MAX_BYTES:
            return
        event.pop("chat", None)  # transcripts are large; the replayed event keeps the rest
        with open(PENDING, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
