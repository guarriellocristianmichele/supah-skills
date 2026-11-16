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

## Steps

1. **Scope**: the file, and a function or line range when the file is large; `mutate.py list <file> [--function NAME]` shows the mutants. More than 60 is a sign to narrow the scope.
2. **Test command**: the narrowest one that exercises the scope (`pytest tests/test_auth.py`, `npm test -- auth`), from the project's own scripts. To judge one test file, give that file alone.
3. **Clean file**: `run` refuses a file with uncommitted changes. Ask with options: stash them (`git stash push -- <file>`, recommended: popped after the run) or commit them first.
4. **Run**: `mutate.py run <file> --test "<command>" [--function NAME] --json`. It executes the test command through the shell, so it is not pre-approved: the user sees and confirms the exact command. The file is changed in place and restored after each mutant.
5. **Judge every survivor**, reading the mutated line in context. A `timeout` counts as killed (the mutant hung the tests); list it apart.
   - **equivalent**: the mutant behaves the same for every input (`x < lo` to `x <= lo` when both branches return the same value at `x == lo`). Not a gap.
   - **gap**: an input exists where behaviour differs and no test uses it. Name that input.
6. **Report**: score, survivors with verdicts and the missing inputs, and, when one test file killed nothing, that the file is tautological for this code: it asserts what a mock returns, a constant, or nothing.

**Completion.** Every mutant has a status, every survivor has a verdict with its reason, and the file is as the user left it: a stash from step 3 is popped, and `git status` shows the same changes as before the run.

For `ai-slop-audit`, a `tautological-test` finding's evidence is the run with that test file alone: zero killed mutants of the code it claims to test.
