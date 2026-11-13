# supah-skills

Agent skills for cleaning up what AI leaves behind, in code and in prose, plus an orchestrator that runs large jobs across parallel agents without running out of memory. Written for Claude Code first; every skill also runs on other agents that read the [Agent Skills](https://agentskills.io) format.

*Versione italiana in fondo: [Italiano](#italiano).*

| Skill | Invoked by | What it does |
|---|---|---|
| [`ai-slop-audit`](skills/ai-slop-audit/README.md) | you (`/ai-slop-audit`) | Audits a whole codebase for dead code, duplication, needless abstractions, wrappers, unjustified defensive checks and tautological tests. Every finding carries reproducible evidence and a confidence level. Fixes are applied only by ID, in small verified batches, and can be published as GitHub issues. |
| [`ai-slop-prose`](skills/ai-slop-prose/README.md) | the agent, or you | Finds the patterns that make English and Italian prose read as machine-written (negative parallelism, dashes, inflated vocabulary, false suspense, chat leftovers, wrong punctuation) with a deterministic scanner, then rewrites each one in the author's voice. |
| [`orchestrate`](skills/orchestrate/README.md) | the agent, or other skills | Splits a job into units and runs them inline or on parallel subagents sized to free RAM, with per-unit checkpoints, shedding under memory pressure and resume across sessions. |

## Install

Every route asks for, or takes, one decision first: **where** the skills go.

| Scope | Where the skills live | Who gets them |
|---|---|---|
| Global | your home folder | you, in every project |
| Project | inside the repository, committed with it | everyone who works on the repository |
| Local (Claude Code only) | inside the repository, kept out of git | you, in this repository only |

Then pick **one** route per agent. Installing the same skills twice (for example as a plugin and through skills.sh) leaves the agent with every skill twice.

### Any agent, with a prompt for the scope (skills.sh)

```bash
npx skills@latest add guarriellocristianmichele/supah-skills
```

Run with no flags, it asks three questions: which skills, which agents, and **Installation scope** (*Project*: in the current directory, committed with your project; *Global*: in your home directory, for all projects). It knows the folders of Claude Code, Codex, Copilot, Gemini CLI, Cursor, OpenCode, Windsurf, Amp, Goose, Cline, Roo, Kiro, Junie, Pi, Factory, Qwen Code, Continue and more.

To answer the questions on the command line instead:

| Goal | Command |
|---|---|
| Global, chosen agents | `npx skills@latest add guarriellocristianmichele/supah-skills -g -a claude-code codex` |
| Project, chosen agents | `npx skills@latest add guarriellocristianmichele/supah-skills -a cursor` |
| One skill only | add `-s ai-slop-prose` |
| No prompts at all | add `-y` (scope then defaults to project unless `-g` is given) |

skills.sh keeps one copy in `.agents/skills/` (or `~/.agents/skills/` when global) and links each agent's folder to it; `--copy` writes real copies instead. Update with `npx skills@latest update` (it asks for the scope again; `-g` or `-p` answers it), and run `add` again to pick up skills added since.

### Claude Code plugin (updates itself)

The plugin route updates automatically. Choose the scope with `--scope`; the command does not ask, and defaults to `user`.

| Scope | Commands |
|---|---|
| Global | `claude plugin install supah-skills --marketplace guarriellocristianmichele/supah-skills --scope user` |
| Project | `claude plugin marketplace add guarriellocristianmichele/supah-skills --scope project`, then `claude plugin install supah-skills@supah --scope project` |
| Local | the same two commands with `--scope local` |

Project scope writes the marketplace and the plugin into `.claude/settings.json`: commit that file so everyone on the repository gets the same skills. Local scope writes `.claude/settings.local.json`, which stays out of git.

### Codex and GitHub Copilot CLI plugin (global)

Both read the same `.claude-plugin/` manifests. Their plugin commands install for your user only; for a project install, use skills.sh, whose `.agents/skills/` folder both agents read.

```bash
codex plugin marketplace add guarriellocristianmichele/supah-skills
codex plugin add supah-skills@supah
```

If your Codex version has no `plugin add` command, install `supah-skills` from the app's Plugins Directory after adding the marketplace.

```bash
copilot plugin marketplace add guarriellocristianmichele/supah-skills
copilot plugin install supah-skills@supah
```

### Gemini CLI (manual updates)

```bash
gemini skills install https://github.com/guarriellocristianmichele/supah-skills.git --path skills --scope user        # global
gemini skills install https://github.com/guarriellocristianmichele/supah-skills.git --path skills --scope workspace   # project
```

Run the same command again to update. On accounts where Gemini CLI has been replaced by Antigravity CLI, use skills.sh with `-a antigravity`.

### From a local clone

Link a skill folder into the agent's skill directory: the user folder for a global install, the same path inside the repository for a project install. Claude Code reads `~/.claude/skills/` (global) and `.claude/skills/` (project). Most other agents (Codex, Copilot, Gemini CLI, Cursor, OpenCode, Amp, Goose, Junie, Pi, Factory, Qwen Code, Roo) also read the shared `~/.agents/skills/` and `.agents/skills/`; Kiro, Cline and Continue use only their own folders. Global install for Claude Code:

```bash
ln -s "$PWD/skills/ai-slop-prose" ~/.claude/skills/ai-slop-prose                  # macOS, Linux
```

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-slop-prose" -Target "$PWD\skills\ai-slop-prose"   # Windows
```

## Requirements

- **Python 3.8 or newer** on `PATH`, for the scripts inside `ai-slop-prose` (scanner) and `orchestrate` (memory gauge). Standard library only: nothing to install with pip. On Windows, install it from [python.org](https://www.python.org/downloads/) or with `winget install Python.Python.3.13`.
- **git**, for `ai-slop-audit` and for the state that `orchestrate` keeps out of version control.
- Optional: the [`gh`](https://cli.github.com) CLI and [mattpocock/skills](https://github.com/mattpocock/skills) with `/setup-matt-pocock-skills` run once per repo, to publish audit findings as GitHub issues.

## How the skills fit together

- `ai-slop-audit` hands its module scan to `orchestrate`, so a large codebase is scanned in parallel and a scan stopped halfway resumes where it stopped.
- `ai-slop-prose` hands sweeps of more than three files to `orchestrate` in the same way.
- Without `orchestrate` installed, both skills run the same work in sequence.
- `ai-slop-audit` speaks the conventions of the mattpocock engineering skills: its `publish` mode writes issues that `/triage` can label and `/implement` can build from, and its `verify` mode hands the result to `/code-review` when that skill is available.

## Compatibility

The skills use Claude Code features where they help: `$ARGUMENTS` and `${CLAUDE_SKILL_DIR}` substitution, command output injected at load time, background subagents, and `disable-model-invocation` for skills you start by hand. Each skill says, in one line near its top, how another agent should resolve these by itself. Consequences outside Claude Code:

- `disable-model-invocation: true` (`ai-slop-audit`) is honoured by Cursor, OpenCode, Pi, Factory, Qwen Code and VS Code. Agents that ignore the field, such as Codex and Gemini CLI, may offer the skill on their own.
- Without background subagents, `orchestrate` runs jobs inline, with the same checkpoints and the same resume file.
- Uploading a skill to claude.ai or the Skills API fails on frontmatter keys other than `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`. Delete the other keys from the uploaded copy.
- No agent other than Claude Code substitutes `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}`; the skills tell the agent what those stand for.

## Development

```bash
claude plugin validate . --strict                         # check the plugin manifests
python skills/ai-slop-prose/scripts/scan.py rules         # list every prose rule
python skills/ai-slop-prose/scripts/scan.py README.md     # sweep a README before committing it
python skills/orchestrate/scripts/mem.py status           # see the RAM budget for parallel agents
```

When adding a skill, put it in `skills/<name>/` and list it in `.claude-plugin/plugin.json`. Bump `version` in `plugin.json` on every release: managed installs update only when it changes.

## License

[MIT](LICENSE)

## Italiano

Skill per agenti che ripuliscono quello che l'AI lascia nel codice e nei testi, più un orchestratore che esegue lavori grandi su agenti in parallelo senza esaurire la memoria. Pensate prima di tutto per Claude Code, funzionano anche sugli altri agenti che leggono il formato [Agent Skills](https://agentskills.io).

| Skill | Chi la avvia | Cosa fa |
|---|---|---|
| `ai-slop-audit` | tu (`/ai-slop-audit`) | Analizza un'intera codebase in cerca di codice morto, duplicazioni, astrazioni inutili, wrapper, controlli difensivi ingiustificati e test tautologici. Ogni problema ha prove riproducibili e un livello di confidenza. Le correzioni si applicano solo per ID, a piccoli lotti verificati, e si possono pubblicare come issue GitHub. |
| `ai-slop-prose` | l'agente, oppure tu | Trova gli schemi che fanno sembrare scritto da una macchina un testo inglese o italiano (parallelismi negativi, trattini, lessico gonfiato, falsa suspense, residui di chat, punteggiatura sbagliata) con uno scanner deterministico, poi li riscrive nella voce dell'autore. |
| `orchestrate` | l'agente, oppure altre skill | Divide un lavoro in unità e le esegue inline o su subagent paralleli dimensionati sulla RAM libera, con checkpoint per unità, arresto ordinato quando la memoria scarseggia e ripresa tra sessioni. |

### Installazione

La prima scelta è dove installare:

| Ambito | Dove finiscono le skill | Chi le usa |
|---|---|---|
| Globale | nella tua cartella utente | tu, in tutti i progetti |
| Progetto | dentro il repository, nel commit | chiunque lavori sul repository |
| Locale (solo Claude Code) | dentro il repository, fuori da git | tu, solo in questo repository |

Poi scegli un solo canale per agente: installare due volte le stesse skill le duplica.

| Canale | Globale | Progetto | Aggiornamento |
|---|---|---|---|
| skills.sh, qualsiasi agente | `npx skills@latest add guarriellocristianmichele/supah-skills` chiede l'ambito; `-g` lo fissa a globale | lo stesso comando, risposta *Project*, oppure senza `-g` | `npx skills@latest update` |
| Plugin Claude Code | `claude plugin install supah-skills --marketplace guarriellocristianmichele/supah-skills --scope user` | `claude plugin marketplace add … --scope project`, poi `claude plugin install supah-skills@supah --scope project`, e commit di `.claude/settings.json` | automatico |
| Plugin Codex, Copilot CLI | `codex plugin …` o `copilot plugin …`, come nella sezione [Install](#install) | non disponibile: usa skills.sh | automatico |
| Gemini CLI | `gemini skills install <repo>.git --path skills --scope user` | lo stesso con `--scope workspace` | rilanciando il comando |

Il comando di skills.sh senza opzioni chiede quali skill, quali agenti e l'ambito (*Project* o *Global*). Il plugin di Claude Code non chiede nulla: l'ambito si sceglie con `--scope` e, se manca, vale `user`.

### Requisiti

Python 3.8 o superiore per gli script (solo libreria standard), git per `ai-slop-audit`. Facoltativi: `gh` e le skill di mattpocock, per pubblicare i risultati dell'audit come issue GitHub.

### Compatibilità

Su Claude Code le skill usano sostituzioni (`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`), output di comandi caricato all'avvio e subagent in background. Ogni skill spiega in una riga come un altro agente deve risolverle da solo. Senza subagent in background, `orchestrate` lavora in sequenza con gli stessi checkpoint.

### Licenza

[MIT](LICENSE)
