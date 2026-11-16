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

## Lot 2: orchestrate

Tasks: a fresh job of six units (word count and H2 headings of six READMEs), and a resume from a state left mid-run: one orphan worker `running` under an ended session with two checkpoints, an open STOPPED block, two units never assigned. Both checkpoints in the seeded state close a placeholder line (`H2: (as counted)`) that fails the done criterion. Subagents can dispatch their own background workers, so these runs went through dispatch, the watchdog and calibration, not the inline path.

Reading the skill found two gaps. Step 5 calibrates from the free RAM at dispatch and the peak worker count, but `state.json` stored neither, so both were lost on resume. And a finished worker's units without a checkpoint were never returned to `pending`, so the job could not complete.

| Run | Tokens | Tools | Seconds | Units done | Calibration inputs in state |
|---|---|---|---|---|---|
| current, fresh | 90,334 | 18 | 123 | 6/6 | invented by the agent |
| variant, fresh | 89,056 | 15 | 116 | 6/6 | `dispatch_avail_mb`, `peak_workers` |
| current, resume | 93,956 | 19 | 188 | 6/6, placeholders redone | kept while running, then deleted |
| variant, resume | 92,736 | 19 | 158 | 6/6, placeholders merged | `dispatch_avail_mb`, `peak_workers` |
| final, resume | 95,373 | 20 | 136 | 6/6, placeholders redone | `dispatch_avail_mb`, `peak_workers` |

Neither the current skill nor the first variant says what to do with a checkpoint whose result fails the done criterion: one run redid the units, the other merged the placeholders. The final version says it, together with the other rules the runs had to improvise:

- `state.json` carries `dispatch_avail_mb` and `peak_workers`, and step 5 calibrates from them; inline runs skip calibration.
- A finished worker's units without a checkpoint return to `pending`, and a unit returned twice becomes `failed:<reason>`. A checkpoint whose result fails the done criterion does not count.
- Between notifications the orchestrator ends its turn instead of polling; one run had looped in Python because `sleep` is blocked.
- An orphan's STOPPED block gets the reason `orphan: session <id> ended`; all three resume runs had made one up.

The description, the one part loaded every session, lost its STOPPED_AGENTS_WORK.md clause. Token use again does not separate the versions.

## Lot 3: mutation-check

The trial repository holds `discount()` and `clamp()` with a known answer: three gaps (the 100 threshold, twice, and the rounding to two places), two equivalent mutants at the `clamp` boundaries, and `tests/test_mock.py`, which only checks what a mock returns. Tasks: the clean repository, and the same repository with an uncommitted function in the target file.

Computing the answer key exposed a bug in `mutate.py`: Python trusts a cached `.pyc` whose source has the same size and the same mtime second, so a mutant of the same length as the one before it ran the previous mutant's bytecode. Three mutants the tests kill (`*` to `/`, `-` to `+`, `1` to `2`) were reported as survivors, and an agent would have written them up as gaps. Every test run now gets a fresh `PYTHONPYCACHEPREFIX`. The trials then found a second bug: the file was read with universal newlines, so a CRLF checkout was restored as LF, git saw it as modified, the next run refused it and a `git stash pop` aborted. Both bugs have a regression test that failed before the fix.

| Run | Tokens | Tools | Seconds | Verdicts | File as the user left it |
|---|---|---|---|---|---|
| current, clean | 77,443 | 8 | 98 | 3 gaps, 2 equivalent, test_mock tautological | yes |
| variant, clean | 73,873 | 7 | 91 | same | yes |
| current, dirty | 80,220 | 16 | 155 | same | yes, stash popped |
| variant, dirty | 82,292 | 16 | 170 | same | yes, stash popped |

The outputs tie, so the shorter text wins except where the current one is wrong. Its completion criterion asked for `git status` to show the file clean, which on a file with uncommitted changes rewards leaving them in a stash; the criterion now asks for the same changes as before the run, with the stash popped. Step 3 asks with options (stash, recommended, or commit) instead of telling the agent to commit or stash, and a `timeout` counts as killed. The rewording of the tautology rule was dropped: both versions already ran the test file alone.

## Lot 4: slop-guard

