# Skills reach each other through their files, fan out through orchestrate, and call in one direction

The skills work as one set: a sweep hands its copy to ai-slop-prose, an audit asks mutation-check for evidence, large jobs run on parallel agents. Most of them are user-invoked, so they have no description another skill can fire (see the `writing-for-agents` skill mechanics). A skill therefore reaches another in one of three ways:

1. **Model-invoked target** (ai-slop-prose, mutation-check, orchestrate): name the skill in the step, and the agent loads it.
2. **User-invoked target** (ai-slop-design, ai-slop-audit, doc-truth): read the target's mode file or script from where it is installed, `${CLAUDE_SKILL_DIR}/../<skill>/` when the set is installed together, otherwise wherever the agent finds it, and follow it.
3. **Fan-out**: a step over more than three independent units hands them to orchestrate as a job (name, units, profile, unit brief, writable paths). orchestrate sizes the workers to free memory, checkpoints each unit, and goes inline for small jobs. Work that needs every unit at once (duplication counted across files) stays with the caller, before the fan-out or after the merge.

Every companion is optional: each step says what to do when the target is not installed, so a single-skill install still works (ADR 0005).

## Call graph

Calls go one way; no skill calls back into its caller.

- buyer-panel → orchestrate (interviews in batches of buyers), ai-slop-prose (the report, the pitch, the test kit), ai-slop-design (the smoke-test page in `test`)
- ai-slop-design → ai-slop-prose (visible copy; an audit runs only its scanner, read-only), orchestrate (sweeps of more than 3 files, craft variants, an audit's surfaces)
- ai-slop-audit → mutation-check (tautological tests), ai-slop-design's scanner (frontend duplication), ai-slop-design's ledger (reads `.slop-design/findings.md`: when it exists, frontend duplication is marked `handoff:ai-slop-design`), orchestrate (module scan)
- ai-slop-prose → orchestrate (sweeps of more than 3 files)
- doc-truth → orchestrate (more than 3 files)
- supah-help → reads every SKILL.md, calls none

Not edges: ai-slop-design never calls ai-slop-audit nor reads `.slop-audit/`; cross-module component work stays in its own audit as a token/component batch, and only work outside the frontend files is listed for the user to run with `/ai-slop-audit`, so the code audit's use of the design scanner and ledger stays one-way. mutation-check does not fan out, because it changes the file under test in place and two runs on one checkout would see each other's mutants. context-audit reads one set of transcripts and settings, which is one unit. buyer-panel's judge runs in its own subagent context, not as a skill.

## Considered options

- Making every skill model-invoked so the Skill tool can fire it: rejected; each description costs context in every session, and the user-invoked skills are heavy, deliberate jobs.
- A shared library imported across skills: rejected; per-skill installs cannot reach files outside their folder, which is why slop-guard carries copies (ADR 0008).
- Two-way calls (ai-slop-prose asking ai-slop-design to sweep a page it is editing): rejected; a cycle can loop, and each pair has one natural owner of the hand-over.

## Consequences

- A new skill that calls another adds its edge to the graph above, says what happens when the target is absent, and gets a supah-help row.
- A skill that fans out names its job, profile and unit brief in the step, as ai-slop-prose and ai-slop-design do.
