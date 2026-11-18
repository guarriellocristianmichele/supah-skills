# orchestrate

A Claude Code skill for jobs that split into many independent units (modules, files, documents). It decides on its own whether to work inline or on parallel subagents, based on the RAM actually free on the machine. When memory runs short it stops some agents, keeps every unit they finished, and resumes them later, in the same session or the next one.

Other skills in this repository use it: `ai-slop-audit` hands it the module scan, `ai-slop-prose` and `ai-slop-design` hand it sweeps of more than three files, and `ai-slop-design` builds craft variants with it.

*Versione italiana in fondo: [Italiano](#italiano).*

## Contents

- [Install](#install)
- [Usage](#usage)
- [How it works](#how-it-works)
- [Graph jobs](#graph-jobs)
- [When memory runs short](#when-memory-runs-short)
- [State on disk](#state-on-disk)
- [mem.py reference](#mempy-reference)
- [For agents](#for-agents)
- [Limits](#limits)
- [Italiano](#italiano)

## Install

This skill alone, for any agent (asks for global or project scope):

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s orchestrate
```

This skill alone, as a Claude Code plugin (`--scope user`, `project` or `local`):

```sh
claude plugin install orchestrate --marketplace guarriellocristianmichele/supah-skills --scope user
```

Inside a Claude Code session: `/plugin install orchestrate --marketplace guarriellocristianmichele/supah-skills`. The [repository README](../../README.md#installation-1-minute-setup) covers every route, the full set, and what each scope means.

Requirements: Python 3.10 or newer on `PATH` (standard library only) and a git repository for the state directory.

## Usage

The skill is model-invoked: the agent loads it when a task fans out over many units, and other skills call it by name. You can start it yourself too:

```text
/orchestrate
/orchestrate docs-sweep
```

A job is defined by six fields. The skill asks for any that are missing, and saves them in the job's `job.md`, so running the same job again, even after `/clear`, does not ask twice.

| Field | Meaning |
|---|---|
| name | identifies the job and its state directory |
| units | the work list; a unit may depend only on its blockers (see [Graph jobs](#graph-jobs)) |
| brief | what to do for one unit |
| done criterion | when one unit is finished |
| profile | `light` for reading and searching, `build` for tests, typecheck and builds |
| allowed writes | where workers may write besides their own work file |

## How it works

1. **Resume.** If the job's state already exists, interrupted work is recovered. Workers still marked `running` from an earlier session are treated as stopped; units with a checkpoint whose result meets the done criterion count as done. A stopped worker's units without a checkpoint go back to the queue; the ones it finished stay done.
2. **Size.** `mem.py status` measures free RAM and computes the slots: (free RAM − reserve) ÷ RAM per agent, capped at 6. With one slot or fewer, or three units or fewer left, the skill works inline, as a worker named `inline` that writes its checkpoints to `work/inline.md`.
3. **Dispatch.** Workers start in the background, then a watchdog starts, also in the background, and checks memory every 10 seconds. The watchdog spends no tokens: its exit is what wakes the orchestrator.
4. **React.** When a worker finishes, the units it left without a checkpoint go back to the queue (a unit that comes back twice is marked `failed`) and free slots are refilled. When the watchdog reports pressure, the most recently started workers are stopped. When it cannot read `state.json`, the orchestrator writes the file again and restarts it; a second failure stops new dispatches, and the job ends partial once the running workers finish.
5. **Merge.** Results are joined in unit order, and the measured RAM per agent is saved for the next run.

The job is complete when every unit is `done` or `failed`, every stopped worker has been resumed or had nothing left to resume, and no worker is running. Otherwise the skill reports `PARTIAL: k/N units`, and invoking the same job again continues from there.

## Graph jobs

Some jobs change code in an order: the batches of an `/ai-slop-audit` or `/ai-slop-design` plan, where a batch can start only after the batches it depends on have landed. The caller gives each unit its blockers and the files it may edit, plus an integration branch, a setup command for a fresh checkout (an install from the lockfile, or none), the checks to run after each merge, and what to record after it.

- `scripts/graph.py frontier --state <dir>` reads `units.md` and prints the units that can start now, the ones still waiting and on what, and the ones that can never start because a blocker failed. Two units that edit the same file run one after the other, the earlier one first, unless a blocker already orders them. A cycle or a blocker that does not exist stops the job before anything starts.
- Each unit runs in its own git worktree, branched from the tip of the integration branch, and ends with one commit. When it finishes, the orchestrator merges it into the integration branch (`--no-ff`) and runs the checks there; the units waiting on it start from the new tip. A merge conflict or red checks after the merge send the unit back once; the second time it is `failed`.
- A unit whose own checks fail is `failed`, and the units that depend on it are `blocked`; everything else goes on. Your checkout never changes branch: merges happen in a worktree of the integration branch, under the job's state directory.

## When memory runs short

Stopping happens in two steps:

1. The watchdog creates `stop/<worker>` for the most recently started workers, which have the least work to lose. Each worker checks for this file before starting a unit, and exits after saving the last unit it finished.
2. If a flagged worker is still running after 3 minutes and memory is still below the reserve, the orchestrator ends it with TaskStop. At most the unit in progress is lost, and it goes back to the queue.

Every stopped worker leaves a block in `STOPPED_AGENTS_WORK.md`:

```markdown
## w3 · stopped 2026-11-13T15:02 · memory: 1.9 GB free < 2.4 GB reserve
Brief: briefs/w3.md
Done: mod-api, mod-auth
Remaining: mod-billing, mod-cli
Checkpoint: work/w3.md
Status: open
```

On resume, a new worker gets the same brief over the remaining units that still have no checkpoint, and the block becomes `Status: resumed as w7`. A block with no such unit left becomes `Status: closed`.

## State on disk

The directory is `<caller state dir>/orchestrator/<job>/`, or `.orchestrator/<job>/` at the repo root. It is added to `.git/info/exclude`, so it stays out of git without touching `.gitignore`.

| File | Contents |
|---|---|
| `job.md` | the job's brief, done criterion, profile and allowed writes, read again on every resume |
| `state.json` | session, profile, RAM per agent, reserve, free RAM at the first dispatch and the most workers run at once (the inputs of the calibration), the list of workers and their status |
| `units.md` | status of every unit: `pending`, `assigned:<worker>`, `done`, `failed:<reason>` |
| `briefs/<worker>.md` | the exact prompt each worker received, reused on resume |
| `work/<worker>.md` | the worker's output; each finished unit ends with `<!-- unit:<id> done -->` |
| `stop/<worker>` | stop flag written by the watchdog |
| `STOPPED_AGENTS_WORK.md` | register of stopped workers and the work they left |

The `<!-- unit:<id> done -->` marker is the checkpoint. When `units.md` and the work files disagree, the marker wins, as long as the result it closes meets the done criterion.

## mem.py reference

```text
python scripts/mem.py status [--profile light|build] [--per-agent MB] [--reserve MB] [--max N]
python scripts/mem.py watch --state DIR [--interval S] [--grace S]
```

`status` prints one JSON object: `avail_mb`, `total_mb`, `reserve_mb`, `per_agent_mb`, `slots`.

```json
{"avail_mb": 6144, "total_mb": 16311, "reserve_mb": 2446, "per_agent_mb": 400, "slots": 6}
```

`watch` reads `DIR/state.json` and exits with one of these codes:

| Exit code | Event | Printed JSON |
|---|---|---|
| 0 | no worker is running | `{"event": "idle", "min_avail_mb": …}` |
| 1 | `state.json` missing, half-written or not a job state, after a few reads 0.2 seconds apart | `{"event": "error", "error": …}` |
| 3 | memory below the reserve; stop flags written | `{"event": "pressure", "stop": [ids], "avail_mb": …, "reserve_mb": …}` |
| 4 | flagged workers still running after `--grace` seconds, pressure persisting | `{"event": "hard-stop", "workers": [ids], "avail_mb": …}` |

| Setting | Default |
|---|---|
| reserve | the larger of 2 GB and 15% of total RAM |
| RAM per agent | 400 MB (`light`), 1500 MB (`build`), replaced by the measured value after the first run |
| `--max` | 6 workers |
| `--interval` | 10 seconds |
| `--grace` | 180 seconds |

Free RAM is read from `GlobalMemoryStatusEx` on Windows, `MemAvailable` in `/proc/meminfo` on Linux, and `vm_stat` (free + inactive + speculative pages) on macOS.

## For agents

1. Run `mem.py status` before dispatching; never size the pool from the unit count.
2. Give every worker the brief template from `SKILL.md` unchanged, including the stop-file check before each unit and the done marker after it.
3. Start exactly one watchdog per job, in the background, and react to its exit code.
4. Treat the done marker as the only proof that a unit finished.
5. Outside Claude Code, use the agent's own subagent and background-process mechanisms; without background subagents, run the job inline with the same checkpoints.

## Limits

- In Claude Code, subagents run inside the same process. What weighs on RAM is the commands they launch (tests, compilers, analyzers), which is why the skill measures memory instead of estimating it, and why the `build` profile reserves far more.
- Every parallel worker spends tokens. The cap of 6 limits the cost; change it with `--max`.
- On Windows, available RAM includes the standby cache, as in Task Manager. Heavy software running alongside lowers the slots accordingly.
- Agents from a closed session cannot be revived; resuming starts a new worker with the same brief.

## Italiano

Skill di Claude Code per lavori che si dividono in tante unità indipendenti (moduli, file, documenti). Decide da sola se lavorare inline o con subagent in parallelo, in base alla RAM davvero libera. Quando la memoria scarseggia ferma alcuni agenti senza perdere il lavoro fatto e li riprende più tardi, anche in una sessione successiva.

### Come funziona

1. Ripresa: recupera il lavoro interrotto; gli agenti rimasti `running` da una sessione precedente contano come fermati, e un'unità conta come fatta solo se il suo checkpoint rispetta il criterio di completamento. Brief, criterio, profilo e scritture permesse stanno in `job.md`, quindi dopo `/clear` non li richiede.
2. Dimensionamento: `mem.py status` calcola gli slot come (RAM libera − riserva) ÷ RAM per agente, al massimo 6. Con uno slot o meno, oppure con tre unità o meno, lavora inline, come worker `inline` con i checkpoint in `work/inline.md`.
3. Avvio: lancia i worker e un watchdog in background, che controlla la memoria ogni 10 secondi.
4. Reazione: rimette in coda le unità che un worker ha lasciato senza checkpoint (alla seconda volta diventano `failed`) e riempie gli slot liberati; quando la memoria scende sotto la riserva ferma i worker avviati per ultimi.
5. Unione: unisce i risultati e salva la RAM misurata per agente per la volta successiva.

### Lavori a grafo

Alcuni lavori cambiano il codice in un ordine preciso: i lotti di un piano di `/ai-slop-audit` o `/ai-slop-design`, dove un lotto parte solo dopo quelli da cui dipende. Chi chiama indica per ogni unità i blocchi e i file che può modificare, più un integration branch, il comando di setup per un checkout nuovo, i controlli da lanciare dopo ogni merge e cosa registrare. `scripts/graph.py frontier` calcola le unità che possono partire, quelle in attesa e quelle bloccate da un fallimento; due unità che modificano lo stesso file girano una dopo l'altra, e un ciclo ferma il lavoro prima di partire. Ogni unità lavora in un worktree git suo e finisce con un commit; l'orchestratore fa il merge nell'integration branch, lancia i controlli e solo dopo fa partire chi aspettava. Il tuo checkout resta sul suo branch.

### Memoria piena

Il watchdog crea `stop/<worker>`: il worker termina dopo aver salvato l'ultima unità completata. Se dopo 3 minuti è ancora attivo, l'orchestratore lo chiude con TaskStop e rimette in coda solo l'unità in corso. Ogni worker fermato lascia un blocco in `STOPPED_AGENTS_WORK.md` con lavoro fatto, unità rimanenti e checkpoint; alla ripresa un nuovo worker riparte dalle unità rimanenti ancora senza checkpoint, e un blocco senza più nulla da fare diventa `Status: closed`.

### Codici di uscita di `mem.py watch`

`0` nessun worker attivo; `1` `state.json` mancante, scritto a metà o non valido (l'orchestratore lo riscrive e riavvia il watchdog); `3` memoria sotto la riserva, flag di stop scritti; `4` worker segnalati ancora attivi dopo il periodo di grazia.

### Limiti

I subagent di Claude Code girano nello stesso processo: la RAM la consumano i comandi che lanciano, per questo la skill la misura invece di stimarla. Ogni worker in parallelo consuma token; il tetto di 6 si cambia con `--max`.
