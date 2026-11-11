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
