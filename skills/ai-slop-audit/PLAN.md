# plan

## Steps

1. **Load** `open` findings. `low` confidence goes to a "needs evidence" list, outside the batches.
2. **Re-check freshness.** For findings in files changed since their module's `scanned@<sha>` (`git diff --stat <sha>`), re-run the evidence; mark `stale` what no longer reproduces.
3. **Checks.** Discover the project's test, lint, typecheck and build commands from its manifests, task runner and CI config. Run them and record each command and its baseline result in `checks.md`, with the baseline commit. A red baseline check cannot protect a fix; note which.
4. **Score** each finding: value (complexity removed) × confidence, against risk. Risk rises with public API, reach that only shows at runtime, an area no test exercises, security- or performance-sensitive paths.
5. **Order.** Record dependencies: findings sharing files, or one fix that enables or obsoletes another (remove the wrapper before its now-dead helper).
6. **Batch.** Group into small batches, each one category in one area, independently revertible. Each batch lists: IDs, files, protecting checks, risk, depends-on, and the **characterization test** to write first when no existing test covers the behaviour.
7. Write `plan.md`, set batched findings to `planned`, and show the batches in order.

**Completion.** Every `open` high/medium finding is in a batch, or `rejected` with a reason; every batch has at least one protecting check or a characterization test.
