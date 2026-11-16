# ai-slop-design audits a whole platform by surface into a ledger, plans batches and publishes them, and only sweep edits

`sweep` works for a set of files someone means to fix. Pointed at a platform with dozens of routes and hundreds of components it breaks: every hit's JSON lands in the main agent's context, workers edit files before anyone has seen the whole platform, the judgment-only read and the screenshots happen in one context a platform does not fit in, verdicts live in a scratchpad and do not survive the session, and nothing turns findings into work a team can split. ai-slop-audit already has the shape that fixes this for code (ledger, inventory, audit, plan, publish), and it already reads this scanner's duplication hits, so both audits would report the same duplication.

The decisions, from a grilling session on 2026-11-16 (issue #15):

- **Three modes in ai-slop-design**, each in its own mode file next to CRAFT.md and SWEEP.md: `audit [path]` (read-only), `plan` and `publish [batches]`. ai-slop-design still never calls ai-slop-audit.
- **The unit is the surface**: a route or page plus the components only it reaches, so each hit is judged in the context of the page it renders on. Components reached by several surfaces form one `shared` unit, judged once, and every frontend file belongs to exactly one unit, so coverage `k/N surfaces` means what it says. Files no static read can place (auto-imported components, config) go to `shared` as `unreached` rather than out of the count.
- **Surfaces come from framework conventions** (Next.js, Nuxt, SvelteKit, Astro, react-router), read from `package.json`, with units by directory when no convention matches; a unit above 40 files splits by directory so one worker context holds it.
- **The scanner is the one code seam**: `surfaces` writes the inventory, `--surfaces … --out` scans every file in one run (duplication counts across the platform) and writes the hits grouped by unit to the ledger, printing only a summary, and `hits <file> <unit>` gives a worker its own unit without the duplication hits. Standard library only, no rule changes, so no recalibration.
- **Fan-out through orchestrate**: job `design-audit`, profile `light`, units = surfaces plus `shared`, state dir `.slop-design/`; workers write only their work file, inline when orchestrate is missing. Duplication stays with the main agent as a summary.
- **The ledger is `.slop-design/`**: `STATUS.md`, the inventory with `pending` / `scanned@<sha>` / `skipped:<reason>`, the hits file, `findings.md`, a persistent `keep.tsv`, `plan.md` and, without a tracker, `issues/`. Same roles as ai-slop-audit's ledger; the formats are this skill's own, because per-skill installs cannot share files (ADR 0008).
- **The audit judges; sweep reuses the verdicts** from the persistent keep file. `designscan.py verdict` (the calibration log) runs only in sweep, because it needs a before and an after.
- **Screenshots on a sample**: the browser question is asked once, as today; the sample is one surface per category plus the five with the most hits, and the rest are reported as render not checked.
- **Copy read-only**: the audit runs ai-slop-prose's scanner in JSON mode only; rewrites stay with sweep's hand-off.
- **Frontend duplication belongs to the design audit**: ai-slop-audit marks `repeated-class-string`, `duplicate-css-block` and `untokened-colour` `handoff:ai-slop-design` when `.slop-design/findings.md` exists, a one-way edge in ADR 0012's call graph.
- **Three kinds of batch**, planned in this order: token/component (sequenced expand → migrate per group of surfaces → contract), surface, handoff; each lists files, findings, depends-on and checks.
- **Publish follows ai-slop-audit's publish**: integrated tracker, `gh` or local files; numbered drafts approved with options; a map issue; a marker per batch. With the mattpocock skills installed the report names `/to-tickets` and `/to-spec`, which stay user-invoked; their formats and reserved paths stay theirs (ADR 0005).
- **Only sweep edits**: it takes a batch (`sweep B<n>`), marks its findings `fixed` and never writes the tracker; a plain sweep above 5 surfaces or 40 frontend files asks first whether to audit. Craft gains `craft <surface>`, a restyle away from the named lane.
- **No `verify` mode**: re-running `audit` reconciles the ledger against a fresh scan.

## Considered options

- Running ai-slop-audit's audit over the frontend: rejected; its categories are about reach and removal, not reflexes, and it would need this skill's catalogue, category frames and browser checks anyway.
- One unit per file, as sweep does: rejected; a hit is judged against the page it renders on, and a platform has too many files for one checkpoint each to stay cheap.
- Putting every component in the surfaces that import it: rejected; a shared button would be judged and counted once per route.
- Screenshots of every surface: rejected; three widths per route does not fit a session on a platform, and a sample with an honest "render not checked" list claims no more than was checked.
- A separate `verify` mode: rejected; a re-run audit already compares a fresh scan with the ledger.

## Consequences

- AUDIT.md (and later PLAN.md and PUBLISH.md) are model-run prose; the deterministic parts live in the scanner and are tested through its CLI with three mini-platforms in `tests/fixtures/design/platforms/`.
- The inventory's import reading is static: aliases beyond `@/`, `~/`, `~~/`, `@@/` and `$lib/` are not resolved, and the files they reach land in `shared`. That costs precision on placement, never coverage.
- The reconcile (`designscan.py reconcile`) matches a finding to the fresh hits by rule, exact match and the file in `Where:`, not by line, so a hit that only moved stays the same finding; a duplication group is matched by rule and match alone, open while any copy is left. Judgment and copy finds have no pattern to match, so the reconcile leaves them `unchecked` and only a fresh read closes them. `--write` updates statuses, lines and the `Scanned:` commit in `findings.md` itself, so a ledger with hundreds of findings is not edited by hand.
