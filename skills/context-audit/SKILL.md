---
name: context-audit
description: Measure what every Claude Code session loads before you type, and find the instructions, memories and plugins that contradict each other or hold development back.
argument-hint: "[project dir]"
disable-model-invocation: true
allowed-tools: Bash(python *ctx.py*)
---

# Context audit

Everything always loaded (instructions, memories, skill and tool listings, hook text) is a standing cost and a standing order. The job: put a measured number on the cost, and give every standing order that conflicts with another, or with the repo, a verdict.

Claude Code fills in `${CLAUDE_SKILL_DIR}` (this skill's folder) and `$ARGUMENTS` (what the user typed after the skill name); elsewhere, resolve them yourself. `measure` and `sources` read Claude Code's transcripts and settings; `check` also works on any repo with an `AGENTS.md`.

**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when the answer is a fact about the world. What only the user can decide, ask as one question with 2 to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's `AskUserQuestion` shows them on screen, other agents number them in the reply.

**Next step.** End every run with the next step of the workflow, worked out from what this run left (the ledger's statuses, failed or blocked units, a question still open, the user's goal): the exact command and its reason in one line, and when two fit, both, the recommended one first; a skill that keeps a `STATUS.md` writes the same command as its next action. Put `/clear` before it (on another agent, a new session) when this run left its state on disk for that command to read; keep the session when the next step answers this run in conversation. When another skill called this one, hand the result back to it instead. When nothing is left, say the workflow is done.

The script is `python "${CLAUDE_SKILL_DIR}/scripts/ctx.py"`, run with `--project <dir>` when `$ARGUMENTS` names one. Transcripts hold the user's conversations: quote hook text and file lines, never prompts.

## Steps

1. **Measure**: `ctx.py measure`. Done when you have, for the last three sessions (all of them when there are fewer), the first request's measured tokens, the breakdown by category and owner, and each hook's cost; a `UserPromptSubmit` hook costs its tokens × prompts.
2. **Sources**: `ctx.py sources` lists the instruction files (with `@imports`), the memory index and the plugins whose hooks run on every session or prompt.
3. **Candidates**: `ctx.py check --json`.
4. **Judge** every candidate and every rule line, one verdict each, using the kinds below. Read both sides before calling a pair: the skill descriptions in the listing, the full memory file, the instruction in its section.
5. **Report**, in this order, every section present even when empty:
   - cost: first-request tokens, then the ten largest owners with tokens, then per-prompt hook cost;
   - contradictions: both quotes, both sources, which one the agent obeyed in the transcript when that is visible;
   - duplicate triggers: the group, and which skill to keep;
   - stale references and sediment: each candidate with its verdict and reason;
   - limits: the rule, what it blocks, the evidence;
   - fixes: each with the tokens it saves or the conflict it removes, and who applies it.

**Completion.** Every `check` candidate has a verdict (`real` or `fp` with a reason), every rule line was read against the others on its topic, and the report has all six sections.

## Kinds

- **contradiction**: two always-loaded rules that one action cannot both satisfy ("invoke a skill before any response" against "act when you have enough information"; "write terse fragments" against a prose rule that flags fragment runs). Same topic, compatible scope, is not one.
- **duplicate trigger**: skills from different owners that fire on the same request, so the agent picks between them at random and both descriptions cost tokens. Skills on one topic that serve different steps (requesting a review and receiving one) are complementary.
- **stale reference**: `missing-path`, `missing-adr`, `index-missing-file`, `dangling-memory-link`. Real when the target was renamed or deleted; `fp` when the text names something that is created later or lives outside the project.
- **sediment**: a memory that restates the repo (an `AGENTS.md` rule, a config value), a `memory-not-indexed` file, an always-loaded line that no longer bears on the work. It costs tokens and drifts from its source.
- **limit**: a standing order that blocks or slows development: a pinned runtime past end of life, a process mandated on every action, a rule the repo already breaks, an always-on hook whose text never changes a decision.

## Fixes

Memories and repo files are fixed in place once the user approves the list: ask with options (apply all, apply some by number, change one first); for each contradiction, the options are its two quoted sides plus a merged wording. Settings, plugins and hooks belong to the user: give the exact change (`claude plugin disable <name>`, the `settings.json` key) and let them apply it. Rerun `measure` in a new session after changes; the new first-request number is the result.
