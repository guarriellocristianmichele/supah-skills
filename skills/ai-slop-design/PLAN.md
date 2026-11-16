# Plan

Group the ledger's open findings into ordered batches that `sweep B<n>`, `craft <surface>` and `publish` can each take on their own. Like the audit, this mode never changes a source file: it writes `.slop-design/plan.md`, the statuses in `findings.md` and `STATUS.md`, nothing else (SKILL.md, Ledger).

1. **Load**: read `STATUS.md`, `inventory.md`, `findings.md` and, on a re-plan, `plan.md`. Without `findings.md` there is nothing to plan: say so and name `/ai-slop-design audit`. When `inventory.md` still has `pending` rows, ask with options: plan the scanned surfaces now (recommended; the plan's header names the pending ones) or resume the audit first. Nothing is read from `.slop-audit/`: the frontend duplication ai-slop-audit marks `handoff:ai-slop-design` is already in this ledger as the design audit's own findings, and this plan owns it.
2. **Freshness**: stale findings are marked before anything is batched.
   - Rescan: `designscan.py --surfaces .slop-design/surfaces.json --out .slop-design/hits.json --keep .slop-design/keep.tsv`, then `designscan.py reconcile .slop-design/findings.md .slop-design/hits.json --keep .slop-design/keep.tsv --write`. The whole inventory goes in one run, so duplication still counts across the platform; files unchanged since their surface's `scanned@<sha>` give the same hits as before, and the reconcile settles the changed ones: a scanner finding whose hit is gone becomes `fixed`, one a keep line now covers `rejected:kept`, a `fixed` or `stale` one whose hit is back `open`. Read only the summary it prints.
   - Judgment, copy and lane findings are `unchecked` by the reconcile (no pattern can tell). For each one whose `Where:` files appear in `git diff --name-only <its Scanned sha>` (a `Scanned: <sha>-dirty` one was read in uncommitted changes, so read it again whatever the diff says), read the finding again in the file as it is now: when it no longer reproduces, set its status to `stale`; when it does, set `Scanned:` to the current commit. The rest stay as they are.
   - New hits the reconcile lists are not judged here: the plan's header counts them as unjudged, for a re-run of `/ai-slop-design audit`, and no batch holds them. Routes and files added since the audit also come in through that re-run; the plan does not rebuild the inventory.
3. **Sort** every `open` finding, and every `planned` one whose batch has no issue, into one kind, testing in this order:
   - **handoff**: a `Hit: lane · <lane>` finding, and every other finding on a surface that has one. The restyle gives the page a new direction and its own sweep fixes what is left, so a patch made first would be undone.
   - **token/component**: a finding of `repeated-class-string`, `duplicate-css-block` or `untokened-colour`, and any finding whose `Fix:` needs one new token or component on more than one surface. They are grouped by what they introduce: one **group** per token set (a palette, a type scale, a radius scale) or per component, named `T1` upward.
   - **surface**: everything else, by its `Surface:` unit (a route, `shared`, or a directory in the fallback): that unit's scanner reflexes, judgment-only finds and copy.

   A finding that fits no batch is rejected with a reason in its status, never left out: its unit is `skipped:<reason>` in `inventory.md` (`rejected:<reason>`), its file is vendored or generated (`rejected:generated`), or the user drops it in step 6 (`rejected:<their reason>`).
4. **Batch**, token/component first, so the surface fixes and restyles already use the new tokens and components:
   - **token/component**, per group, in three steps that keep the platform working batch to batch. One **expand** batch adds the token or component (theme file, `@theme` block, CSS custom properties, the component file) and changes no caller. Then **migrate** batches replace the copies with it, one per set of at most 5 surfaces or 40 frontend files that carry copies (inventory order, `shared` first), each depending on the expand. Last, one **contract** batch removes what the copies leave behind (the old CSS block, the class string nothing uses any more, an alias kept while migrating) and depends on every migrate batch of its group; when nothing is left behind, it is the platform rescan that closes the group. The group's findings are in the contract batch, which closes them; expand and migrate batches name them under `Serves:`.
   - **surface**: one batch per unit with findings, depending on the migrate batches whose files it shares.
   - **handoff**: one batch per lane, holding every surface that sits in it, depending on the migrate batches whose files they share. It is worked with `/ai-slop-design craft <surface>`, one surface after another: the first sets the direction and the next ones reuse it (CRAFT.md, Restyle).

   IDs are `B<n>` in plan order: every token/component batch, then the surface batches (`shared` first, then inventory order), then the handoff batches. They are never reused: a re-plan keeps each batch that has an issue as it is, minus the findings no longer `open` or `planned`, and numbers new batches from the plan's `Next:` line.
5. **Checks**, written on every batch, the ones its issue and its sweep run:
   - **rescan**: for surface, handoff and expand batches, `designscan.py --keep .slop-design/keep.tsv <files>` exits 0. A migrate or contract batch's files can still hold later batches' findings, so for those the platform rescan and `designscan.py reconcile .slop-design/findings.md .slop-design/hits.json --keep .slop-design/keep.tsv --json` show no copy of the group left in the batch's files (migrate) or the group's findings `fixed` (contract).
   - **content**: every visible string, link, form field, handler and accessible name in the batch's files is unchanged against a snapshot taken before the batch.
   - **render**: where the user allows a browser, no horizontal scroll (`document.documentElement.scrollWidth` not above `clientWidth`) at 390, 768 and 1440 pixels on each of the batch's surfaces; without one, the batch is reported as render not checked.
6. **Write** `plan.md` in the format below, set every batched finding to `planned`, rewrite `STATUS.md` (finding counts, next action `/ai-slop-design publish` or `/ai-slop-design sweep B1`), and show the batches in order: ID, kind, title, files, findings, depends-on. Ask with options: keep the plan (recommended), drop findings by ID with a reason (they become `rejected:<reason>` and the plan is rewritten), or split a batch named by ID.

**Completion.** Every finding that was `open` after step 2 is in the `Findings:` of exactly one batch or `rejected:<reason>`; every token/component group has one expand batch, at least one migrate batch depending on it and one contract batch depending on every migrate batch; every handoff batch names its lane and surfaces; every batch has files, checks and a `Work:` line; and no source file changed (`git status --short` shows what it showed before the run).

## plan.md

The batch format is the contract with `sweep B<n>`, `craft <surface>` and `publish`: one `## B<n>` block per batch, then one `Key: value` field per line, in this order, lists comma-separated, `none` when empty.

```markdown
# Design plan @a3f8d70

Coverage: COMPLETE 12/12 surfaces
Findings: 41 planned, 2 rejected, 3 stale; 0 unjudged new hits
Next: B9

## B1 · token/component:expand · `--color-brand` for `#6d28d9`
Group: T1 · token `--color-brand` replaces `#6d28d9`
Surfaces: shared
Files: app/globals.css
Findings: none
Serves: DS-004
Depends-on: none
Change: add `--color-brand: #6d28d9` to the `@theme` block; no caller changes.
Checks:
- rescan: `designscan.py --keep .slop-design/keep.tsv app/globals.css` exits 0
- content: app/globals.css keeps every rule it had
- render: none, no caller changes
Work: /ai-slop-design sweep B1
Status: planned
Issue: none

## B7 · handoff · cream and clay on /about, /team
Lane: Cream ground, high-contrast serif display, terracotta or clay accent.
Surfaces: /about, /team
Files: app/about/page.tsx, app/team/page.tsx, components/about/Hero.tsx
Findings: DS-021, DS-022, DS-030
Depends-on: B3
Change: a new direction for both pages, away from the lane; DS-021 and DS-022 are fixed by the restyle's sweep.
Checks:
- rescan: `designscan.py --keep .slop-design/keep.tsv <the files above>` exits 0
- content: the restyle's inventory of strings, links, fields, handlers and accessible names matches
- render: no horizontal scroll at 390, 768 and 1440 on /about and /team
Work: /ai-slop-design craft /about, then /ai-slop-design craft /team
Status: planned
Issue: none
```

- **Heading**: `## B<n> · <kind> · <title>`. `<kind>` is one of `token/component:expand`, `token/component:migrate`, `token/component:contract`, `surface` or `handoff`.
- **Group** and **Serves**: token/component batches only. `Serves:` lists the group's findings that the expand or migrate step works toward; on the contract batch they are in `Findings:` and `Serves:` is `none`.
- **Lane**: handoff batches only, the lane as REFLEXES.md names it.
- **Surfaces**: the units the batch touches. **Files**: the files it may edit; for a surface or token/component batch, the files its findings and the group's copies name, for a handoff batch every file of its surfaces in `surfaces.json`.
- **Findings**: the IDs this batch closes; every planned finding is in exactly one batch.
- **Depends-on**: the batch IDs that must be `done` first.
- **Change**: one paragraph of what the batch changes and what stays.
- **Checks**: the three lines of step 5, with the batch's own files and surfaces.
- **Work**: the command that works the batch: `/ai-slop-design sweep B<n>`, or `craft <surface>` for each surface of a handoff, in order.
- **Status**: `planned` until the batch is worked; `done` once every ID in `Findings:` is `fixed`, `stale` or `rejected:<reason>`, and for an expand or migrate batch once its checks pass.
- **Issue**: `none` until publish writes `#<n>` or the local file path.
