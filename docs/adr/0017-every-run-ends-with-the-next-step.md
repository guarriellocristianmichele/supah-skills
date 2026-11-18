# Every run ends with the next step of its workflow

Every skill carries the same paragraph, **Next step**, right after **Ask with options**: a run ends by working out the next step of the workflow from what it left (the ledger's statuses, failed or blocked units, a question still open, the user's goal) and giving the exact command with its reason in one line. When two commands fit, both are given, the recommended one first. When the run left its state on disk for that command to read, `/clear` comes before it (a new session on another agent), because the next command reads the state back and the old context only costs tokens and can steer it. The session is kept when the next step answers this run in conversation (approving drafts, choosing a direction). A skill another skill called (orchestrate, ai-slop-prose inside a sweep) hands its result back to the caller, whose own run ends with the next step.

The flows are long (`audit`, `plan`, `publish`, `fix all`, `verify`; a buyer panel's rounds), and most skills are user-invoked, so the user has to remember which command comes next and when a fresh context is safe. Reading the next step from the state, rather than from a fixed sequence, keeps the advice right after a partial run, a failed batch or a skipped step.

## Considered options

- A fixed "next" line per mode: rejected; it is wrong whenever the run ended partial, failed or with work left out, which is when the user most needs the advice.
- Leaving it to supah-help: rejected; the user would have to call a second skill after every command, and per-skill installs may not have it.
- One shared file every skill points at: rejected for the reason in ADR 0013; the paragraph is repeated in each SKILL.md, worded identically.

## Consequences

- A new skill copies the paragraph verbatim after Ask with options; `python scripts/release.py --check` fails a SKILL.md without it.
- supah-help, which writes whole sequences, writes `/clear` inside them by the same rule.
- A mode whose `STATUS.md` holds a next action writes the same command it ends the run with.
