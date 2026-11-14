---
name: supah-help
description: Ask which supah skill or flow fits your situation, and why. A router over ai-slop-audit, ai-slop-prose, context-audit, mutation-check, orchestrate and the slop-guard hooks, with how they pair with mattpocock/skills.
argument-hint: "[what you are trying to do]"
disable-model-invocation: true
---

# supah-help

The user describes a situation (`$ARGUMENTS`; Claude Code fills it in, elsewhere read it from the request). Recommend the flow below that fits, the exact commands in order, and the reason behind each step. Answer in the user's language. When the situation fits two rows, ask one question that separates them; when `$ARGUMENTS` is empty, show the situations table and ask which one is theirs.

Read the SKILL.md of every skill you recommend (in this skill's sibling folders, `${CLAUDE_SKILL_DIR}/../<skill>/SKILL.md`, or wherever it is installed) before describing what it does or saying a step can be skipped; the lines here orient, the SKILL.md decides.

## The approach

Every recommendation follows these five habits. State the one behind each step you suggest.

1. **Evidence before change.** Nothing is deleted or rewritten on a hunch: a finding carries the commands that prove it, a prose hit carries its context. Code that looks unused may be reached by a string, a route or a config file.
2. **Measured, not guessed.** Thresholds come from corpora, memory budgets from the machine, precision from recorded verdicts. When a number is unknown, the flow measures it first.
3. **Small, reversible steps.** Fixes land in batches that revert on their own, behind the project's checks; a partial scan is reported as partial.
4. **People decide what leaves the machine.** Issues, pushes and approvals of fixes wait for the user; a sample of the model's own verdicts goes back to the user for audit.
5. **Standalone first, paired by configuration.** Each skill works alone; with mattpocock/skills installed, they read its configuration and hand it the work it owns, without copying its formats.

## Situations

| You are… | Flow | Why this way |
|---|---|---|
| looking at a codebase built fast with AI that feels bloated | `/ai-slop-audit audit` → `plan` → `fix B1` (one batch at a time) → `verify` | the audit proves every reach path before calling code dead; the plan records a test baseline, so each batch can be checked and reverted on its own |
| sharing that cleanup with a team or with agents | after `plan`: `/ai-slop-audit publish`, then work the issues with `fix #<n>` or `/implement #<n>` | issues carry their own done-when checks and evidence, so whoever picks one up needs no local state |
| cleaning the text people see in an app (UI copy, error messages, translations) | `/ai-slop-prose sweep src/**/*.tsx locales/*.json` | only visible strings are read, never comments or code; each text has a purpose (button, error…) and is rewritten for it |
| editing a page, post, email or README | `/ai-slop-prose sweep <file>` and say what it is for ("landing page", "onboarding email") | the purpose picks the rewrite rules in PURPOSES.md; calibration keeps human-sounding text untouched (under 1% of human documents need a fix) |
| paying for a big context before typing anything, or getting instructions that fight each other | `/context-audit` | the first request's tokens are measured from your transcripts and split by plugin, so you cut what costs most; every contradiction is quoted from both sides before anything changes |
| wanting Claude to avoid slop in every session, without asking | `claude plugin install slop-guard --marketplace guarriellocristianmichele/supah-skills` (Claude Code only) | its hooks add about 150 tokens of rules per session and scan only the prose Claude just saved, so clean work costs nothing |
| writing something new for people | nothing to type: ai-slop-prose drafts to its rules and sweeps its own draft | catching a tell while drafting is cheaper than sweeping it out afterwards |
| unsure whether the tests protect a refactor, or suspecting a test checks nothing | `/mutation-check <file> --function <name> <test command>` | each change the tests let through is a behaviour nobody checks; a survivor is called equivalent or a gap only after reading it |
| told by the scanner that fine text is slop | keep the hit with reason `fp`, finish the sweep, then `scan.py verdict`; once in a while `scan.py audit` | verdicts measure each rule's precision; noisy rules lose tier on their own, and your audit checks the model's judgement |
| running a job over many files, or a slow, loaded machine | nothing to type for the two skills above, they call `orchestrate`; `/orchestrate` for your own fan-out | agents are sized to free RAM, stopped newest-first under pressure, and resumed from `STOPPED_AGENTS_WORK.md` |
| coming back after an interrupted session | run the same command again | `.slop-audit/`, `.orchestrator/` and the verdict log keep the state; nothing restarts from zero |
| using mattpocock/skills as well | `/setup-matt-pocock-skills` once, then the flows above | `publish` uses their tracker and labels so `/triage` and `/implement` take over; design findings go to `/improve-codebase-architecture`; `verify` adds `code-review` |

## Boundaries

- A finding whose cure is a new interface, not a deletion, is design work: `/improve-codebase-architecture` (mattpocock) or a decision for the user, not `fix`.
- Documents agents consume (SKILL.md, AGENTS.md, CLAUDE.md) are out of scope for ai-slop-prose; `writing-for-agents` (mattpocock) covers them.
- Detecting who wrote a text is not offered: the skills remove catalogued patterns and say so, because authorship detection is unreliable.
