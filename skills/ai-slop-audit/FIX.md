# fix

The IDs in the arguments are the approval: finding IDs (`SLOP-012`, `SLOP-012,SLOP-014`), one batch (`B3`), or a published batch's issue (`#123`, resolved through `plan.md`). Change exactly what they name. Several batches (`B2 B5`, the map issue `#<map>`, or `all`) run as one job: see Several batches.

## Steps

1. **Preconditions.** Every ID exists and is `planned`; the working tree is clean; `checks.md` holds a baseline; every batch in its `depends-on` is `fixed`, or ask with options (fix that batch first, recommended, or go ahead, naming the lines both touch). A batch whose issue is already closed (built elsewhere, for example by `/implement`) is synced to `fixed` instead of changed. Any miss: stop and say which.
2. **Re-prove.** Re-run each finding's evidence at current HEAD. Not reproducible: mark `stale`, stop.
3. **Protect.** Run the batch's protecting checks: green. When the plan calls for a characterization test, write it and see it pass on unchanged code.
4. **Change** the lines the findings name, plus their **fallout**: imports, types and exports that became unused through this change. Anything else you notice becomes a new `open` finding in the ledger.
5. **Verify.** Re-run the checks: no result worse than baseline. A scanner hit the change uncovers that an existing `planned` finding already names is not worse; any other new hit is. Re-search removed symbols: zero references. Dependency removals go through the project's package manager so the lockfile stays consistent.
6. **Report** `git diff --stat` and the diff, then set each finding `fixed` with a one-line summary, and end with the commit to make: the next `fix` needs a clean tree. A batch with an issue ends with the line `Closes #<n>` for the pull request.

Verification red because of the change: restore the files this batch touched (`git restore -- <files>`, safe since the tree was clean), set the finding back to `open` with the failure output, and report.

## Guardrails

- New dependencies are out of scope. A fix that needs one goes back to `open` with the reason.
- A test is deleted or merged only with proof its behaviour stays asserted: the name and assertion of the test that covers it, or, where the project measures coverage, before/after numbers for the production code it exercised.

## Several batches

`fix B2 B5`, `fix #<map>` (every batch of the map issue, resolved through `plan.md`) or `fix all` (every `planned` batch) works the batches in parallel, each one in its own worktree, merged into one integration branch in the order their `depends-on` sets. One batch named this way runs the Steps above.

1. **Preconditions**, once for the run: step 1's checks for every batch, except that a batch's `depends-on` may also be a batch of this run. A blocker outside the run and not `fixed`: ask with options: add it to the run (recommended) or drop the batches that need it. A batch whose issue is closed is synced to `fixed` and leaves the run.
2. **Job** through the `orchestrate` skill, as a graph job: job `audit-fix`, state dir `.slop-audit/`, profile `build`, units = the batches in plan order, each with `blocked-by` = its `depends-on` inside the run and `files` = its files. Integration branch: the one `.slop-audit/orchestrator/audit-fix/state.json` names, else `slop/audit-<HEAD>`. Setup: the install the baseline in `checks.md` ran on, from the lockfile. After each merge: the batch's protecting checks. Unit brief: steps 2 to 5 for that batch, reading `.slop-audit/` at the main checkout's absolute path, then one commit `<B> · <batch title>` whose body lists the finding IDs and `Refs #<n>` when the batch has an issue; the reply gives each finding's result (`fixed` with its one-line summary, or `open` with the failure output) and every new finding noticed. A red step 5 restores the files and ends the unit without a commit. Record step, yours, after each merge or failure: write those results into `findings.md`, giving new findings the next IDs.
   Without orchestrate: work the batches yourself in plan order, a batch only after its blockers are `fixed`, each committed on the integration branch.
3. **Verify** on the integration branch, in its worktree: VERIFY.md against the baseline commit in `checks.md`. Its failures become `open` findings; none is fixed in this run.
4. **Report** each batch `done`, `failed:<reason>` (its findings back to `open`) or `blocked by B<n>`, the `verify` table and the integration branch. On GitHub, ask with options: open one pull request from the integration branch (recommended: push it, then `gh pr create`, the body carrying `Closes #<n>` for every done batch with an issue, and `Closes #<map>` when every batch of the map is done, else `Part of #<map>`), or leave the branch for the user. Integrated: close the work the way `docs/agents/issue-tracker.md` says. Local issues: report the branch only. Write the branch in `STATUS.md`; running the same command again resumes the job.

**Completion.** Every batch of the run is `done`, `failed:<reason>` or `blocked by B<n>`; every done batch's findings are `fixed` in `findings.md` and its commit is on the integration branch; `verify` ran there; and the user's checkout is still on the branch it started on.
