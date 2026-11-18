---
name: orchestrate
description: Run a job of work units inline or as parallel subagents sized to free RAM, with per-unit checkpoints and resume across sessions; units that change code in an order run as a blocker graph on worktrees merged into an integration branch. Use when a task or skill fans out over many modules, files, documents or planned batches.
argument-hint: "[job-name]"
allowed-tools: Bash(python *mem.py*) Bash(python *graph.py*) Bash(git worktree *)
---

# Orchestrate

The caller (a skill or the user) supplies a **job**: a name, the **units** (no unit needs another's output, except a graph job's blockers), the task brief for one unit, its done criterion, a **profile** (`light`: reads and searches; `build`: runs tests, typecheck or builds), and where workers may write besides their work file. Ask for whatever is missing. A job whose units change code and must land in an order is a **graph job** (Graph job, below).

A workflow that already runs its own subagents (the mattpocock `implement-spec` and `research`, for instance) keeps managing them; wrap only work that would otherwise run one unit at a time.

Size the pool from measured RAM, never from the unit count: subagents share Claude Code's process, and the RAM that matters is what their commands consume.

Written for Claude Code, which fills in `${CLAUDE_SKILL_DIR}` (this skill's folder) and `${CLAUDE_SESSION_ID}`, and provides background subagents, background shell commands and TaskStop. On another agent: resolve the placeholders yourself (use a timestamp as the session id), use its own subagent and background-process mechanisms, and when it has no background subagents, run the job inline with the same checkpoints.

**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when the answer is a fact about the world. What only the user can decide, ask as one question with 2 to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's `AskUserQuestion` shows them on screen, other agents number them in the reply.

**Next step.** End every run with the next step of the workflow, worked out from what this run left (the ledger's statuses, failed or blocked units, a question still open, the user's goal): the exact command and its reason in one line, and when two fit, both, the recommended one first. Put `/clear` before it (on another agent, a new session) when this run left its state on disk for that command to read; keep the session when the next step answers this run in conversation. When nothing is left, say the workflow is done.

## State

`<caller state dir>/orchestrator/<job>/`, or `.orchestrator/<job>/` at the repo root, listed in `.git/info/exclude`.

- `state.json`: `session` (`${CLAUDE_SESSION_ID}`), `profile`, `per_agent_mb`, `reserve_mb`, `dispatch_avail_mb`, `peak_workers`, `workers: [{id, units, status: running|done|stopped, started, task}]`. The watchdog reads it.
- `units.md`: `| unit | status |`, status `pending`, `assigned:<worker>`, `done` or `failed:<reason>`.
- `briefs/<worker>.md`: the exact prompt each worker got.
- `work/<worker>.md`: worker output; every finished unit ends with `<!-- unit:<id> done -->`. That marker is the **checkpoint**, and it outranks `units.md`; a checkpointed result that fails the done criterion does not count, and its unit returns to `pending`.
- `stop/<worker>`: the stop flag.
- `STOPPED_AGENTS_WORK.md`: one block per stopped worker, template below.

## Steps

1. **Resume.** When the state dir exists: workers `running` under another session are orphans; mark them `stopped` and give each a STOPPED block with reason `orphan: session <id> ended`. Units with a checkpoint are `done`. Units of `open` STOPPED blocks go back to `pending`.
2. **Size.** Run `python "${CLAUDE_SKILL_DIR}/scripts/mem.py" status --profile <profile>`, adding `--per-agent <state per_agent_mb>` when state holds a calibrated value. Go **inline** when `slots` ≤ 1 or at most 3 units are pending: run the units yourself, in order, writing the same checkpoints. Otherwise plan `min(slots, pending batches)` workers, each batch small enough for one fresh context.
3. **Dispatch.** On the first dispatch, store `status`'s `avail_mb` as `dispatch_avail_mb`. Per worker: write its brief, register it `running` in `state.json`, launch it with the Agent tool in the background, and record the task handle; keep `peak_workers` at the most workers ever running at once. Then start the **watchdog** with Bash in the background: `python "${CLAUDE_SKILL_DIR}/scripts/mem.py" watch --state <dir>`. One watchdog at a time.
4. **React** to each notification; between them, end your turn, since every worker and the watchdog wake you when they finish:
   - **Worker done**: set its status, mark its checkpointed units `done` and return the rest of its units to `pending` (a unit returned twice becomes `failed:<reason>`), re-run `status`, and fill free slots from `pending`, starting with `open` STOPPED blocks.
   - **Watchdog exit 3** (pressure): write a STOPPED block for each worker in `stop`, then restart the watchdog. Flagged workers finish their current unit and exit.
   - **Watchdog exit 4** (hard stop): stop the listed workers with TaskStop (load it with ToolSearch). Their checkpointed units stay `done`; the unit in flight returns to `pending`. Restart the watchdog.
   - **Watchdog exit 0** (idle): fill free slots, or move to step 5.
5. **Merge** the work files in unit order into the caller's output. Calibrate: from the idle output's `min_avail_mb`, set `per_agent_mb` = (`dispatch_avail_mb` − `min_avail_mb`) ÷ `peak_workers`, never below the profile default. Inline runs skip calibration.

**Completion.** Every unit is `done`, `failed:<reason>` or `blocked:<unit>`, every STOPPED block is `resumed as <id>`, and no worker is `running`. Otherwise report `PARTIAL: k/N units`; `STOPPED_AGENTS_WORK.md` is the resume point, and invoking the same job again continues from it.

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

## Graph job

The caller adds, per unit, its **blockers** (`blocked-by`, unit ids of the same job) and the `files` it may edit, and for the job: the **integration branch** name, the setup command a fresh worktree needs before its checks run (an install from the lockfile, or `none`), the checks to run after each merge, and the record step to apply after each merge. Every unit is one commit, so a worker takes one unit. `units.md` becomes `| unit | status | blocked-by | files |` in the caller's order; `state.json` also holds `branch`.

The steps above change as follows:

- **Resume**: reuse the branch `state.json` names; on a first run create it at HEAD (`git branch <branch>`). Keep its own worktree at `<dir>/integration` (`git worktree add <dir>/integration <branch>`), recreated when missing; every merge happens there and the user's checkout never changes branch. A worktree in `<dir>/wt/` whose unit is not `assigned` is left over: remove it and its unit branch.
- **Graph**: before Size, and after every merge and every failure, run `python "${CLAUDE_SKILL_DIR}/scripts/graph.py" frontier --state <dir>`. Exit 2 (a cycle or an unknown blocker): report it and stop; nothing is dispatched. Units it lists under `blocked` become `blocked:<root>` in `units.md`. Size and Dispatch take units from `frontier` only, and plan `min(slots, len(frontier))` workers.
- **Inline** (`slots` ≤ 1, or a frontier of one unit with nothing running): work the unit yourself in `<dir>/integration`, commit, run the after-merge checks and the record step.
- **Dispatch**: per unit, `git worktree add <dir>/wt/<unit> -b <branch>-<unit> <branch>` from the integration tip, so the unit sees every blocker's commit; then the worker brief with the Graph job lines.
- **Worker done**: a checkpoint and a commit: in `<dir>/integration`, `git merge --no-ff <branch>-<unit>`. A conflict (`git merge --abort`) or red after-merge checks (`git reset --hard ORIG_HEAD`) returns the unit to `pending`, to start again from the new tip; the second time it is `failed:<reason>`. A green merge: the unit is `done` and you run the record step. A worker that reports its own checks red, or ends without a commit, leaves its unit `failed:<reason>`. Either way, remove its worktree and branch (`git worktree remove --force`, `git branch -D`), then run Graph and fill free slots.
- **Watchdog stops**: a stopped unit's uncommitted work goes with its worktree; the unit returns to `pending` and starts again from the tip.
- **Merge** (step 5): the integration branch is the output; report each unit `done`, `failed:<reason>` or `blocked:<unit>`, then remove `<dir>/integration` (the branch stays). Calibrate as usual.

Graph job lines, appended to the worker brief:

```
Work only in <dir>/wt/<unit>, on branch <branch>-<unit>; run <setup> there first.
Read the caller's state at <absolute paths>; write nothing there.
Run every fan-out inside this unit inline, in order.
End the unit with one commit: <commit message>.
```
