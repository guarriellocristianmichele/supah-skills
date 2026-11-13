---
name: orchestrate
description: Run a job of independent work units inline or as parallel subagents sized to free RAM, with per-unit checkpoints, memory-pressure shedding into STOPPED_AGENTS_WORK.md, and resume across sessions. Use when a task or skill fans out over many modules, files or documents.
argument-hint: "[job-name]"
allowed-tools: Bash(python *mem.py*)
---

# Orchestrate

The caller (a skill or the user) supplies a **job**: a name, the **units** (independent: no unit needs another's output), the task brief for one unit, its done criterion, a **profile** (`light`: reads and searches; `build`: runs tests, typecheck or builds), and where workers may write besides their work file. Ask for whatever is missing.

Subagents run inside Claude Code's own process; the RAM that matters is what their commands consume. Measure it, never estimate it from the unit count.

Written for Claude Code, which fills in `${CLAUDE_SKILL_DIR}` (this skill's folder) and `${CLAUDE_SESSION_ID}`, and provides background subagents, background shell commands and TaskStop. On another agent: resolve the placeholders yourself (use a timestamp as the session id), use its own subagent and background-process mechanisms, and when it has no background subagents, run the job inline with the same checkpoints.

## State

`<caller state dir>/orchestrator/<job>/`, or `.orchestrator/<job>/` at the repo root, listed in `.git/info/exclude`.

- `state.json`: `session` (`${CLAUDE_SESSION_ID}`), `profile`, `per_agent_mb`, `reserve_mb`, `workers: [{id, units, status: running|done|stopped, started, task}]`. The watchdog reads it.
- `units.md`: `| unit | status |`, status `pending`, `assigned:<worker>`, `done` or `failed:<reason>`.
- `briefs/<worker>.md`: the exact prompt each worker got.
- `work/<worker>.md`: worker output; every finished unit ends with `<!-- unit:<id> done -->`. That marker is the **checkpoint**, and it outranks `units.md`.
- `stop/<worker>`: the stop flag.
- `STOPPED_AGENTS_WORK.md`: one block per stopped worker, template below.

## Steps

1. **Resume.** When the state dir exists: workers `running` under another session are orphans; mark them `stopped` and give each a STOPPED block. Units with a checkpoint are `done`. Units of `open` STOPPED blocks go back to `pending`.
2. **Size.** Run `python "${CLAUDE_SKILL_DIR}/scripts/mem.py" status --profile <profile>`, adding `--per-agent <state per_agent_mb>` when state holds a calibrated value. Go **inline** when `slots` ≤ 1 or at most 3 units are pending: run the units yourself, in order, writing the same checkpoints. Otherwise plan `min(slots, pending batches)` workers, each batch small enough for one fresh context.
3. **Dispatch.** Per worker: write its brief, register it `running` in `state.json`, launch it with the Agent tool in the background, and record the task handle. Then start the **watchdog** with Bash in the background: `python "${CLAUDE_SKILL_DIR}/scripts/mem.py" watch --state <dir>`. One watchdog at a time.
4. **React** to each notification:
   - **Worker done**: set its status, mark its checkpointed units `done`, re-run `status`, and fill free slots from `pending`, starting with `open` STOPPED blocks.
   - **Watchdog exit 3** (pressure): write a STOPPED block for each worker in `stop`, then restart the watchdog. Flagged workers finish their current unit and exit.
   - **Watchdog exit 4** (hard stop): stop the listed workers with TaskStop (load it with ToolSearch). Their checkpointed units stay `done`; the unit in flight returns to `pending`. Restart the watchdog.
   - **Watchdog exit 0** (idle): fill free slots, or move to step 5.
5. **Merge** the work files in unit order into the caller's output. Calibrate: from the idle output's `min_avail_mb`, set `per_agent_mb` = (free MB at dispatch − `min_avail_mb`) ÷ peak workers, never below the profile default.

**Completion.** Every unit is `done` or `failed:<reason>`, every STOPPED block is `resumed as <id>`, and no worker is `running`. Otherwise report `PARTIAL: k/N units`; `STOPPED_AGENTS_WORK.md` is the resume point, and invoking the same job again continues from it.

## Worker brief

```
You are worker <id> of job <job>. Your units, in order: <unit ids>.
<task brief for one unit>
For each unit:
1. If <dir>/stop/<id> exists, reply "stopped before <unit>" and end.
2. Work the unit until <done criterion>.
3. Append its result to <dir>/work/<id>.md, ending with <!-- unit:<unit> done -->.
Write only to that file<, plus the caller's allowed paths>. Reply with the units you finished.
```

## STOPPED_AGENTS_WORK.md block

```
## <worker> · stopped <ISO time> · <reason, e.g. memory: 1.9 GB free < 2.4 GB reserve>
Brief: briefs/<worker>.md
Done: <unit ids>
Remaining: <unit ids>
Checkpoint: work/<worker>.md
Status: open
```

Resuming dispatches a new worker with the same brief over `Remaining`, and sets `Status: resumed as <new id>`.