`rules.md` is the one text here loaded in every session. Its prose line listed the tells to avoid ("not X, but Y", em dashes, "In conclusion", delve-type words…), which `writing-for-agents` warns can prime the very patterns it names. Three arms wrote the same pieces with the rules as session context: none (control), the current rules, and a rewrite that states each rule positively. Agents returned their text in the reply and wrote no file, so the PostToolUse hook played no part: the runs measure the first draft, which is what the session rules act on.

| Task | None | Current | Positive |
|---|---|---|---|
| 250-word engineering blog post (en) | 0 open hits | 0 | 0 |
| 250-word agency blog post (it) | 0 | 0 | 0 |
| `slugify()` and its tests | 0 codescan hits, tests pass; type and range checks for inputs the caller controls | 0, tests pass, no such checks | 0, tests pass, no such checks |

A second round on the genre most prone to tells, a 150-word LinkedIn launch post, compared none, current and a short prose line ("state each point plainly"): 0 open hits in all three.

On these tasks the model writes no catalogued tell with or without the prose line, so the line spent about 45 tokens a session for nothing measurable; the code line did change the code. The prose line is now "state each point plainly", and the tells are left to the PostToolUse hook, which names each one when the text is saved. The file went from 665 to 495 characters (about 166 to 124 tokens by the characters ÷ 4 estimate). One run per cell is a small sample: the evidence is that no arm wrote a tell, not that the line can never help.

## Lot 5: doc-truth

The trial repository has five commits and a README written against the first: a script renamed on purpose, a make target dropped on purpose, an environment variable dropped on purpose, a flag lost in a commit titled "tidy argument parsing", a wrong anchor, a link to a file that never existed, a state file the code never writes, and a default port the doc gets wrong. Fixing the script name brings two flags into reach: `--port`, which the wrapper forwards to the program that defines it, and the lost `--dry-run`. The current skill and a variant each ran twice.

| Run | Tokens | Tools | Seconds | Answer key (6 checks) | Code and history untouched |
|---|---|---|---|---|---|
| current, a | 78,696 | 10 | 107 | 6/6 | yes |
| current, b | 76,491 | 11 | 87 | 6/6 | yes |
| variant, a | 76,569 | 11 | 92 | 6/6 | yes |
| variant, b | 75,827 | 7 | 94 | 6/6 | yes |

All four runs also read `pip install -e .` against a repository with no packaging and fixed it. The variant's three additions (a forwarded flag counts as fp, W findings get verdicts too, a doc fix can surface new claims) changed nothing: the current skill's runs did all three on their own, so they were dropped. One gap showed up in all four runs. A code regression stays in the doc as a promise, yet the rescan must exit 0, and the skill described the keep file for false positives only; every run put the claim there with a reason it wrote itself. The rule is now written down: the claim goes in the keep file with reason `regression <commit>`. Under orchestrate each worker keeps its own keep file, while `doctruth.py` takes one `--keep`, so the workers' files are concatenated before the rescan.

## Lot 6: context-audit and supah-help

From this lot on, the current skill runs first, and a variant is written only for what its runs improvise.

**context-audit.** A synthetic Claude Code home (`--home`) holds two sessions, two always-on plugins whose hooks contradict `AGENTS.md` (a skill before every reply against acting when ready; fragments in every file against full sentences in docs), two TDD skills from different owners, a review pair that serves different steps, four stale references, a memory that restates an `AGENTS.md` rule, a Python 3.7 target the repo's `pyproject.toml` already breaks, and prompts that must never be quoted. Two runs (83,527 and 84,485 tokens) found every item, called the review pair `fp`, quoted no prompt and left `settings.json` to the user. Both had to place the stale references and sediment somewhere, since the report's five sections had no room for them: one added a sixth section, the other folded them into the fixes. The report now has a sixth section for them. Both also reported two sessions where the step asks for three; the step now says all of them when there are fewer.

**supah-help.** A router with no script or state, so the trial compared answers. Its "Why" cells restated how each routed skill works, although the skill already tells the agent to read every recommended SKILL.md, which decides; the platform-audit cell alone was about 250 words. A variant cut each reason to one sentence (2,001 to 1,724 words, keeping the phrases the router tests require) and fixed two facts: the skills that call `orchestrate` (the row said "the two skills above", which were doc-truth and mutation-check, and mutation-check does not) and the state folders (`.slop-design/` and `.buyer-panel/` were missing).

