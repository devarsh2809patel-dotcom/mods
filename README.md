# mods

A Claude Code plugin with personal subagents and workflows.

## What's inside

| Part | Type | Model | What it does |
| --- | --- | --- | --- |
| `quick-fixer` | subagent | haiku | Typos, renames, formatting and other small, clear edits |
| `planner` | subagent | opus | Reads the code and writes an implementation plan. Read-only: it has no edit or shell tools |
| `builder` | subagent | sonnet | Writes the code by following the planner's plan |
| `plan-and-build` | skill | — | Runs planner, then hands its full plan to builder |

Use the workflow with `/mods:plan-and-build <what to build>`.

## Install

At the prompt of a Claude Code session:

```
/plugin install mods --marketplace devarsh2809patel-dotcom/mods
```

From a shell:

```bash
claude plugin install mods --marketplace devarsh2809patel-dotcom/mods
```

## Live dashboard (multi-agent observability)

A live web dashboard of every Claude Code event in this project: prompts, tool calls, subagents, errors.
It uses the server and web client from
[disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability),
fetched at a pinned commit into `~/.cache/mods/observability` (not copied into this repo).

- `.claude/settings.json` sends all 12 hook events to the dashboard via `.claude/hooks/send_event.py`
  (plain Python, no dependencies, no API calls; drops events silently if the dashboard is not running).
- `dashboard/start.sh` installs and starts it. Needs `bun` and `git`.
- `dashboard/stop.sh` stops it.

```bash
./dashboard/start.sh
```

Then open http://localhost:5173. The web page reaches the server through its own address (`/obs`),
so it also works through a port preview in a cloud session.

Note: the dashboard stores prompts, tool inputs and tool outputs in a local SQLite file
(`~/.cache/mods/observability/apps/server/events.db`).
