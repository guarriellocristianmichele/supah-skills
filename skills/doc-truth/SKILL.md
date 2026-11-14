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

## Steps

1. **Scope**: the files in `$ARGUMENTS`, or every tracked Markdown file (`git ls-files '*.md'`) except vendored and generated ones.
2. **Scan**: `doctruth.py --json <files>`.
3. **Judge each finding** by reading the doc line and the code it points at:
   - **doc is wrong**: the thing was renamed, moved or removed on purpose (`git log -S<name>` tells you when); fix the doc to what the code does now.
   - **code is wrong**: the doc describes behaviour that was lost by accident; report it, with the commit that dropped it, and leave the code alone.
   - **fp**: the claim is about the user's project or a path the program creates (`.claude/settings.json`, a state file); append `kind<TAB>claim<TAB>reason` to a keep file in the scratchpad.
4. **Read for what the scanner can't see**: behaviour the doc describes (defaults, output formats, supported versions) checked against the code that implements it, one section at a time.
5. **Rescan** with `--keep <keep file>`: exit 0.
6. **Report**: per file, the fixes made, the code regressions reported, the kept claims with reasons, and the behaviour claims read in step 4.

**Completion.** The rescan exits 0, every W finding was read, and every section of every file in scope was read for behaviour claims.
