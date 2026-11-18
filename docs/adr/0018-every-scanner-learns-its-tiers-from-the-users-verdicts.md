# Every scanner learns its tiers from the user's verdicts

The prose scanner already learned from verdicts: every judged hit (`tell`, `kept`, `fp`) went into a log in the user's config folder, and `learn.py` turned the log into a model, a Beta-Binomial posterior on each rule's precision that moves the rule's tier after 30 verdicts at 95% confidence, plus suppressions for a context judged `fp` again and again. The design and code scanners recorded nothing they used: design kept a log no scan read (ADR 0011), and code kept none (ADR 0010). Now all three learn the same way.

- **One module.** `skills/ai-slop-prose/scripts/learn.py` is the source; `release.py --sync` copies it next to `designscan.py` and `codescan.py`, and `--check` fails when a copy differs. Each scanner selects its own store (`supah-skills/prose`, `design`, `code`, or `SUPAH_<NAME>_HOME`), and reads a log by its header, so design's existing log, with a `file` column and no language, counts as it is.
- **More verdicts.** Besides a sweep's before and after, an audit records its judgments: design's `verdict --judged` turns each scanner finding into `reflex` and each keep line into `fp` or `chosen`; code's `verdict --judged` reads a file of judged hits (`tell` when it became a finding, `fp` when the falsification disproved it). Each judgment carries its finding or location in the reason, so a re-run records nothing twice.
- **Only tiers and suppressions.** Learning moves an existing rule between S, M, W and off, and keeps a context out; it never adds or rewrites a rule, which still takes a fixture and a recalibration in the repository. Inventory scans and `reconcile` keep the calibrated tiers, so a ledger does not shift under the user.
- **Visible progress.** After 30 verdicts per rule is a long way off, so every `verdict` prints each touched rule's count toward 30, its precision so far and its tier, and asks for `audit` (a human sample, whose verdicts override the model's) when a change would rest on the model's verdicts alone.
- **Shared on request only.** Nothing is sent anywhere. `export` writes per-rule aggregates (rule, language, tiers, `tell`/`kept`/`fp` counts, human count, precision, lower bound) with no match and no context, for the user to read and attach to an issue when the shipped tiers should move for everyone.

## Considered options

- Lower thresholds so learning shows sooner: rejected; 30 verdicts and 95% confidence come from `docs/research/2026-11-false-positive-control.md`, and AGENTS.md requires new research to change them. Showing the progress answers the same complaint without loosening the guard.
- Learning in the inventory scan too: rejected for now; `reconcile` matches findings to hits, and a hit the model suppressed would close a finding the audit never re-judged.
- Telemetry to calibrate the shipped tiers automatically: rejected; matches and contexts are the user's code and text, and the user decides what leaves the machine.

## Consequences

- Two users' scans of the same file can differ once their verdicts do; `--no-learn` (or `SUPAH_<NAME>_NO_LEARN`) gives the shipped tiers, and the test suites run with it.
- A change to `learn.py` is made in the prose copy and synced; the other two are never edited by hand.
