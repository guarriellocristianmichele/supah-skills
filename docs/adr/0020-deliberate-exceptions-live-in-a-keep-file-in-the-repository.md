# Deliberate exceptions live in a keep file in the repository

The prose scanner and doc-truth kept the hits and claims left on purpose (a quote, a term, a script removed in a known commit) in a keep file in the scratchpad. The scratchpad does not outlive the session, so the next run reported the same exceptions and the user judged them again (issues #43 and #44). A judgment made once should hold for the project, for the next session and for a teammate.

- **One file per skill at the repository root.** `.slop-prose-keep.tsv` holds `rule<TAB>match<TAB>reason`, `.doc-truth-keep.tsv` holds `kind<TAB>claim<TAB>reason`; `#` starts a comment and a UTF-8 BOM is accepted. Each skill reads its file on every run without a flag, and the file is committed with the fixes. `--keep FILE` adds another file, for text outside a repository, and a missing one is an error rather than a silent no-op.
- **Found from what is scanned.** The prose scanner walks up from the scanned file to the first folder that holds `.git`, and falls back to the working directory; it starts no git process. doc-truth reads the file at the root of the repository it checks.
- **One judgment, however often it is seen.** A keep entry counts once for learning (ADR 0018): `verdict` records each entry the first time it applies, and a hit rewritten in the current run is recorded as a rewrite whatever the keep file says.
- **Parallel workers do not share it.** Under `orchestrate`, each worker writes its exceptions to its own keep file in the scratchpad; the coordinator appends them to the repository file before the final rescan.
- **This repository's README check ignores it.** `release.py` runs the scanner with `--no-repo-keep`, so README exceptions stay in `docs/readme-keep.tsv` with a reason, as AGENTS.md requires.

## Considered options

- Keep files in the scratchpad: rejected; they are lost with the session, so every exception is judged again.
- Markers inside the document or source file: rejected; they clutter text people read, and each source language would need its own comment syntax.
- One keep file shared by every skill: rejected; the columns differ (a rule and a match, or a kind and a claim), and skills are installed one at a time.
- The user's config folder, next to the learning store: rejected; it belongs to one machine, so a teammate or CI would see the exceptions again.

## Consequences

- A teammate, CI and the next session see the same exceptions, and a review sees each new one with its reason in the diff.
- A project that drops these skills is left with two small TSV files that nothing reads.
