---
name: dashboard
description: Start (if needed) and open the live multi-agent observability dashboard that shows every prompt, tool call and subagent in Claude Code sessions. Use when the user asks to open, show, start, stop or check the dashboard, or asks where it is.
---

The dashboard starts by itself when a session starts. This skill makes sure it is running and tells the user how to open it.

1. Run `"${CLAUDE_PLUGIN_ROOT}/dashboard/start.sh"` (no flag: it waits until ready; it is quick if already running). The first start on a fresh machine installs packages and can take about a minute.
   - If the user asked to stop it, run `"${CLAUDE_PLUGIN_ROOT}/dashboard/stop.sh"` instead and stop here.
   - If it fails, show the user the last lines of the logs it names and stop.
2. Tell the user how to open it, in this order:
   - If the environment variable `CLAUDE_CODE_REMOTE` is `true` (a cloud session): call the `report_preview_port` tool with port `5173` and name `dashboard` if that tool is available, then tell the user to open the "dashboard" preview in their Claude app. Say plainly that some app versions do not show previews.
   - Otherwise (their own computer): tell them to open http://localhost:5173 in their browser.
3. Keep it short: one line on where to open it, one line that events appear live as Claude works.
