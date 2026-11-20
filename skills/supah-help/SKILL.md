---
name: supah-help
description: Ask which supah skill or flow fits your situation, and why. A router over ai-slop-audit, ai-slop-design, ai-slop-prose, buyer-panel, context-audit, doc-truth, mutation-check, orchestrate and the slop-guard hooks, with how they pair with mattpocock/skills.
argument-hint: "[what you are trying to do]"
disable-model-invocation: true
---

# supah-help

The user describes a situation (`$ARGUMENTS`; Claude Code fills it in, elsewhere read it from the request). Recommend the flow below that fits, the exact commands in order, and the reason behind each step. Answer in the user's language. When the situation fits two rows, ask one question that separates them; when `$ARGUMENTS` is empty, ask with options which of the four groups under Situations is theirs (the group headings are the answers), then show that group's rows and ask which one fits.

**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when the answer is a fact about the world. What only the user can decide, ask as one question with 2 to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's `AskUserQuestion` shows them on screen, other agents number them in the reply.

**Next step.** End every run with the next step of the workflow, worked out from what this run left (the ledger's statuses, failed or blocked units, a question still open, the user's goal): the exact command and its reason in one line, and when two fit, both, the recommended one first; a skill that keeps a `STATUS.md` writes the same command as its next action. Put `/clear` before it (on another agent, a new session) when this run left its state on disk for that command to read; keep the session when the next step answers this run in conversation. When another skill called this one, hand the result back to it instead. When nothing is left, say the workflow is done.

**Lessons.** At the start of a run, read this skill's section of `.supah/LESSONS.md` at the repo root with `sed -n '/^## <skill>[[:space:]]*$/,/^## /p' .supah/LESSONS.md 2>/dev/null || true`, and follow its rules; no output means no lessons yet. Write a lesson only when the user corrects or undoes what this skill did, or when a run ends failed or partial for a cause the skill could have avoided: one entry under `## <skill>` (on first use create the file and add `.supah/` to `.git/info/exclude`) with the date, the trigger (`correction` or `failure`), the evidence (the user's words, the commit or the output), the step it changes, and the rule in one positive line. Keep at most 15 per skill: a lesson that contradicts an older one replaces it, and past 15 the oldest goes. A lesson about this skill's own instructions, true in any project, changes nothing here: draft an issue for guarriellocristianmichele/supah-skills (title, the SKILL.md step, what happened, no code or text from the project) and ask with options: open it with `gh issue create`, save it in `.supah/issue-drafts/`, or drop it. The report names the lessons added, replaced and drafted.

