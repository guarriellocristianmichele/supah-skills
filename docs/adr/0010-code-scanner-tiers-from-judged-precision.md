# The code scanner's tiers come from judged precision, not from how AI-typical a pattern is

`skills/ai-slop-audit/scripts/codescan.py` finds mechanical slop in Python (with `ast` and `tokenize`) and in JavaScript and TypeScript (with line regexes): placeholders, comments that restate the next line or narrate an edit, catch blocks that only rethrow, swallowed broad exceptions, runtime type checks that repeat an annotation, forwarding wrappers, `if c: return True else: return False`. As in ADR 0003, the scanner finds candidates and the audit judges them. A tier says how often a hit turns out to be real when someone reads it: S at 90% of at least 8 judged hits, M at 70%, W below. Verdicts live in `PRECISION` in `scripts/calibrate_code.py`.

The prose rule (ADR 0007) measures authorship evidence: a pattern earns a tier when it is rare in human text and common in AI text. That is the wrong question for code. Slop is complexity the behaviour does not need, whoever wrote it, and a catch that only rethrows is as useless in a human file as in a generated one. The calibration showed it: on 1,000 human files per language (CodeMirage, GitHub code cleaned in May 2022), 1,200 files per language from ten 2025 models and 212 files from Sonnet 5.5, no rule reached a likelihood ratio of 20, and most stayed under 3.

## Findings that shaped the rules

- Sonnet 5.5 writes almost none of the classic tells: no restating comments in 93 parsed Python files (3.9% of human files, 8.5% of 2025-model files), no forwarding wrappers, rethrows or placeholders. Asked to write a file from a description, a frontier model now produces code that looks like 2022 human code on these patterns. Its slop sits in design (options, fallbacks, validation nobody needs), which the audit's reach paths judge and a regex cannot.
- `changelog-comment` first matched "Modified BSD License" and "Fixed header on scroll" (0 of 5 hits real). It now matches only narrated edits ("Updated to…", "Now uses…"), which no file in the corpora contains; it keeps its designed tier until verdicts exist.
- 12.6% of the human Python files are Python 2 and do not parse; they are left out rather than guessed.
- A model that recognises a seed file recalls it: 47 of 260 Sonnet files matched their seed on more than half their lines (one reproduced a Bitcoin Core licence header). They are set aside as human code, as CodeMirage does with its BLEU cap.

## Considered options

- ADR 0007's likelihood-ratio tiers: rejected for the reason above; with them every rule but two fell to W, and slop-guard would have stayed silent on code.
- A larger frontier sample (1,800 files across Opus, Sonnet and Haiku): deferred. 260 Sonnet generations cost $27 in API-equivalent usage, four times the estimate, because of `@path` attachments and cache writes; the script now neutralises `@` and turns caching off.

## Consequences

- Rates and likelihood ratios stay in `docs/research/2026-11-code-calibration-results.md` as context: they say where today's models differ, not whether a hit is real.
- Eight verdicts per rule is the minimum for S. More verdicts, from audits or slop-guard sessions, go into `PRECISION`, then `calibrate_code.py report` and `release.py --sync`.
- The next corpus for frontier slop is agent patches against human patches for the same task (SWE-bench-style), where design-level slop shows up.
