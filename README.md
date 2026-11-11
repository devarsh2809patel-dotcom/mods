# mods

A Claude Code plugin with personal subagents and workflows.

## What's inside

| Part | Type | Model | What it does |
| --- | --- | --- | --- |
| `quick-fixer` | subagent | haiku | Typos, renames, formatting and other small, clear edits |
| `planner` | subagent | opus | Reads the code and writes an implementation plan. Read-only: it has no edit or shell tools |
| `builder` | subagent | sonnet | Writes the code by following the planner's plan |
| `plan-and-build` | skill | — | Runs planner, then hands its full plan to builder |
| `dashboard` | skill + hooks | — | Live dashboard of every Claude Code event; starts by itself |

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

A live web page showing every prompt, tool call, subagent and error from your Claude Code sessions,
in any repo where this plugin is installed. Events are labelled with the project folder name.

- **Starts by itself** when a session starts (in the background; first start on a fresh machine takes about a minute).
  Events sent before it is ready are queued and replayed, so nothing is lost.
- **Open it:** ask Claude to "open the dashboard" (or run `/mods:dashboard`). On your own computer it is http://localhost:5173.
  In a Claude cloud session, open the "dashboard" port preview in the Claude app.
- **Stop it:** ask Claude to stop the dashboard, or run `dashboard/stop.sh`.
- **Needs:** `bun`, `git`, `python3`. Without `bun` the plugin stays silent and does nothing.
- **Privacy:** data stays on the machine the session runs on (`~/.cache/mods/observability`).
  The data server only accepts connections from that machine. On a personal computer the page does too.

It uses the server and web page from
[disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability),
downloaded at a pinned version into `~/.cache/mods/observability` (not copied into this repo).

## Use it in every Claude cloud session

Add this to your cloud environment's setup script (Settings → environment → setup script).
It needs this repository to be public.

```bash
claude plugin marketplace add devarsh2809patel-dotcom/mods || true
claude plugin install mods@mods --scope user || true
```
