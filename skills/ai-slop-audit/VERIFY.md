# verify

Scope: `git diff <baseline>`, where the baseline commit is the one in `checks.md`.

## Steps

1. **Checks.** Run every command in `checks.md`. Each result equals or beats baseline: no new failures, warnings or type errors.
2. **Per fixed finding**: the diff touches only its files plus fallout; removed symbols have zero references; the public surface (package exports, routes, CLI flags, schemas) is unchanged unless the finding said otherwise.
3. **Tests.** Compare test counts with baseline; every removed test has its coverage proof in the ledger.
4. **Dependencies.** The manifest diff shows only removals that findings name, and no additions.
5. **Boundaries.** Every guard at a trust boundary in baseline still exists. Changes on paths the plan marked performance-sensitive run the project's benchmark when one exists, otherwise go to the human as unverified.
6. **Review.** Integrated (SKILL.md's Companions table): run the `code-review` skill with the baseline commit as the fixed point and the batches' issues as the spec, and add its findings as rows. Standalone: steps 1–5 are the review.
7. **Report** a table: item, PASS/FAIL, output excerpt. FAIL items name the finding that caused them.

**Completion.** Every check ran and every `fixed` finding has a verdict. The first line is `VERIFIED` only when all rows PASS; otherwise `FAILED: n items`.
