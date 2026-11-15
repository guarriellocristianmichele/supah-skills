# The design scanner's tiers come from judged precision, and its verdict log never moves a tier at scan time

`skills/ai-slop-design/scripts/designscan.py` reads frontend source (class strings, CSS declarations and style objects, visible text) for design reflexes: choices that appear whatever the subject, such as purple gradients, gradient text, icon-card grids, glued arrows, text below WCAG contrast and styles copied instead of shared. As in ADR 0003, the scanner finds candidates and the model judges each one. A reflex is a default rather than an authorship signal: a human designer who sets Inter has made the same unchosen choice as a model. So the tier rule is ADR 0010's, not ADR 0007's: S at 90% of at least 8 judged hits, M at 70% of at least 8, W below or with fewer verdicts. Verdicts live in `PRECISION` in `scripts/calibrate_design.py`.

A `chosen` verdict (a brand colour, a real sequence, a live status dot) counts as a real hit: the rule found the pattern it names, and intent belongs to the keep file. Only `fp` counts against a rule. Rules that no verdict has reached keep their designed tier; at release every designed M rule must have at least 8 judged hits drawn from the calibration corpus, or it ships at W.

## Calibration corpus

- AI-era pages: the sites labelled by design-slop-cop (MIT, about 190 Show HN launches labelled in April 2026), read from the Wayback Machine snapshot closest to each label date.
- Human pages: a seeded sample of Tranco-listed domains as archived in June 2021, before generated sites were common.
- Each page is its archived HTML plus up to six linked stylesheets, fetched with the standard library. Pages whose HTML is nearly empty (client-rendered apps) are counted and left out; the results note states how many pages were usable.
- slop-cop's labels are page-level: they say a pattern is somewhere on the rendered page, not that a given hit is real. They are reported as agreement, never turned into verdicts.

## Considered options

- Likelihood-ratio tiers (ADR 0007): rejected, for the reason above; a reflex is unchosen whoever wrote it.
- Per-user learning from the verdict log, as ai-slop-prose does: deferred. The log (`designscan.py verdict`) records evidence for the maintainer to copy into `PRECISION`; the scanner never reads it, so two users' scans of the same file always agree.
- Rendering pages (headless Chrome) for computed styles: rejected for the skill script (ADR 0002). Contrast is therefore checked only where text and background are declared on the same element or in the same CSS block, and render-level reflexes (a centred hero, dead bands) are judged from screenshots when a browser tool exists.
- Reusing ai-slop-prose's extractor (`extract.py`): rejected; it reads the visible text of a page, while most design rules read class strings and CSS declarations, so the design scanner has its own reader and needs no copy kept in sync.
- Calling impeccable's or hallmark's detectors: rejected; they need Node and Chrome, and their rules change upstream (ADR 0005).

## Consequences

- A rule change comes with a fixture in `tests/fixtures/design/` and a recalibration: `python scripts/calibrate_design.py fetch` (once, into `.calibration/design/`), then `run`, `sample <rule>` for the judging pass, and `report`; commit `designscan-calibration.json` and `docs/research/2026-11-design-calibration-results.md`.
- Duplication rules count across the files of one scan, so the skill passes all files of a feature in one call.
