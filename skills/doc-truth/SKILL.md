---
name: doc-truth
description: Check that a repository's docs still tell the truth about it (links, anchors, commands, scripts, flags, make targets, environment variables), then fix the doc or report the code.
argument-hint: "[file…] (default: every tracked Markdown file)"
disable-model-invocation: true
allowed-tools: Bash(python *doctruth.py*) Bash(git ls-files *)
---

# Doc truth

A **claim** is anything a doc says the repository has: a linked file, a heading, a script, a flag, an npm script, a make target, an environment variable the code reads. The job: every claim in scope checked, and every false one resolved, either by fixing the doc or by reporting that the code lost something the doc promises.

Claude Code fills in `${CLAUDE_SKILL_DIR}` (this skill's folder) and `$ARGUMENTS` (what the user typed after the skill name); elsewhere, resolve them yourself. The script is `python "${CLAUDE_SKILL_DIR}/scripts/doctruth.py"`; it reads files and runs nothing from the repository.

**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when the answer is a fact about the world. What only the user can decide, ask as one question with 2 to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's `AskUserQuestion` shows them on screen, other agents number them in the reply.

**Next step.** End every run with the next step of the workflow, worked out from what this run left (the ledger's statuses, failed or blocked units, a question still open, the user's goal): the exact command and its reason in one line, and when two fit, both, the recommended one first; a skill that keeps a `STATUS.md` writes the same command as its next action. Put `/clear` before it (on another agent, a new session) when this run left its state on disk for that command to read; keep the session when the next step answers this run in conversation. When another skill called this one, hand the result back to it instead. When nothing is left, say the workflow is done.

## Steps

1. **Scope**: the files in `$ARGUMENTS`, or every tracked Markdown file (`git ls-files '*.md'`) except vendored and generated ones. More than 3 files: scan them all in step 2, then run the `orchestrate` skill when installed (job `doc-truth`, profile `light`, units = files, unit brief = steps 3 and 4 for one file with its findings, each worker may edit its own file and append to its own keep file, concatenated into one before step 5); without it, work the files in sequence.
2. **Scan**: `doctruth.py --json <files>`.
3. **Judge each finding** by reading the doc line and the code it points at:
   - **doc is wrong**: the thing was renamed, moved or removed on purpose (`git log -S<name>` tells you when); fix the doc to what the code does now.
   - **code is wrong**: the doc describes behaviour that was lost by accident; report it, with the commit that dropped it, and leave the code alone. The doc keeps the promise: append the claim to the keep file with reason `regression <commit>`.
   - When the history cannot tell which side changed on purpose, ask with options: fix the doc, report the code, or keep the claim.
   - **fp**: the claim is about the user's project or a path the program creates (`.claude/settings.json`, a state file); append `kind<TAB>claim<TAB>reason` to a keep file in the scratchpad.
4. **Read for what the scanner can't see**: behaviour the doc describes (defaults, output formats, supported versions) checked against the code that implements it, one section at a time.
5. **Rescan** with `--keep <keep file>`: exit 0.
6. **Report**: per file, the fixes made, the code regressions reported, the kept claims with reasons, and the behaviour claims read in step 4.

**Completion.** The rescan exits 0, every W finding was read, and every section of every file in scope was read for behaviour claims.
