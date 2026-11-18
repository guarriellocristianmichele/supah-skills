# Publish

Turn the batches in `.slop-design/plan.md` into issues, one per batch plus one map issue, so the cleanup can be split, assigned and worked over time by a person, by `sweep B<n>` and `craft <surface>`, or by any agent. Arguments: batch IDs (`B2 B5`); by default every batch with `Status: planned` and `Issue: none`. This mode never changes a source file: it writes the tracker (or `.slop-design/issues/`), and in the ledger only `plan.md`, the statuses in `findings.md` and `STATUS.md`.

The ledger stays in this clone, so each issue carries what is needed to do the work without it: the files, the findings with their evidence, the keep lines and the checks.

## Steps

1. **Load**: read `STATUS.md`, `plan.md` and `findings.md`. Without `plan.md` there is nothing to publish: say so and name `/ai-slop-design plan`. A batch ID not in `plan.md` is named back to the user and left out. A finding of a selected batch with `Scanned: <sha>-dirty` was read in uncommitted changes, so no commit holds its evidence: list those findings and ask with options: commit them and run `/ai-slop-design audit` again (recommended), which pins them to the new commit, or publish now with their locations as `path:line` marked uncommitted.
2. **Route**, one for the whole run:
   - **integrated**, when `docs/agents/issue-tracker.md` exists (the mattpocock skills' setup writes it): follow it for every tracker operation, including its check of the target repo, and take label names from `docs/agents/triage-labels.md`. Read both; never write them or anything else under `docs/agents/`.
   - **GitHub**, when `origin` is on GitHub and `gh auth status` passes: confirm the target with `gh repo view --json nameWithOwner`.
   - **local files** otherwise: each batch goes to `.slop-design/issues/<B>.md` (`.slop-design/issues/B4.md`) and the map to `.slop-design/issues/map.md`, each path standing for an issue number (Local issues, below).
3. **Sync**, before drafting anything: for each batch whose `Issue:` names an issue, read its state (on GitHub, `gh issue view <n> --json state,stateReason,labels`). Closed as completed: every ID in its `Findings:` becomes `fixed` in `findings.md` and the batch `Status: done`. Closed as not planned, or carrying the tracker's `wontfix` label: every ID in its `Findings:` becomes `rejected:wontfix (#<n>)` and the batch `Status: done`. Open issues whose findings the ledger already has `fixed` (a sweep closed them) are listed for the user to close. On the local route the file's `State:` line is the state (Local issues, below). Report each change as `DS-x planned -> fixed (#<n>)`.
4. **Draft** one issue per selected batch with the template below, and the map issue when `STATUS.md` names none. Titles: `<B> · <kind> · <batch title>` for a batch, `AI slop design @<sha of plan.md's header>` for the map. Labels on the integrated route only: the tracker's `ready-for-agent` only for a token/component or surface batch whose findings are all reflex verdicts from the scanner, each with a fix direction; its `needs-triage` for every other batch: a handoff batch, which needs a direction chosen, and a batch holding a judgment, copy or lane finding, or a finding with `Scanned: <sha>-dirty`, which someone checks first. The GitHub and local routes apply no labels.
5. **Approve**: nothing reaches the tracker, and no file is written in `.slop-design/issues/`, before the user approves. Show the numbered drafts: title, route, labels, the map it joins and what it is blocked by, with the full body of one draft per kind. Ask with options: publish all (recommended), publish some by number, or change a draft; iterate on the changes until the user approves.
6. **Publish** the map first, then the batches in plan order, which puts every batch after the ones it depends on.
   - Before each create, search for the issue's marker among open and closed issues (`gh issue list --state all --search "\"ai-slop-design batch B4\" in:body"` on GitHub; the integrated route's own search; on the local route, the file `.slop-design/issues/B4.md`). Confirm the marker line in the result's body matches the batch ID exactly, then reuse the match: update its body and labels instead of creating a second issue. Only when nothing matches, create one.
   - Link each batch to the map: as a sub-issue where the tracker has them, else `Part of #<map>` as the body's first line. Record each `Depends-on:` batch as a blocking link where the tracker has them, else as a `Blocked by: #<n>` line under it.
   - After the last batch, rewrite the map's batch list with the issue numbers (or file paths).