Read the SKILL.md of every skill you recommend (in this skill's sibling folders, `${CLAUDE_SKILL_DIR}/../<skill>/SKILL.md`, or wherever it is installed) before describing what it does or saying a step can be skipped; the lines here orient, the SKILL.md decides.

Every command sequence you write follows the Next step rule at each step: `/clear` after each command that leaves its state in `.slop-audit/`, `.slop-design/`, `.buyer-panel/` or `.orchestrator/` (an audit, a plan, a publish, a fix or sweep, a buyer-panel round).

When no row fits and no skill here covers the situation, say so in one line instead of stretching a flow to fit it: name the Boundaries line that covers it, or a skill outside this set that does (a mattpocock skill such as `writing-for-agents` or `/improve-codebase-architecture`, or one the user already has installed), and recommend no supah command.

## The approach

Every recommendation follows these five habits. State the one behind each step you suggest.

1. **Evidence before change.** Nothing is deleted or rewritten on a hunch: a finding carries the commands that prove it, a prose hit carries its context. Code that looks unused may be reached by a string, a route or a config file.
2. **Measured, not guessed.** Thresholds come from corpora, memory budgets from the machine, precision from recorded verdicts. When a number is unknown, the flow measures it first.
3. **Small, reversible steps.** Fixes land in batches that revert on their own, behind the project's checks; a partial scan is reported as partial.
4. **People decide what leaves the machine.** Issues, pushes and approvals of fixes wait for the user; a sample of the model's own verdicts goes back to the user for audit.
5. **Standalone first, paired by configuration.** Each skill works alone; with mattpocock/skills installed, they read its configuration and hand it the work it owns, without copying its formats.

## Situations

### Cleaning code, docs and tests

| You are… | Flow | Why this way |
|---|---|---|
| looking at a codebase built fast with AI that feels bloated | `/ai-slop-audit audit` → `/clear` → `plan` → `/clear` → `fix all` (or `fix B1`, one batch at a time, then `/clear` → `verify`) | the audit proves every reach path before calling code dead; the plan records a test baseline, so each batch can be checked and reverted on its own; `fix all` runs every batch whose blockers are done in parallel, each in its own worktree, merges each into one integration branch before its dependents start, and runs `verify` there |
| sharing that cleanup with a team or with agents | after `plan`: `/clear`, `/ai-slop-audit publish`, then `/clear` and work them all with `fix #<map>`, or one at a time with `fix #<n>` or `/implement #<n>` | issues carry their own done-when checks and evidence, so whoever picks one up needs no local state |
| holding a plan with many batches, too slow to work one command at a time | after a plan: `/clear` → `/ai-slop-audit fix all` or `/ai-slop-design sweep all` (or the map issue: `fix #<map>`, `sweep #<map>`) | the batches run as a blocker graph: each starts when its blockers are merged, batches sharing a file wait for each other, a failed batch holds back only its dependents, and one pull request closes the done issues after you say yes |
| docs that may no longer match the code (renamed scripts, dead links, removed flags) | `/doc-truth` | every claim is checked against the repository before anything is rewritten; a doc is fixed when the code changed on purpose, and the code is reported when it lost what the doc promises |
| unsure whether the tests protect a refactor, or suspecting a test checks nothing | `/mutation-check <file> --function <name> <test command>` | each change the tests let through is a behaviour nobody checks; a survivor is called equivalent or a gap only after reading it |

### Cleaning what people see: pages, design and text

| You are… | Flow | Why this way |
|---|---|---|
| building a new site, landing page or app screen and wanting it not to look generated | `/ai-slop-design craft <brief>` | the reflex answer for the category is written down and set aside first, so every choice in the direction has a reason tied to the subject; the build is swept and checked on screenshots before it is shown |
| looking at a site that reads as "AI made this" (purple gradients, icon-card grids, glass, eyebrows), or with low-contrast text and copy-pasted styles | `/ai-slop-design sweep <files>` (pass all files of a feature together) | each hit is judged against the brand and the content before it changes; a page that sits in a whole lane is handed to `craft` instead of patched; duplicated styles are counted across files; with no files, on a repo above 5 surfaces or 40 frontend files, it asks first whether to audit instead |
| holding a page a sweep marked `handoff` (it sits in a whole lane: cream and clay, near-black and neon, the SaaS card kit) | after the sweep: `/clear` → `/ai-slop-design craft <surface>` | the brief is read from the page and every string, link, form and handler is listed before the restyle and compared after it, so only the look changes; the new direction is checked against the lane the page sat in |
| looking at a whole platform (dozens of routes, hundreds of components) that reads as generated, before deciding what to fix | `/ai-slop-design audit [path]` → `/clear` → `/ai-slop-design plan` → `/clear` → `/ai-slop-design publish` (when others will work the batches) → `/clear` → `/ai-slop-design sweep all` (every batch a scanner verdict settles, in parallel; or `/ai-slop-design sweep B<n>`, one at a time, `B1` first) → `/clear` → `/ai-slop-design craft <surface>` for each handoff batch → `/clear` → `audit` again | nothing is edited until a batch is swept: each route is judged in its own context and the verdicts stay in `.slop-design/`, so a re-run resumes, and `audit` run again reconciles the ledger, closing what was fixed; shared tokens and components are batched before page fixes, and `sweep all` merges them before the pages that use them start; `/ai-slop-audit audit` on the same repo marks frontend duplication `handoff:ai-slop-design`, so each copy is reported once |
| sharing a design cleanup with a team or with agents | after `/ai-slop-design plan`: `/clear`, `/ai-slop-design publish`, then `/clear` and work them with `sweep #<map>`, or each issue with the command on its Work line (`sweep B<n>` or `craft <surface>`) | nothing is opened until you approve the drafts, and each issue carries its files, evidence and checks, so whoever picks it up needs no local ledger |
| cleaning the text people see in an app (UI copy, error messages, translations) | `/ai-slop-prose sweep src/**/*.tsx locales/*.json` | only visible strings are read, never comments or code; each text has a purpose (button, error…) and is rewritten for it |
| editing a page, post, email or README | `/ai-slop-prose sweep <file>` and say what it is for ("landing page", "onboarding email") | the purpose picks the rewrite rules in PURPOSES.md; calibration keeps human-sounding text untouched (under 1% of human documents need a fix) |
| writing something new for people | nothing to type: ai-slop-prose drafts to its rules and sweeps its own draft | catching a tell while drafting is cheaper than sweeping it out afterwards |

### Testing a business idea

| You are… | Flow | Why this way |
|---|---|---|
| wondering whether an idea or a product is worth building, before spending money on it | `/buyer-panel <idea>`, or `/buyer-panel` inside the product's repo; then the real test its report names | each buyer sees the idea next to real competitors and "buy nothing", in a fresh context, and a script computes every number; a synthetic panel only suggests hypotheses, so it ends with a test on people |
| holding a first panel and wanting to know what would remove the top reason buyers passed | after the first panel: `/clear` → `/buyer-panel fix`, or `/buyer-panel fix <reason>` | the same buyers see the changed offer in fresh contexts, so the diff shows who flipped and why |
| choosing between two offers, names or positionings, or asking what happens if a competitor arrives or cuts its price | after a first panel: `/clear` → `/buyer-panel compare "<A>" "<B>"`, or `/buyer-panel competitor <name> [price]` | the panel's noise is printed next to the difference, so a small gap is not read as a win |
| asking which price to charge, or how to pitch to the people most likely to buy | `/buyer-panel <idea>` → `/clear` → `/buyer-panel price` (three prices from the report's range, or `price <low> <mid> <high>`) → `/clear` → `/buyer-panel pitch [type]` | the pick rests on price times discounted buyers; synthetic prices run two to three times too high, so it is an upper bound to confirm with real people |
| ready to test an idea on real people after a panel | after the panel: `/clear` → `/buyer-panel test` → run the interviews and the smoke test it writes → `/clear` → `/buyer-panel ground` with the counts | the go and stop thresholds are written down before the test goes live, so the result can't be read to fit |
| back from a real test (smoke test, interviews, a pre-sale) and wanting to know how far the panel was off | `/buyer-panel ground` | the counts come only from your records and are compared with the round that showed the same offer at the same price; the ratio is kept for the project, so every later BUY share, on any panel, prints a corrected figure under the simulated one |

### Your setup: context, sessions, learning, other skills

| You are… | Flow | Why this way |
|---|---|---|
| paying for a big context before typing anything, or getting instructions that fight each other | `/context-audit` | the first request's tokens are measured from your transcripts and split by plugin, so you cut what costs most; every contradiction is quoted from both sides before anything changes |
| wanting Claude to avoid slop in every session, without asking | `claude plugin install slop-guard --marketplace guarriellocristianmichele/supah-skills` (Claude Code only) | its hooks add about 120 tokens of rules per session and scan only the prose Claude just saved, so clean work costs nothing |
| told by the scanner that fine text is slop | keep the hit with reason `fp`, finish the sweep, then `scan.py verdict`; once in a while `scan.py audit` | verdicts measure each rule's precision, in prose, design and code alike; after 30 verdicts a noisy rule loses tier on your machine, each sweep shows how far it is, and `export` hands the counts (no text) to the maintainer, and your audit checks the model's judgement |
| wanting the skills to learn from you and remember the corrections you made | nothing to type: each skill reads its section of `.supah/LESSONS.md` at the start of a run and adds a lesson when you correct or undo what it did, or when a run fails for a cause it could have avoided; each scanner moves a rule's tier once your verdicts on it reach 30 | lessons stay in the project, out of git, at most 15 per skill, so any agent that opens the repository reads them and you can edit or delete one; a skill never rewrites its own instructions: a lesson about them becomes an issue draft you open, save or drop |
| running a job over many files, or a slow, loaded machine | nothing to type for ai-slop-prose, ai-slop-audit, ai-slop-design, doc-truth and buyer-panel, which call `orchestrate` themselves; `/orchestrate` for your own fan-out | agents are sized to free RAM, stopped newest-first under pressure, and resumed from `STOPPED_AGENTS_WORK.md` |
| coming back after an interrupted session | run the same command again | `.slop-audit/`, `.slop-design/`, `.buyer-panel/`, `.orchestrator/` and the verdict log keep the state; nothing restarts from zero |
| using mattpocock/skills as well | `/setup-matt-pocock-skills` once, then the flows above | `publish` uses their tracker and labels so `/triage` and `/implement` take over; design findings go to `/improve-codebase-architecture`; `verify` adds `code-review` |

## Boundaries

- A finding whose cure is a new interface, not a deletion, is design work: `/improve-codebase-architecture` (mattpocock) or a decision for the user, not `fix`.
- Documents agents consume (SKILL.md, AGENTS.md, CLAUDE.md) are out of scope for ai-slop-prose; `writing-for-agents` (mattpocock) covers them.
- Detecting who wrote a text is not offered: the skills remove catalogued patterns and say so, because authorship detection is unreliable.
