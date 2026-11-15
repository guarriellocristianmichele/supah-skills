---
name: ai-slop-audit
description: Evidence-backed audit and cleanup of needless complexity across a codebase (dead code, duplication, wrappers, comment noise, tautological tests). Modes audit, plan, publish (GitHub issues), fix <ID>, verify.
argument-hint: "audit [path] | plan | publish [B<n>…] | fix <SLOP-ID[,ID]|B<n>|#issue> | verify"
arguments: [mode, target]
disable-model-invocation: true
effort: high
allowed-tools: Read Grep Glob Bash(python *codescan.py*) Bash(python *designscan.py*) Bash(git rev-parse *) Bash(git status *) Bash(git ls-files *) Bash(git log *) Bash(git diff *)
---

# AI slop audit

Mode `$mode` · target `$target` · arguments `$ARGUMENTS`
HEAD !`git rev-parse --short HEAD`

```!
git status --short
```

Claude Code fills in the placeholders and command output above, and `${CLAUDE_SKILL_DIR}` (this skill's folder) below. Where they still appear raw, take mode and target from the user's request and run `git rev-parse --short HEAD` and `git status --short` yourself.

**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when the answer is a fact about the world. What only the user can decide, ask as one question with 2 to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's `AskUserQuestion` shows them on screen, other agents number them in the reply.

**Slop** is complexity the code's behaviour does not need. Judge each candidate by what the code does and which reach paths hit it; style, length and suspected AI origin are not evidence. A claim without reproducible **evidence** stays out of the ledger.

## Modes

Read the mode's file in `${CLAUDE_SKILL_DIR}/` and follow it to its completion criterion, then rewrite `STATUS.md`.

| mode | file | writes |
|---|---|---|
| `audit [path]` | `AUDIT.md` | ledger |
| `plan` | `PLAN.md` | ledger |
| `publish [batches]` | `PUBLISH.md` | issue tracker, ledger |
| `fix <IDs>` | `FIX.md` | code the IDs name, ledger |
| `verify` | `VERIFY.md` | ledger |

Code changes happen in `fix` only, for the IDs given; tracker writes in `publish` only. Any other mode: show the argument-hint and `STATUS.md`, then stop.

## Ledger

`.slop-audit/` at the repo root is the single source of truth across sessions. Read `STATUS.md` first when it exists. On first run create the directory and append `.slop-audit/` to `.git/info/exclude`, keeping it untracked without touching `.gitignore`.

- `STATUS.md`: at most 15 lines: last mode and HEAD, coverage `k/N modules scanned`, finding counts by status, next action.
- `inventory.md`: `| module | paths | entrypoints | status |`, status `pending`, `scanned@<sha>` or `skipped:<reason>`.
- `findings.md`: one block per finding, schema below. IDs `SLOP-001` upward, never reused.
- `plan.md`: batches `B1` upward, each with `issue: #<n>` once published.
- `checks.md`: verification commands, baseline commit, baseline results.

Finding status: `open` → `planned` → `fixed`; `stale`, `rejected:<reason>` or `handoff:<skill>` from any state.

## Companions

The skill runs **standalone**, or **integrated** with the mattpocock engineering skills when `docs/agents/issue-tracker.md` exists (written by `/setup-matt-pocock-skills`). Integrated means reading their configuration and handing work to their skills; their files and formats stay theirs.

| Need | Integrated | Standalone |
|---|---|---|
| issue tracker | the operations in `docs/agents/issue-tracker.md`, labels from `docs/agents/triage-labels.md` | `gh` when `origin` is on GitHub and `gh auth status` passes; otherwise files in `.slop-audit/issues/` |
| vocabulary and decisions | `GLOSSARY.md` and `docs/adr/` when present | the same files when present |
| a fix that needs a new interface instead of a deletion | `handoff:improve-codebase-architecture` | `handoff:design`, listed for the human |
| a published batch already closed by `/implement` | synced to `fixed`, never rebuilt | the same |
| review in `verify` | the `code-review` skill (`mattpocock-skills:code-review` as a plugin) | `verify`'s own checks |

Their reserved paths (`docs/agents/`, `.scratch/`, `.out-of-scope/`) are read, never written.

## Findings

```
### SLOP-012 · wrapper · confidence: high · status: open
Where: src/http/client.ts:40-58 `getJson`
Claim: forwards to `fetchJson` unchanged; 3 callers.
Evidence: commands run and the output that proves the claim.
Reach paths: which were checked, and how.
Risk: what breaks if the claim is wrong.
Fix: one-line sketch.
```

**Reach paths** are every way code gets used: static imports; dynamic imports (`import()`, computed `require`, glob loaders); string references (reflection, DI tokens, templates, routes, serialized names); entrypoints; public API of published packages; config files; framework conventions; tests; sibling workspace packages.

Confidence:

- **high**: evidence closes every reach path, and rerunning its commands reproduces it.
- **medium**: static paths closed; one indirect path stays open (reflection, external consumers).
- **low**: suspicion. Kept out of plans until evidence upgrades it.