| Question | Current | Variant |
|---|---|---|
| a v0-built Next.js app that looks generic, with bloated code (it) | 90,189 tokens; one question (both, design first), design audit before code audit so frontend duplication is handed off, batches, verify | 88,533 tokens; the same question and flow |
| is a padel booking app worth building, and what to charge (en) | 85,351 tokens; buyer-panel run, read the report, price, test, ground | 79,585 tokens; run, price, test, without `ground` |

Both versions read the routed skills and gave the same flows; the variant's answers are shorter. With quality tied, the shorter version wins.

## Lot 7: ai-slop-audit

One chain on a small Python shop with planted slop and an answer key: a try/except that only rethrows, a forwarding wrapper, a one-implementation interface with its factory, restating comments, a duplicated helper, two dead functions, a test that asserts its own mock, and a trap, `round_up`, which looks unused but `hooks.json` reaches by name through `importlib`. Each mode ran in a fresh agent on the ledger the previous one left, as separate sessions would.

| Mode | Tokens | Tools | Seconds | Result |
|---|---|---|---|---|
| audit | 99,084 | 17 | 212 | all 8 planted findings, the trap rejected as reached via `hooks.json`, plus two the seed did not plant (`round_up` reimplements `math.ceil`; a plugin loader with one value) |
| plan | 87,320 | 11 | 135 | baseline in `checks.md`, 10 findings in 9 one-category batches, characterization tests where none existed |
| fix B2 | 89,101 | 14 | 107 | characterization tests green before the change, the rethrow removed, checks green after |

`fix B2` ran instead of B1 on purpose: B2 depends on B1 and needs a characterization test, so it exercises more of `FIX.md`. Building the repo exposed a script bug: `codescan.py` given a folder crashed with a traceback (`PermissionError` on Windows); a folder now expands to its source files. The runs improvised four things, now written down:

- `fix` did not check `depends-on`, and went ahead with B1 unfixed; a batch whose dependency is not fixed now asks first (fix that batch first, recommended, or go ahead naming the lines both touch).
- Removing the rethrow uncovered a scanner hit that an existing planned finding already names; such a hit no longer counts as worse than baseline, any other new one does.
- `fix` does not commit, while the next `fix` needs a clean tree; the report now ends with the commit to make.
- `AUDIT.md` said what to do for a tautological test with `mutation-check` installed but not without it, which AGENTS.md requires; the agent replaced the function in memory and showed the test still passed, and that is now the rule.

The chain was not re-run after the edits: each rule writes down what the run did on its own.

## Lot 8: ai-slop-design and buyer-panel

**ai-slop-design.** Two runs of the current skill, without a browser. `sweep` ran on the scanner's `slop.tsx` fixture as a page whose `DESIGN.md` names the purple-to-blue gradient as the logo (102,399 tokens): it fixed 31 of 38 hits, kept the gradient and the brand name as `chosen · brand`, left two placeholders that need real content for the user, rescanned to exit 0 and listed the copy for ai-slop-prose. `audit` ran on the scanner's three-route Next.js fixture (95,244 tokens): `COMPLETE: 4/4 surfaces`, eight findings, no source file touched, and two notes a reader needs (Tailwind is not installed, so the class strings render nothing; one component no route reaches). What the runs improvised was already settled: the scanner finds a unit through Git Bash's path rewrite, including the root route, and the audit writes the same checkpoints without orchestrate. No change.

The sweep's `verdict` step wrote its 36 verdicts to the real per-user log, because the run did not set `SUPAH_DESIGN_HOME` as the prose runs set `SUPAH_PROSE_HOME`. They were removed from the log afterwards; later trials set both.

**buyer-panel.** A real panel costs millions of tokens, so this lot is a static read and the script tests. Every step a file cites by number (`RUN.md` steps 3, 7, 9, 10, 11, 12, 14 and 15, `TEST.md` 5 and 7, `PITCH.md` 4) is the step it names, and the `test_panel*` tests pass. The companions listed ai-slop-prose twice, once for reports and pitches and once for `test`; they are now one entry.
