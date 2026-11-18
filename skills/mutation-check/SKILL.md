---
name: mutation-check
description: Prove whether tests catch behaviour changes by mutating the code and running them. Use for test-quality evidence, a suspected tautological test, or before trusting a suite to protect a refactor.
argument-hint: "<file> [--function NAME | --lines A-B] [test command]"
allowed-tools: Bash(git status *)
---

# Mutation check

A **mutant** is the code with one small change (`<` to `<=`, `and` to `or`, a return value dropped, a call removed). Tests that still pass on a mutant do not check that behaviour. The job: for the code in scope, every mutant run, and every **survivor** given a verdict.

Claude Code fills in `${CLAUDE_SKILL_DIR}` (this skill's folder) and `$ARGUMENTS` (what the user typed after the skill name); elsewhere, resolve them yourself. The script is `python "${CLAUDE_SKILL_DIR}/scripts/mutate.py"`.

**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when the answer is a fact about the world. What only the user can decide, ask as one question with 2 to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's `AskUserQuestion` shows them on screen, other agents number them in the reply.

**Next step.** End every run with the next step of the workflow, worked out from what this run left (the ledger's statuses, failed or blocked units, a question still open, the user's goal): the exact command and its reason in one line, and when two fit, both, the recommended one first; a skill that keeps a `STATUS.md` writes the same command as its next action. Put `/clear` before it (on another agent, a new session) when this run left its state on disk for that command to read; keep the session when the next step answers this run in conversation. When another skill called this one, hand the result back to it instead. When nothing is left, say the workflow is done.

**Lessons.** At the start of a run, read this skill's section of `.supah/LESSONS.md` at the repo root when it exists, and follow its rules. Write a lesson only when the user corrects or undoes what this skill did, or when a run ends failed or partial for a cause the skill could have avoided: one entry under `## <skill>` (on first use create the file and add `.supah/` to `.git/info/exclude`) with the date, the trigger (`correction` or `failure`), the evidence (the user's words, the commit or the output), the step it changes, and the rule in one positive line. Keep at most 15 per skill: a lesson that contradicts an older one replaces it, and past 15 the oldest goes. A lesson about this skill's own instructions, true in any project, changes nothing here: draft an issue for guarriellocristianmichele/supah-skills (title, the SKILL.md step, what happened, no code or text from the project) and ask with options: open it with `gh issue create`, save it in `.supah/issue-drafts/`, or drop it. The report names the lessons added, replaced and drafted.

## Steps

1. **Scope**: the file, and a function or line range when the file is large; `mutate.py list <file> [--function NAME]` shows the mutants. More than 60 is a sign to narrow the scope. `--function` works on Python only: for JavaScript and TypeScript, give the function's lines with `--lines A-B`.
2. **Test command**: the narrowest one that exercises the scope (`pytest tests/test_auth.py`, `npm test -- auth`), from the project's own scripts. To judge one test file, give that file alone.
3. **Clean file**: `run` refuses a file with uncommitted changes. Ask with options: stash them (`git stash push -- <file>`, recommended: popped after the run) or commit them first.
4. **Run**: `mutate.py run <file> --test "<command>" [--function NAME] --json`. It executes the test command through the shell, so it is not pre-approved: the user sees and confirms the exact command. The file is changed in place and restored after each mutant. Exit codes: 0 no survivor, 1 survivors, 2 refused (bad arguments, uncommitted file), 3 the tests fail on the original file (fix that before any mutant can say anything), 128 + the signal number when interrupted. A run killed outright (closed terminal, task kill) can leave a mutant in the file: the next `run` puts the original back, and so does `mutate.py restore <file>`, which you run before popping a stash from step 3.
5. **Judge every survivor**, reading the mutated line in context. A `timeout` counts as killed (the mutant hung the tests, and the script killed them with every process they started); list it apart.
   - **equivalent**: the mutant behaves the same for every input (`x < lo` to `x <= lo` when both branches return the same value at `x == lo`). Not a gap.
   - **gap**: an input exists where behaviour differs and no test uses it. Name that input.
6. **Report**: score, survivors with verdicts and the missing inputs, and, when one test file killed nothing, that the file is tautological for this code: it asserts what a mock returns, a constant, or nothing.

**Completion.** Every mutant has a status, every survivor has a verdict with its reason, and the file is as the user left it: after an interrupted run `mutate.py restore <file>` has run, a stash from step 3 is popped, and `git status` shows the same changes as before the run.

For `ai-slop-audit`, a `tautological-test` finding's evidence is the run with that test file alone: zero killed mutants of the code it claims to test.
