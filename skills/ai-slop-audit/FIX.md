# fix

The IDs in the arguments are the approval: finding IDs (`SLOP-012`, `SLOP-012,SLOP-014`), one batch (`B3`), or a published batch's issue (`#123`, resolved through `plan.md`). Change exactly what they name.

## Steps

1. **Preconditions.** Every ID exists and is `planned`; the working tree is clean; `checks.md` holds a baseline. A batch whose issue is already closed (built elsewhere, for example by `/implement`) is synced to `fixed` instead of changed. Any miss: stop and say which.
2. **Re-prove.** Re-run each finding's evidence at current HEAD. Not reproducible: mark `stale`, stop.
3. **Protect.** Run the batch's protecting checks: green. When the plan calls for a characterization test, write it and see it pass on unchanged code.
4. **Change** the lines the findings name, plus their **fallout**: imports, types and exports that became unused through this change. Anything else you notice becomes a new `open` finding in the ledger.
5. **Verify.** Re-run the checks: no result worse than baseline. Re-search removed symbols: zero references. Dependency removals go through the project's package manager so the lockfile stays consistent.
6. **Report** `git diff --stat` and the diff, then set each finding `fixed` with a one-line summary. A batch with an issue ends with the line `Closes #<n>` for the pull request.

Verification red because of the change: restore the files this batch touched (`git restore -- <files>`, safe since the tree was clean), set the finding back to `open` with the failure output, and report.

## Guardrails

- New dependencies are out of scope. A fix that needs one goes back to `open` with the reason.
- A test is deleted or merged only with proof its behaviour stays asserted: the name and assertion of the test that covers it, or, where the project measures coverage, before/after numbers for the production code it exercised.
