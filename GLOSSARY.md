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
The `.slop-audit/` directory that holds an audit's state across sessions; the single source of truth for findings and batches.
_Avoid_: cache, report, state file

**Batch**:
A small group of findings in one area and one category, fixed and reverted together, and published as one issue.
_Avoid_: ticket (the tracker's word), PR, chunk

**Fallout**:
Imports, types and exports that become unused because of a fix, removed with it.
_Avoid_: cleanup, side effects

**Trust boundary**:
A point where data enters from outside the code's control (user input, network, environment, files, deserialization, auth); checks there are security and stay.
_Avoid_: edge, input layer

**Handoff**:
A finding whose cure is a new interface rather than a removal, passed to design work instead of being fixed.
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
