# supah-skills

Agent skills that remove what AI leaves behind in code and prose, and run large jobs across parallel agents within the machine's memory.

## Language

### Code audit

**Slop**:
Complexity the code's behaviour does not need, judged by what the code does and who reaches it.
_Avoid_: bad code, AI code, cruft

**Finding**:
One claim of slop with its location, reproducible evidence, the reach paths checked, a confidence level and a status.
_Avoid_: issue (that is the tracker's word), smell, problem

**Reach path**:
Any way code gets used: static or dynamic import, string reference, entrypoint, public API, config, framework convention, test, sibling package.
_Avoid_: usage, caller (a caller is one kind of reach path)

**Ledger**:
The directory that holds an audit's state across sessions (`.slop-audit/` for code, `.slop-design/` for design); the single source of truth for findings and batches.
_Avoid_: cache, report, state file

**Batch**:
A small group of findings fixed and reverted together, and published as one issue: in a code plan, one category in one area; in a design plan, a token/component, surface or handoff batch, worked by `sweep B<n>` (a handoff batch by `craft <surface>`).
_Avoid_: ticket (the tracker's word), PR, chunk

**Map issue**:
The one issue per plan that lists every published batch in order with its blockers, under the plan's coverage and finding counts; each batch's issue links to it.
_Avoid_: epic, tracking issue

**Issue marker**:
The hidden comment that ends a published issue and names the skill, the batch and its findings (`<!-- ai-slop-design batch B4 · DS-021 -->`), by which a re-run publish finds the issue again instead of opening a second.
_Avoid_: tag, label (labels are the tracker's)

**Fallout**:
Imports, types and exports that become unused because of a fix, removed with it.
_Avoid_: cleanup, side effects

**Trust boundary**:
A point where data enters from outside the code's control (user input, network, environment, files, deserialization, auth); checks there are security and stay.
_Avoid_: edge, input layer

**Handoff**:
Work passed to whoever owns its cure instead of being patched where it was found. Three senses, told apart by where the word sits:
- _Status_ (`handoff:<skill>` on a code audit finding): the cure is a new interface rather than a removal, so the finding goes to design work (`handoff:improve-codebase-architecture`, `handoff:design`); or another skill owns it, as frontend duplication is marked `handoff:ai-slop-design` once the design audit's ledger exists and its inventory holds every file of the group.
- _Keep reason_ (`handoff` after a `chosen` verdict in a design keep file): the whole page sits in a lane and needs a new direction from `craft <surface>`, not a patch.
- _Batch kind_ (`handoff` in a design plan's batch heading): one lane and every surface in it, worked by a restyle; see **Handoff batch**.
_Avoid_: rejection, deferral

### Prose

**Tell**:
A pattern whose frequency marks text as machine-written, whatever the text says.
_Avoid_: AI-ism, slop word, red flag

**Tier**:
How much evidence a tell needs before rewriting: S on one sighting, M unless a keep reason applies, W only when its density metric is flagged.
_Avoid_: severity, level

**Sweep**:
One pass over a text, category by category, that resolves every scanner hit and reads for the tells no regex sees.
_Avoid_: scan (the scanner's step within a sweep), lint, check

**Keep file**:
A TSV of hits and metrics deliberately left in the text, each with a reason (`quote`, `voice`, `literal`, `term`, `dialogue`).
_Avoid_: allowlist, ignore file

### Design

**Reflex**:
A design choice that appears whatever the subject: the default a model reaches for on any brief in the category. Wrong only when nothing (brief, brand, content) chose it.
_Avoid_: AI look, slop style, cliché

**Direction**:
The plan a craft run commits to before writing code: palette, type roles, layout concept, one memorable element, one motion moment, each with the reason it fits the subject.
_Avoid_: theme, style, moodboard

**Lane**:
A saturated aesthetic family a page can fall into even when it avoids every catalogued reflex (cream + serif + clay; near-black + one neon accent; broadsheet hairlines; neo-brutalist offset shadows; the SaaS card kit).
_Avoid_: trend, aesthetic, vibe

**Surface**:
A route or page plus the components only it reaches; components reached by several surfaces, or by none a static read can find, form the `shared` unit, so every frontend file belongs to exactly one unit. The unit an audit judges and counts coverage by.
_Avoid_: page (one surface may render several), screen, view

**Reconcile**:
The step of a re-run design audit that compares a fresh scan with the ledger's findings and keep file: a finding whose hit is gone is fixed, one still there is open, one a keep line now covers is resolved, and a hit no finding or keep line covers is new. It replaces a separate verify mode.
_Avoid_: verify, diff, rescan (the rescan is its input)

**Restyle**:
A craft run on an existing surface (`craft <surface>`), usually a sweep's or plan's `handoff`: the brief is read from the page, content and behaviour stay unchanged, and the direction is checked against the lane the page sat in.
_Avoid_: redesign, reskin, makeover

**Token/component batch**:
A design plan's batch that replaces copies across surfaces (repeated class strings, duplicate CSS blocks, untokened colours) with one token or component, in three steps: expand adds it, migrate swaps it in a few surfaces at a time, contract removes what the copies left. Planned before every other kind.
_Avoid_: refactor, design-system ticket

**Surface batch**:
A design plan's batch holding one surface's reflexes, judgment-only finds and copy, fixed in one sweep.
_Avoid_: page fix, route ticket

**Handoff batch**:
A design plan's batch naming one lane and every surface that sits in it, worked by a restyle instead of patches.
_Avoid_: redesign ticket, lane fix

### Buyer panel

**Panel**:
A fixed set of synthetic buyers for one idea, built once from a segment plan and kept in `.buyer-panel/<slug>/`; a generator of hypotheses, never market evidence.
_Avoid_: survey, focus group, sample (they imply real people)

**Buyer**:
One model-written person of a panel: segment, budget, habits, current solution, last spend, a need that would make them look for something new and one honest objection, unchanged across rounds.
_Avoid_: persona, respondent, customer (respondent stays only inside quoted research note headings)

**Round**:
One offer at one price shown to the panel's buyers in fresh contexts, with its answers, scores, numbers and report in `rounds/<label>/`. Several rounds run together for one question form a series (the price series `p<n>`).
_Avoid_: run, wave, iteration

**Anchor**:
One of five fixed statements of purchase intent, from "definitely not" to "definitely", that the judge matches a buyer's free reaction to; intent is never asked as a number.
_Avoid_: rating, score label, Likert point

**Grounding**:
Comparing what real people did (interviews, a smoke test, pre-sales) with what the panel predicted for the same offer, and storing the ratio in the project's `.buyer-panel/grounding.jsonl` so later rounds of every panel show a corrected figure.
_Avoid_: validation, calibration (calibration means the scanners' corpora here)

### Orchestration

**Job**:
Work split into independent units, run inline or across parallel workers.
_Avoid_: task, workflow, run

**Unit**:
The smallest piece of a job; it needs no other unit's output.
_Avoid_: item, chunk, step

**Checkpoint**:
The `<!-- unit:<id> done -->` marker a worker writes after finishing a unit; it outranks every other record of progress.
_Avoid_: savepoint, progress flag

**Watchdog**:
The background script that measures free memory and writes stop flags when it falls below the reserve.
_Avoid_: monitor, supervisor

### Distribution

**Scope**:
Where an installed skill lives: global (the user's home folder), project (inside the repository, committed) or local (inside the repository, kept out of git; Claude Code only).
_Avoid_: level, target

**Hook plugin**:
A Claude Code plugin under `plugins/<name>` that holds hooks and no skill; installed only through the plugin marketplace.
_Avoid_: extension, add-on

**Rules file**:
The short text a hook plugin injects at session start (`hooks/rules.md` in slop-guard); every line costs tokens in every session.
_Avoid_: prompt, system prompt, reminder
