# ai-slop-audit

A Claude Code skill that finds and removes needless complexity across a whole codebase: dead code, duplication, unused exports and dependencies, premature abstractions, pass-through wrappers, unjustified defensive checks, logic that already exists elsewhere, tautological or redundant tests, and incoherent organisation. It judges code by what it does and who reaches it, never by style, length or a guess about who wrote it. Every finding carries evidence you can rerun; every change is applied only by ID, in a small batch, behind tests.

*Versione italiana in fondo: [Italiano](#italiano).*

## Contents

- [Install](#install)
- [Modes](#modes)
- [A typical run](#a-typical-run)
- [The ledger](#the-ledger)
- [Findings](#findings)
- [Standalone or with the mattpocock skills](#standalone-or-with-the-mattpocock-skills)
- [Guardrails](#guardrails)
- [For agents](#for-agents)
- [Limits](#limits)
- [Italiano](#italiano)

## Install

This skill alone, for any agent (asks for global or project scope):

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s ai-slop-audit
```

This skill alone, as a Claude Code plugin (`--scope user`, `project` or `local`):

```sh
claude plugin install ai-slop-audit --marketplace guarriellocristianmichele/supah-skills --scope user
```

Inside a Claude Code session: `/plugin install ai-slop-audit --marketplace guarriellocristianmichele/supah-skills`. The [repository README](../../README.md#installation-1-minute-setup) covers every route, the full set, and what each scope means.

The skill needs git, and works best with the [`orchestrate`](../orchestrate/README.md) skill installed for large codebases. With [`ai-slop-design`](../ai-slop-design/README.md) installed as well, frontend modules get its duplication rules as evidence: the same class string in three components, identical CSS blocks, a colour repeated instead of a token. Once `/ai-slop-design audit` has written its ledger (`.slop-design/findings.md`), the copies whose files are all in its inventory are its findings: this audit marks them `handoff:ai-slop-design` and leaves them to `/ai-slop-design plan`, so each one is reported once; a copy in a file outside that inventory stays a finding here. Publishing to GitHub needs `gh` and a repo configured with `/setup-matt-pocock-skills`.

The skill is user-invoked (`disable-model-invocation: true`): it runs only when you type its name.

## Modes

| Command | Reads | Writes | Ends when |
|---|---|---|---|
| `/ai-slop-audit audit` | the whole repo | ledger only | every module is `scanned@<sha>` or `skipped:<reason>`; the report starts `COMPLETE: N/N` or `PARTIAL: k/N` |
| `/ai-slop-audit audit <path>` | modules under `<path>` | ledger only | the same, for that path; the report starts `SCOPED: <path>` |
| `/ai-slop-audit plan` | open findings | ledger only | every high or medium finding is in a batch or rejected with a reason; every batch has a protecting check |
| `/ai-slop-audit publish [B1 B4…]` | planned batches | issue tracker, ledger | each batch has exactly one issue, with its blocking edges |
| `/ai-slop-audit fix <IDs>` | the named findings | code, ledger | checks are no worse than baseline, removed symbols have zero references, the diff is shown |
| `/ai-slop-audit fix B2 B5`, `fix #<map>`, `fix all` | the named batches, the map issue's, or every planned one | code on an integration branch, ledger | every batch is done, failed or blocked; `verify` ran on the branch; you are asked before a pull request opens |
| `/ai-slop-audit verify` | everything since the baseline commit | ledger only | every check ran; the report starts `VERIFIED` or `FAILED: n items` |
| `/ai-slop-audit` | ledger | nothing | prints the argument hint and the current status |

`fix` accepts finding IDs (`SLOP-012`, `SLOP-012,SLOP-014`), one batch (`B3`), or a published batch's issue number (`#123`). Naming the ID is the approval: nothing else changes. A batch whose `depends-on` is not fixed yet asks first, and each fix ends with the commit to make, because the next one needs a clean tree.

Several batches at once (`fix B2 B5`, `fix #<map>` for every batch of the map issue, `fix all`) run in parallel through `orchestrate`. Each batch works in its own git worktree, installs the dependencies, runs its checks and commits; it is then merged into one integration branch, `slop/audit-<sha>`, and only after that do the batches that depend on it start. Batches that touch the same file wait for each other. A failed batch reopens its findings and holds back only its dependents. At the end `verify` runs on the integration branch and you choose whether to open one pull request that closes the done issues. Your checkout stays on its branch, and running the same command again resumes the job.

## A typical run

```text
/ai-slop-audit audit          # inventory, scan, cross-module pass, falsification
/ai-slop-audit audit          # again, if the first run ended PARTIAL: it resumes
/ai-slop-audit plan           # baseline checks, scoring, batches B1…Bn
/ai-slop-audit publish        # optional: one GitHub issue per batch
/ai-slop-audit fix B1         # one batch, tests first, then the change
/ai-slop-audit fix #124       # or by issue number
/ai-slop-audit fix all        # or every batch, in parallel, into one branch
/ai-slop-audit verify         # final regression check across all fixes
```

What each step does:

1. **audit** lists tracked files, groups them into modules, and finds the entrypoints (manifest `main`/`exports`/`bin`, framework conventions, CLI and worker scripts, files referenced by build or CI config). It runs the analyzers the project already has (knip, ts-prune, depcheck, vulture, jscpd, compiler unused flags) and treats their output as evidence, never as a verdict. It then scans each module against twelve categories, compares helpers across modules for semantic duplication, and tries to disprove every finding before keeping it.
2. **plan** discovers the project's test, lint, typecheck and build commands from its manifests and CI config, runs them, and records the baseline. It scores each finding (value × confidence against risk), records dependencies between findings, and groups them into small batches that can each be reverted on their own.
3. **fix** checks that the tree is clean and the baseline exists, reruns the finding's evidence at the current commit, runs the protecting checks (writing a characterization test first when none covers the behaviour), makes the change plus its direct fallout, and runs the checks again. If they get worse, it restores the touched files and reopens the finding.
4. **verify** runs every check against the baseline, confirms that each fix touched only its own files, that the public surface is unchanged, that no dependency was added, that every removed test has a coverage proof, and that every guard at a trust boundary still exists.

## The ledger

Everything lives in `.slop-audit/` at the repo root, added to `.git/info/exclude` so it never shows up in commits. It is the memory across sessions: close the terminal halfway through an audit and the next run continues from it.

| File | Contents |
|---|---|
| `STATUS.md` | up to 15 lines: last mode and commit, coverage, finding counts by status, next action |
| `inventory.md` | one row per module: paths, entrypoints, status (`pending`, `scanned@<sha>`, `skipped:<reason>`) |
| `findings.md` | one block per finding (schema below); IDs `SLOP-001` upward, never reused |
| `plan.md` | batches `B1` upward, with `issue: #<n>` once published |
| `checks.md` | verification commands, baseline commit, baseline results |

Finding status moves `open` → `planned` → `fixed`, and can become `stale` (the evidence no longer reproduces) or `rejected:<reason>` at any point.

## Findings

```markdown
### SLOP-012 · wrapper · confidence: high · status: open
Where: src/http/client.ts:40-58 `getJson`
Claim: forwards to `fetchJson` unchanged; 3 callers.
Evidence: commands run and the output that proves the claim.
Reach paths: which were checked, and how.
Risk: what breaks if the claim is wrong.
Fix: one-line sketch.
```

**Reach paths** are every way code gets used: static imports; dynamic imports (`import()`, computed `require`, glob loaders); string references (reflection, DI tokens, templates, routes, serialized names); entrypoints; the public API of published packages; config files; framework conventions; tests; sibling workspace packages.

| Confidence | Meaning | Can be fixed? |
|---|---|---|
| high | the evidence closes every reach path, and rerunning its commands reproduces it | yes |
| medium | static paths closed; one indirect path stays open (reflection, external consumers) | yes, behind a protecting check |
| low | a suspicion | no, until new evidence upgrades it |

The fourteen categories, each with the evidence it requires, are in [`AUDIT.md`](AUDIT.md): dead-code, unused-export / unused-file, unused-dependency, textual duplication, semantic duplication, reinvented, premature-abstraction, wrapper, defensive-check, comment-noise, residue, tautological-test, redundant-test, incoherent-organization.

## The code scanner

`scripts/codescan.py` lists the mechanical patterns in Python, JavaScript and TypeScript: placeholders, comments that restate the next line or narrate an edit, catch blocks that only rethrow, swallowed broad exceptions, runtime type checks that repeat an annotation, forwarding wrappers. The audit runs it in its tooling step and treats every hit as a candidate. Python is parsed with `ast`, so a file in syntax the interpreter can't read is reported as skipped.

```sh
python skills/ai-slop-audit/scripts/codescan.py src/**/*.py   # exit 1 when an S or M hit is open
python skills/ai-slop-audit/scripts/codescan.py src           # a folder: its source files, skipping hidden, vendored and built folders
python skills/ai-slop-audit/scripts/codescan.py rules         # every rule with its tier
```

Tiers come from reading sampled hits, not from how AI-typical a pattern is (ADR 0010): a catch that only rethrows is useless whoever wrote it. The [calibration](../../docs/research/2026-11-code-calibration-results.md) ran on 1,000 human files per language from 2022, 1,200 files per language from ten 2025 models, and 212 files from Sonnet 5.5. Sonnet 5.5 wrote almost none of these patterns; its slop is in design, which the categories above judge through reach paths.

## Standalone or with the mattpocock skills

The skill works on its own. When the repo has been set up for the [mattpocock engineering skills](https://github.com/mattpocock/skills) (the file `docs/agents/issue-tracker.md` exists), it reads their configuration and hands them the work they own. It never copies their formats or writes their files (`docs/agents/`, `.scratch/`, `.out-of-scope/`).

| | Standalone | With the mattpocock skills |
|---|---|---|
| Where `publish` writes | GitHub issues through `gh` when `origin` is on GitHub; otherwise `.slop-audit/issues/<batch>.md` | the tracker configured in `docs/agents/issue-tracker.md`, through its documented operations |
| Labels | none | the tracker's `ready-for-agent` (all findings high, a protecting check exists) or `needs-triage`, so `/triage` and `/implement #<n>` pick them up |
| Design work (a fix that needs a new interface, not a deletion) | status `handoff:design`, listed for you | status `handoff:improve-codebase-architecture` |
| A batch already built by `/implement` | | synced to `fixed` by `fix` and `publish`, never rebuilt |
| Review in `verify` | `verify`'s own checks | plus the `code-review` skill, with the issues as the spec |
| Vocabulary and decisions | `GLOSSARY.md` and `docs/adr/` when present | the same |

On both routes `publish` creates one map issue per audit (`AI slop audit @<sha>`) and one issue per batch, linked to the map, with the plan's dependencies as blocking links. Each issue says what changes, lists the done-when checks (baseline, no new dependency, justified test removals, trust-boundary guards untouched), and keeps the evidence as permalinks pinned to the scanned commit. A hidden marker prevents duplicates on reruns, and a rerun syncs the ledger with closed issues. Nothing is created before you approve the drafts.

## Guardrails

- `audit`, `plan` and `verify` never change code; only `fix` does, and only for the IDs given.
- `fix` never adds a dependency. A fix that would need one goes back to `open`.
- A test is deleted or merged only with proof that its behaviour stays asserted: the name and assertion of the test that still covers it, or before and after coverage numbers where the project measures coverage.
- Checks at a trust boundary (user input, network, environment, files, deserialization, auth, FFI) are security and stay.
- A partial scan is reported as `PARTIAL`, with the modules still pending, never as complete.

## For agents

`SKILL.md` holds the dispatch table and the shared rules; each mode's steps are in its own file (`AUDIT.md`, `PLAN.md`, `PUBLISH.md`, `FIX.md`, `VERIFY.md`). Read only the file of the mode you run. Read `.slop-audit/STATUS.md` first when it exists. Outside Claude Code, take the mode from the user's request and run `git rev-parse --short HEAD` and `git status --short` yourself, since the injected lines will appear raw.

## Limits

- Dynamic reach (reflection, string-built names, external consumers of a published API) can be narrowed but not always closed; such findings stay at medium confidence.
- The skill relies on the project's own checks. A codebase with no tests gets characterization tests written first, which take time and need your review.
- Analyzers are used only when the project already has them; none are installed.
- The code scanner reads Python, JavaScript and TypeScript only, and JavaScript with regexes, so its rules there are narrower.

## Italiano

Skill di Claude Code che trova e rimuove la complessità inutile in un'intera codebase: codice morto, duplicazioni, export e dipendenze inutilizzati, astrazioni premature, wrapper che inoltrano e basta, controlli difensivi ingiustificati, logica già presente altrove, test tautologici o ridondanti, organizzazione incoerente. Giudica il codice da cosa fa e da chi lo raggiunge, mai dallo stile, dalla lunghezza o da chi si suppone l'abbia scritto. Ogni problema ha prove rieseguibili; ogni modifica si applica solo per ID, a piccoli lotti, protetta dai test.

### Modalità

| Comando | Cosa fa |
|---|---|
| `/ai-slop-audit audit [percorso]` | inventario dei moduli e analisi in sola lettura; riprende da dove si era fermata |
| `/ai-slop-audit plan` | baseline di test, lint, typecheck e build, priorità, rischi, dipendenze, lotti `B1…Bn` |
| `/ai-slop-audit publish [lotti]` | una issue per lotto, con dipendenze e prove, dopo la tua approvazione |
| `/ai-slop-audit fix <ID>` | corregge solo gli ID indicati (`SLOP-012`, `B3` o `#123`), con test prima e verifica dopo |
| `/ai-slop-audit fix all` | lavora tutti i lotti (o `B2 B5`, o quelli della issue mappa `#<map>`) in parallelo, ognuno nel suo worktree, uniti in un integration branch nell'ordine delle dipendenze; lancia `verify` e chiede prima di aprire una pull request |
| `/ai-slop-audit verify` | controllo finale: check, regressioni, superficie pubblica, dipendenze, test rimossi |

### Scanner del codice

`scripts/codescan.py` trova i pattern meccanici in Python, JavaScript e TypeScript: placeholder, commenti che ripetono la riga sotto o raccontano una modifica, catch che rilanciano e basta, eccezioni generiche ingoiate, controlli di tipo che ripetono l'annotazione, wrapper che inoltrano. L'audit lo usa come primo passo e tratta ogni risultato come un candidato. Accetta file o cartelle; da una cartella salta quelle nascoste, vendorizzate e di build. I livelli vengono dalla lettura di campioni di risultati, non da quanto un pattern sia tipico dell'AI: un catch che rilancia e basta è inutile chiunque l'abbia scritto. Sul codice di Sonnet 5.5 questi pattern quasi non compaiono; il suo slop sta nel design, che l'audit giudica con i percorsi di raggiungibilità.

### Stato tra sessioni

Tutto vive in `.slop-audit/`, escluso da git: `STATUS.md` (riepilogo), `inventory.md` (moduli), `findings.md` (problemi), `plan.md` (lotti), `checks.md` (comandi e baseline). Una scansione interrotta riprende dal primo modulo in sospeso e viene dichiarata `PARTIAL` finché non è completa.

### Confidenza

Alta confidenza vuol dire che le prove escludono ogni modo in cui il codice può essere usato. Media vuol dire che resta aperto un uso indiretto (reflection, consumatori esterni), e il problema si corregge solo con un check che protegge il comportamento. Bassa è un sospetto, che resta fuori dal piano finché nuove prove non lo confermano.

### Da sola o con le skill di mattpocock

La skill funziona da sola: `publish` crea le issue su GitHub con `gh`, oppure file in `.slop-audit/issues/` se il repo non è su GitHub. Se nel repo è stato lanciato `/setup-matt-pocock-skills` (esiste `docs/agents/issue-tracker.md`), usa quel tracker e quelle label: `ready-for-agent` per `/implement`, `needs-triage` per `/triage`. Passa i problemi di design a `/improve-codebase-architecture` e aggiunge `code-review` alla verifica finale. Con `ai-slop-design` installata, nei moduli frontend usa le sue regole di duplicazione (classi, blocchi CSS e colori copiati) come prova. Se `/ai-slop-design audit` ha già scritto il suo registro (`.slop-design/findings.md`), le copie i cui file sono tutti nel suo inventario sono sue: questo audit le segna `handoff:ai-slop-design` e le lascia a `/ai-slop-design plan`, così ognuna compare una volta sola; una copia in un file fuori da quell'inventario resta una segnalazione di questo audit. Non copia mai i loro formati e non scrive nei loro file.

### Regole fisse

Nessuna modifica al codice fuori da `fix`, che chiede prima di lavorare un lotto con dipendenze non ancora sistemate e chiude indicando il commit da fare; nessuna dipendenza aggiunta; nessun test eliminato senza dimostrare che il suo comportamento resta verificato; i controlli ai confini di fiducia (input, rete, file, autenticazione) restano dove sono.
