# Skill tuning trials

Each skill is reviewed against mattpocock's `writing-for-agents` (context pointers, information hierarchy, completion criteria, leading words, pruning) and the candidate is run against the current version on the same tasks before it replaces it.

## Method

The pilot ran three versions: the current skill, V1 (pruning: no-ops, exposition, duplication) and V2 (restructuring: verdicts moved into TELLS.md, sweep steps merged into gates). From the second lot on, the current skill runs against one variant that fixes the instruction and gate defects found by reading and running it.

Every run is a fresh Opus subagent given the skill folder and one task, with no user available: it takes the recommended answer wherever the skill says to ask. Folder names are neutral, so the agent does not know which version it runs. Each run has its own copy of the input and its own `SUPAH_PROSE_HOME`, so the learned model starts empty and the user's own model is untouched.

The checks are the rescan exit code, `scan.py compare` against the original, words, subagent tokens, tool calls and duration. A local HTML page shows the outputs side by side under shuffled labels. Quality is the gate; among versions that pass it, the shorter wins. If no variant beats the current skill, the current one stays.

## Lot 1: ai-slop-prose

Tasks: sweep `tests/fixtures/slop-en.md`, sweep `tests/fixtures/slop-it.md`, and draft a 120 to 160 word README intro for a CLI that dedupes CSV rows and normalises headers.

Words loaded per invocation (SKILL.md and TELLS.md): current 2241, V1 2101, V2 2088.

| Run | Tokens | Tools | Seconds | Rescan | Compare |
|---|---|---|---|---|---|
| current, en | 92,200 | 12 | 101 | 0 | 1 missing |
| V1, en | 84,486 | 9 | 93 | 0 | 1 missing |
| V2, en | 87,294 | 11 | 108 | 0 | 1 missing |
| current, it | 83,266 | 9 | 80 | 0 | 1 missing |
| V1, it | 84,907 | 7 | 90 | 0 | 2 missing |
| V2, it | 84,924 | 10 | 95 | 0 | 2 missing |
| current, draft | 79,453 | 8 | 67 | 0 | n/a |
| V1, draft | 82,477 | 12 | 95 | 0 | n/a |
| V2, draft | 77,369 | 8 | 72 | 0 | n/a |

Mean tokens: current 84,973, V1 83,957, V2 83,196. The spread sits inside run-to-run noise: a run costs about 80,000 tokens whatever the skill says, and pruning the text saves about 150 of them.

V1 won all three tasks on the text:

| Task | Why V1 | What the others did |
|---|---|---|
| en | kept the author's contractions and added no fact | current asserted "the gain has held"; V2 dropped the hedge on the unsourced claim and ended on a one-line punch |
| it | kept the meaning, no repetition | current repeated "lavoro… lavoro" and added urgency ("da cogliere adesso"); V2 repeated "lavoro… si lavora" |
| draft | the one worked input and output example, and the warning against redirecting onto the input file | correct, without an example |

## Defects every version shared

The runs found defects no wording change fixes, since all three versions hit them:

1. `compare` reports fixed capitals as lost names. After a Title Case heading or a capital after a colon is fixed, compare lists the old words as a missing name, so its "nothing missing" gate fails in 6 sweeps out of 6 and each agent wrote its own justification for passing anyway.
2. `vague-attribution` (en) is case-sensitive. It matches "Experts argue" and misses "experts argue"; the Italian rule matches both. All three English runs found the miss by reading.
3. TELLS.md disagreed with the scanner. It listed designed tiers without saying calibration admits many rules a tier lower, and it lacked `ecco-opener`, `summary-closer` and `bold-heading`. Four sweeps out of six reported the mismatch.

The third is fixed with V1, and `tests/test_scan.py` now fails when a scanner rule is missing from TELLS.md. The first two change the scanner and go in their own change, with fixtures and a recalibration (ADR 0007).