7. **Record**: `Issue: #<n>` (or the local path) on each published batch in `plan.md`; the map's number or path and the next action in `STATUS.md`: `/ai-slop-design sweep #<map>` (on the local route `/ai-slop-design sweep .slop-design/issues/map.md`) when more than one published batch qualifies for it (SWEEP.md, Several batches), else `/ai-slop-design sweep B<n>` for the first batch with no open blocker. Then report what was created, what was reused and what the sync changed. When the mattpocock skills are installed (`docs/agents/issue-tracker.md` exists or `/to-tickets` is among the skills the session lists), add to the report: `/to-tickets` can split a token/component group's issues further, and `/to-spec` can turn a handoff batch over more than one surface into a spec. Name them only: they are user-invoked, this skill never runs them, and their formats and reserved paths (`docs/agents/`, `.scratch/`, `.out-of-scope/`) stay theirs.

**Completion.** Every selected batch has exactly one issue, which its marker finds; every `Depends-on:` edge is recorded on the issue that depends; the map lists every published batch; `plan.md` names each batch's issue and `STATUS.md` the map's; and no source file changed (`git status --short` shows what it showed before the run).

## Local issues

Without a tracker, each issue is a file in `.slop-design/issues/`, and its path stands wherever this skill writes or reads an issue number:

| On a tracker | On the local route |
|---|---|
| a batch's issue `#<n>` | `.slop-design/issues/B<n>.md` (`Issue: .slop-design/issues/B3.md` in `plan.md`) |
| the map issue `#<map>` | `.slop-design/issues/map.md`, named in `STATUS.md` |
| `Part of #<map>`, `Blocked by: #<n>` | `Part of .slop-design/issues/map.md`, `Blocked by: .slop-design/issues/B2.md` |
| `sweep #<n>`, `sweep #<map>` | `sweep B3`, `sweep .slop-design/issues/map.md` |
| the marker search before a create | the file exists: rewrite its body and keep its `State:` line |
| a permalink | `<path>:<start>-<end> @ <sha>`, the scanned commit |
| open or closed, read by the sync | the file's first line: `State: open` when published; `State: done` (closed as completed) or `State: wontfix` (closed as not planned), set by whoever closes it |
| `Closes #<n>` in the pull request | `sweep B<n>` and `craft <surface>` set the file's first line to `State: done` when they set the batch's `Status: done` |
| `Refs #<n>` in a commit body | nothing: the commit title already names the batch, and the ledger is untracked, so no commit names its path |

The sync reads `State: done` as `fixed` and `State: wontfix` as `rejected:wontfix (.slop-design/issues/B3.md)`.

## Issue template

The body names the files, the findings and the checks. Every location sits in the evidence block as a permalink pinned to the finding's `Scanned:` commit (`https://github.com/<owner>/<repo>/blob/<sha>/<path>#L12`), which stays valid while the code moves; on the local route, `<path>:<start>-<end> @ <sha>`. A local issue file starts with its `State:` line and uses the local forms (Local issues, above). A `Scanned: <sha>-dirty` finding gets no permalink: its location is `path:line (uncommitted at <sha>)`, because that commit does not hold what was read. When the line names files in parentheses (`Scanned: <sha>-dirty (<file>, …)`, a duplication group), only those files are uncommitted; the group's other files get their permalinks.

```markdown
Part of #<map>
Blocked by: #<issue of each Depends-on batch>

> Drafted by ai-slop-design from plan.md; evidence pinned to <sha>.

## Change

<the batch's Change: paragraph; for a handoff, the lane the surfaces sit in and that the new direction must leave it>

## Work it

With this repo's `.slop-design/` ledger: `<the batch's Work: line>`. Without it: fix the findings below in the files listed, with the keep lines below as the keep file, then run the checks.

Files: <the batch's Files:>

## Done when

- [ ] <per finding: DS-x, its hit gone or its judgment no longer true, e.g. no `bg-gradient-to-r from-violet-600 to-indigo-600` left in app/pricing/page.tsx>
- [ ] rescan: <the batch's rescan check>
- [ ] content: <the batch's content check>
- [ ] render: <the batch's render check>

## Not part of this

Findings outside <the batch's Findings:, or the group it serves>, and files outside the list above. New reflexes go to the next `/ai-slop-design audit`, not into this issue.

<details><summary>Evidence</summary>

<each finding block from findings.md, its Where: as permalinks>

Keep lines for this batch's kept hits (`rule<TAB>match<TAB>reason`):

<the keep.tsv lines whose hits are in these files>

</details>

<!-- ai-slop-design batch <B> · <finding IDs, or the group's for expand and migrate> -->
```

The map issue holds plan.md's header lines (coverage, finding counts), then one line per batch in plan order, `- [ ] #<n> <B> · <kind> · <title>` with `(blocked by #<n>, …)` when it has blockers, and ends with `<!-- ai-slop-design map -->`, the marker a re-run finds it by.
