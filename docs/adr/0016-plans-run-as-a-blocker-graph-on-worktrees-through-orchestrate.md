# Plans run as a blocker graph on worktrees through orchestrate

A plan's batches were worked one command at a time (`fix B3`, `sweep B4`), each on the user's checkout, which took as long as the plan was wide. Several batches now run as one job: `fix B2 B5 | #<map> | all` and `sweep B2 B5 | #<map> | all` hand them to orchestrate as a **graph job**. Each batch declares its **blockers** (the plan's `depends-on`); orchestrate starts only the **frontier**, runs each batch in its own git worktree branched from the **integration branch** tip, merges it there with `--no-ff`, runs the batch's checks on the merged tip, and only then lets its dependents start. Two batches that share a file and no blocker chain run one after the other, the earlier in plan order first. The graph rules (frontier, implied order, blocked dependents, cycles) live in `skills/orchestrate/scripts/graph.py`, so they are computed the same way every run and tested.

This changes what a unit is: it may now need the merged output of its blockers, and of no other unit (GLOSSARY.md).

## Considered options

- **A new skill like mattpocock's `implement-spec`**, reading both ledgers: rejected. It would add a skill and an edge into two user-invoked skills, and it would have to repeat each one's preconditions, checks and ledger rules, which belong to the skill that owns the ledger.
- **All of it inside orchestrate**: rejected; orchestrate is the domain-free engine of ADR 0012, and the batch preconditions, checks and ledger writes stay with ai-slop-audit and ai-slop-design. orchestrate learns only blockers, worktrees and the merge loop.
- **Waves** (start the next set of batches when the whole current set is done): rejected. One slow batch would hold every ready batch back; the frontier is recomputed after every merge instead.
- **Workers that skip installs and leave the tests to the integration branch**: rejected. It is faster, but a batch would merge before its own checks ran, which `fix` has always required. Each worktree runs the install the baseline ran on, and the `build` profile sizes workers to that cost.

## Consequences

- Only the coordinator writes the ledger, after each merge and each failure. Workers read it by the main checkout's absolute path, since `.slop-audit/` and `.slop-design/` are excluded from git and absent from a worktree.
- A batch worker runs every fan-out inside its batch inline: the parallelism is between batches, never nested.
- A batch whose own checks fail is `failed`, and its declared dependents, direct and transitive, are `blocked`; a batch it only shares files with goes ahead. A merge conflict or red checks after the merge earn one retry from the new tip.
- Handoff batches, and design batches holding a judgment, copy, lane or dirty finding, stay out of the job, and so do the batches that depend on them: they need a person's choice first.
- The job ends with the skill's verify step on the integration branch and asks before opening one pull request that closes the done batches' issues; nothing else is written to the tracker, except on the local route, where each done batch's issue file gets `State: done` in place of `Closes #<n>`.
