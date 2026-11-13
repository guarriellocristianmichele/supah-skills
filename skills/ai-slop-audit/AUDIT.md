# audit

A target path narrows the scan to the modules under it; the report then says `SCOPED: <path>` and other rows keep their status.

## Steps

1. **Inventory.** List tracked files (`git ls-files`), group them into modules (a package, or a top-level source dir), and mark generated/vendored code `skipped:generated`. Find the **entrypoints**: manifest `main`/`exports`/`bin`, framework conventions (routes, pages, migrations, DI registries, plugin loaders), CLI and worker scripts, files referenced by build/CI/Docker config. Write one `inventory.md` row per module (`pending`). Done when every tracked source file belongs to exactly one row.
   Read the project's domain glossary and the ADRs in each area before scanning it; name findings in glossary vocabulary. A structure an ADR records as deliberate becomes `rejected:ADR-<n>`, so later runs skip it.
2. **Tooling.** Note analyzers the project already has (knip, ts-prune, depcheck, vulture, jscpd, eslint/ruff unused rules, compiler unused flags) and run them; fall back to `rg`. Record tool output as evidence, never as verdict: analyzers miss dynamic reach.
3. **Scan** `pending` rows in inventory order against the categories below, marking each row `scanned@<HEAD>`. Run the `orchestrate` skill when installed (otherwise scan the rows yourself, in order, with the same checkpoints): job `audit`, units = pending modules, profile `light` (`build` when analyzers run per module), state dir `.slop-audit/`, unit brief = the categories, the finding schema and the reach-path list, done when every category was checked against the module. Workers return findings without IDs; you merge them, assign IDs and update the inventory.
4. **Cross-module pass.** Semantic duplication and reinvented logic surface only across modules: compare helpers, validators, formatters, HTTP/retry/cache/date utilities between modules, and against the stdlib and existing dependencies.
5. **Falsify.** For each finding, search for the reach path or caller that would make it wrong. Found one: drop or downgrade. Done when every finding names the paths checked.
6. **Report**: counts by category × confidence, top 10 high-confidence findings, and the coverage line.

**Completion.** Every row is `scanned@<HEAD>` or `skipped:<reason>`, and the report's first line is `COMPLETE: N/N modules`. Otherwise it is `PARTIAL: k/N modules` followed by the next pending rows; the next `audit` run resumes from there.

## Categories

Each category names the evidence that makes a finding real.

- **dead-code**: functions, branches, files no reach path hits. Evidence: zero hits across every reach path.
- **unused-export / unused-file**: Evidence as dead-code. Exports reachable from a published package entry are public API: flag only with proof the package is private or the symbol is undocumented and unreferenced downstream (`medium` at best).
- **unused-dependency**: declared, never used. Check imports, manifest scripts, CLI calls, config files loading plugins by string (babel, eslint, postcss, jest, vite), `@types/*` pairing, peer requirements.
- **duplication (textual)**: copy-pasted blocks. Evidence: both locations and the shared span.
- **duplication (semantic)**: different code, same behaviour. Evidence: both locations, equivalence argued over inputs and edge cases, and every divergence listed; a divergence may be a deliberate fix, so note which copy is newer (`git log -L`).
- **reinvented**: logic the stdlib, an existing dependency or a project utility already provides. Evidence: the existing implementation and equivalence including edge cases.
- **premature-abstraction**: interface, factory, strategy, generic or config option with one implementation, one caller, or one value ever set. Evidence: implementation and caller counts, and what removing it does: the complexity disappears, rather than moving into the callers.
- **wrapper**: forwards to another call and adds nothing. Evidence: the body, and the same removal check. It earns its place when it is a test seam, a deliberate API boundary, or narrows types; check before flagging.

When the cure for either is a new interface rather than a removal (several shallow modules that belong in one deeper module), the finding is design work: set the `handoff` status from SKILL.md's Companions table and leave the code alone.
- **defensive-check**: null/type checks on values proven valid upstream, try/catch that only rethrows or swallows, re-validation of validated data. Evidence: the value's origin traced to show the guarded case is impossible. Checks at a **trust boundary** (user input, network, env, files, deserialization, auth, FFI) are security: keep them.
- **tautological-test**: asserts what a mock was told to return, asserts constants, or has no assertion. Evidence: the **mutation** of production code it would catch; none means tautological.
- **redundant-test**: exercises the same behaviour and branch as another test. Evidence: both tests and the branch they share.
- **incoherent-organization**: one kind of thing placed by conflicting conventions (two utils dirs, mixed naming, a misplaced layer), circular imports. Evidence: the conflicting instances and the dominant convention.
