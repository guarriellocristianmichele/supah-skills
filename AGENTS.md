# supah-skills

Agent skills (Agent Skills format) for cleaning AI slop out of code and prose, plus an orchestrator. Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/adr/`. Research behind lexicons and install routes: `docs/research/`.

## Rules for changing this repo

- A new skill lives in `skills/<name>/` and is listed in `.claude-plugin/plugin.json` and as its own entry (`source: ./skills/<name>`) in `.claude-plugin/marketplace.json`.
- Every SKILL.md carries the **Ask with options** paragraph verbatim after its placeholder line (ADR 0013).
- buyer-panel's anchor statements, default intent weights and check thresholds (round checks and buyer variety) change only with a source in `docs/research/2026-11-synthetic-panels.md` and a reason in ADR 0014, and come with a fixture or an assertion in `tests/`; its edges to orchestrate, ai-slop-prose and ai-slop-design are in ADR 0012's call graph.
- A skill that calls another follows ADR 0012: add the edge to its call graph, say what happens when the target is not installed, and fan out over more than three units through `orchestrate`.
- A plugin that is not a skill (hooks) lives in `plugins/<name>/` with its own `.claude-plugin/plugin.json` and a marketplace entry `source: ./plugins/<name>`; never add `hooks/` at the repo root, it would attach to the bundle (ADR 0008).
- `plugins/slop-guard/scanner/` and `codescan/` are copies of `skills/ai-slop-prose/scripts` and `skills/ai-slop-audit/scripts`: after changing either, run `python scripts/release.py --sync` and commit both.
- A change to a code scanner rule comes with a fixture in `tests/fixtures/code/` and a recalibration: `python scripts/calibrate_code.py fetch` and `frontier` (once, into `.calibration/code/`), then `run` and `report`; commit `codescan-calibration.json` and `docs/research/2026-11-code-calibration-results.md` (ADR 0010).
- A change to a design scanner rule comes with a fixture in `tests/fixtures/design/` and a recalibration: `python scripts/calibrate_design.py fetch` (once, into `.calibration/design/`), then `run`, `sample <rule>` for judged hits, and `report`; commit `designscan-calibration.json` and `docs/research/2026-11-design-calibration-results.md` (ADR 0011).
- Release with `python scripts/release.py <x.y.z>`: it sets the version in every manifest and runs every check. Before any commit, `python scripts/release.py --check` must pass.
- READMEs: English first, an `## Italiano` section last, sentence-case headings. They must pass the prose scanner; add a deliberate exception to `docs/readme-keep.tsv` with a reason, never silence a rule.
- A change to a scanner rule or lexicon comes with a fixture or an assertion in `tests/`, and a recalibration: `python scripts/calibrate.py fetch` (once, into the ignored `.calibration/`), then `run` and `report`; commit the new `calibration.json` and `docs/research/2026-11-calibration-results.md` (ADR 0007).
- Skill bodies use Claude Code features (`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, `` !`cmd` ``) and keep the one line that tells other agents how to resolve them.
- Pairing with mattpocock/skills goes through their configuration files only: never copy their formats, never write `docs/agents/`, `.scratch/` or `.out-of-scope/` (ADR 0005).
- Skill scripts stay Python 3.10+, standard library only (ADR 0002, ADR 0009).
