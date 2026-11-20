# Skills keep lessons per project and draft issues about themselves

Scanner tiers learn from verdicts (ADR 0018), but the way a skill works did not learn from anything: a fix the user reverted, a job that failed for a setup it could have run, a step the user had to redo by hand left no trace, and the next run made the same mistake. Every skill now carries the same paragraph, **Lessons**, after Next step.

- **Two triggers only.** A lesson is written when the user corrects or undoes what the skill did, or when a run ends failed or partial for a cause the skill could have avoided. A run that went well writes nothing, and a skill's opinion of its own work is not a trigger.
- **One file per project.** `.supah/LESSONS.md` at the repo root, excluded from git through `.git/info/exclude`, with a `## <skill>` section per skill. It sits in the project, not in a skill's folder, so a per-skill install reaches it, and skills without a ledger (ai-slop-prose, doc-truth, mutation-check, context-audit) have one too. Each skill reads its section at the start of a run.
- **A fixed shape and a cap.** Each lesson has its date, trigger, evidence (the user's words, a commit, an output), the step it changes and one positive rule. At most 15 per skill; a lesson that contradicts an older one replaces it, and past 15 the oldest goes, so the file cannot grow into sediment.
- **The skill never edits itself.** A lesson about the skill's instructions, true in any project, becomes an issue draft for this repository with no code or text from the user's project. The user chooses to open it, save it in `.supah/issue-drafts/`, or drop it. A change to a SKILL.md still goes through review, its tests and `release.py --check`.

## Considered options

- Skills rewrite their own SKILL.md from lessons: rejected; instructions changed without review drift, contradict each other and cannot be tested, and an installed skill's folder is replaced on the next update.
- One file per ledger (`.slop-audit/LESSONS.md`, `.slop-design/LESSONS.md`): rejected; half the skills have no ledger.
- The agent's own memory (Claude Code's auto-memory): rejected as the store; it is per agent and per user, not per project, and other agents have none. A lesson stays readable by any agent that opens the repository.
- A lesson after every run: rejected; most runs teach nothing, and a file filled with them buries the few that matter.

## Consequences

- A new skill copies the paragraph verbatim after Next step; `python scripts/release.py --check` fails a SKILL.md without it.
- The paragraph names the read command, `sed … 2>/dev/null || true`: most projects have no `.supah/LESSONS.md`, and a read the agent composed itself ended its shell call with exit code 2 there. The heading match allows trailing whitespace, so a file saved with CRLF still matches. `tests/test_release.py` runs the command with and without the file.
- Issues about a skill's instructions arrive from users as drafts they approved, with the step they concern; the fix still lands here with a test where one can be written.
