---
name: plan-and-build
description: Run a two-step workflow for a code change. First the planner subagent reads the code and writes a plan (no edits), then the builder subagent writes the code from that plan. Use when the user asks to plan and build, plan then implement, or invokes this skill.
---

Run this workflow for the change the user described: $ARGUMENTS

If no change was described, ask the user what to build and stop.

## Step 1: Plan
Start the `planner` subagent (it may be listed as `mods:planner`). Give it:
- the user's request, word for word
- any context from this conversation it needs (file paths, constraints, decisions already made), because it cannot see this conversation

Wait for it to finish.

## Step 2: Check the plan
- If the plan's "Risks and open questions" section starts with `BLOCKED:`, do NOT start the builder. Show the user the question and the plan, and stop.
- If the plan is clearly incomplete or does not match the request, run the planner once more with a note on what is missing. Do not loop more than once; after that, show the user and stop.
- Otherwise show the user a short summary of the plan (goal, files, steps) and continue.

## Step 3: Build
Start the `builder` subagent (it may be listed as `mods:builder`). Give it:
- the user's original request
- the planner's full plan, copied word for word. Do not summarize or shorten it: the builder sees nothing else.

Wait for it to finish.

## Step 4: Report
Tell the user:
- what was changed (from the builder's file list)
- any deviations from the plan
- check results, saying plainly if any check failed
Do not claim the work is done if a check failed or was not run.
