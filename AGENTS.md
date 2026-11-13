# supah-skills

Agent skills (Agent Skills format) for cleaning AI slop out of code and prose, plus an orchestrator. Vocabulary: `GLOSSARY.md`. Decisions and their reasons: `docs/adr/`. Research behind lexicons and install routes: `docs/research/`.

## Rules for changing this repo

- A new skill lives in `skills/<name>/` and is listed in `.claude-plugin/plugin.json` and as its own entry (`source: ./skills/<name>`) in `.claude-plugin/marketplace.json`.
- A plugin that is not a skill (hooks) lives in `plugins/<name>/` with its own `.claude-plugin/plugin.json` and a marketplace entry `source: ./plugins/<name>`; never add `hooks/` at the repo root, it would attach to the bundle (ADR 0008).
- `plugins/slop-guard/scanner/` is a copy of `skills/ai-slop-prose/scripts`: after changing the scanner, run `python scripts/release.py --sync` and commit both.
- Release with `python scripts/release.py <x.y.z>`: it sets the version in every manifest and runs every check. Before any commit, `python scripts/release.py --check` must pass.
- READMEs: English first, an `## Italiano` section last, sentence-case headings. They must pass the prose scanner; add a deliberate exception to `docs/readme-keep.tsv` with a reason, never silence a rule.
- A change to a scanner rule or lexicon comes with a fixture or an assertion in `tests/`, and a recalibration: `python scripts/calibrate.py fetch` (once, into the ignored `.calibration/`), then `run` and `report`; commit the new `calibration.json` and `docs/research/2026-11-calibration-results.md` (ADR 0007).
- Skill bodies use Claude Code features (`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, `` !`cmd` ``) and keep the one line that tells other agents how to resolve them.
- Pairing with mattpocock/skills goes through their configuration files only: never copy their formats, never write `docs/agents/`, `.scratch/` or `.out-of-scope/` (ADR 0005).
- Skill scripts stay Python 3.10+, standard library only (ADR 0002, ADR 0009).
