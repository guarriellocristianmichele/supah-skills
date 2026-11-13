# publish

Turns planned batches into issues, one per batch, so the cleanup can be worked from the tracker by a human, by this skill's `fix #<n>`, or by any agent. Arguments: batch IDs (`B1 B4`), default every `planned` batch without an issue. The route (integrated or standalone) is the one in SKILL.md's Companions table.

The ledger is local to this clone, so each issue carries everything needed to do the work without it.

## Steps

1. **Route.** Integrated: follow `docs/agents/issue-tracker.md` for every operation, including its target-repo check. Standalone on GitHub: confirm the target with `gh repo view --json nameWithOwner`. Standalone without GitHub: write `.slop-audit/issues/<batch>.md`.
2. **Sync.** For batches already carrying an issue, read its state: closed as completed → findings `fixed`; closed as not planned, or carrying the tracker's `wontfix` label → `rejected:wontfix (#<n>)`. Report the changes.
3. **Draft** one issue per selected batch with the template below, plus one **map** issue per audit (`AI slop audit @<sha>`: coverage line, finding counts, batch list) when none exists. Labels, integrated only: the tracker's `ready-for-agent` when every finding is `high` and the batch has a protecting check, else its `needs-triage`; standalone applies no labels.
4. **Approve.** Show the numbered drafts: title, labels, blocked by. Iterate until the user approves.
5. **Publish** the map first, then batches with blockers first. Link each batch to the map (sub-issue where the tracker has them, else `Part of #<map>` as the first line) and record `depends-on` as blocking links where the tracker has them, else as a `Blocked by: #<n>` line. Before each create, search for the batch's marker and reuse a match.
6. **Record** `issue: #<n>` (or the local file path) on each batch in `plan.md`, and the map in `STATUS.md`.

**Completion.** Every selected batch has exactly one issue (its marker matches one result), every `depends-on` edge is recorded on it, and `plan.md` names each one.

## Issue template

Name symbols and behaviour in the body; put file locations only in the evidence block, as permalinks pinned to the scanned commit (`https://github.com/<owner>/<repo>/blob/<sha>/<path>#L40-L58`), which stay valid as the code moves.

```markdown
> Drafted by ai-slop-audit; evidence pinned to <sha>.

## Change

<one paragraph: which symbols go or merge, and why the behaviour stays the same>

## Done when

- [ ] <per finding, e.g. no reference to `getJson` remains>
- [ ] <each check command> is no worse than at <sha> (<baseline result>)
- [ ] no dependency added; each removed test names the test that still covers its behaviour
- [ ] guards at trust boundaries unchanged

## Not part of this

Anything beyond findings <IDs>. New findings go to a new issue.

<details><summary>Evidence</summary>

<finding blocks, locations as permalinks>

</details>

<!-- ai-slop-audit: <batch ID> <finding IDs> -->
```
