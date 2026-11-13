# supah-skills

Agent skills for cleaning up what AI leaves behind, in code and in prose, plus an orchestrator that runs large jobs across parallel agents without running out of memory. Written for Claude Code first; every skill also runs on other agents that read the [Agent Skills](https://agentskills.io) format.

*Versione italiana in fondo: [Italiano](#italiano).*

| Skill | Invoked by | What it does |
|---|---|---|
| [`ai-slop-audit`](skills/ai-slop-audit/README.md) | you (`/ai-slop-audit`) | Audits a whole codebase for dead code, duplication, needless abstractions, wrappers, unjustified defensive checks and tautological tests. Every finding carries reproducible evidence and a confidence level. Fixes are applied only by ID, in small verified batches, and can be published as GitHub issues. |
| [`ai-slop-prose`](skills/ai-slop-prose/README.md) | the agent, or you | Finds the patterns that make English and Italian prose read as machine-written (negative parallelism, dashes, inflated vocabulary, false suspense, chat leftovers, wrong punctuation) with a deterministic scanner, then rewrites each one in the author's voice. |
| [`orchestrate`](skills/orchestrate/README.md) | the agent, or other skills | Splits a job into units and runs them inline or on parallel subagents sized to free RAM, with per-unit checkpoints, shedding under memory pressure and resume across sessions. |

## Install

Pick **one** route per agent. Installing the same skills twice (for example as a plugin and through skills.sh) leaves the agent with every skill twice.

### Claude Code (updates itself)

```bash
claude plugin marketplace add guarriellocristianmichele/supah-skills
claude plugin install supah-skills@supah
```

### Codex and GitHub Copilot CLI (plugin marketplace)

Both read the same `.claude-plugin/` manifests.

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
gemini skills install https://github.com/guarriellocristianmichele/supah-skills.git --path skills
```

Run the same command again to update. Add `--scope workspace` to install into the current project instead of your user folder. On accounts where Gemini CLI has been replaced by Antigravity CLI, use skills.sh with `-a antigravity`.

### Every other agent, or editable copies (skills.sh)

```bash
npx skills@latest add guarriellocristianmichele/supah-skills            # asks which agents and skills
npx skills@latest add guarriellocristianmichele/supah-skills -a cursor  # preselect an agent
npx skills@latest add guarriellocristianmichele/supah-skills --skill ai-slop-prose
```

Add `-g` to install for your user instead of the current project. skills.sh keeps one copy in `.agents/skills/` and links each agent's folder to it. Update with `npx skills@latest update`, and run `add` again to pick up skills added since.

### From a local clone

Link a skill folder into the agent's skill directory. Claude Code reads `~/.claude/skills/`. Most other agents (Codex, Copilot, Gemini CLI, Cursor, OpenCode, Amp, Goose, Junie, Pi, Factory, Qwen Code, Roo) also read the shared `~/.agents/skills/`; Kiro, Cline and Continue use only their own folders. For Claude Code:

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

Scegli un solo canale per agente: installare due volte le stesse skill le duplica.

| Agente | Comandi | Aggiornamento |
|---|---|---|
| Claude Code | `claude plugin marketplace add guarriellocristianmichele/supah-skills`, poi `claude plugin install supah-skills@supah` | automatico |
| Codex, Copilot CLI | gli stessi due passaggi con `codex plugin …` o `copilot plugin …`, come nella sezione [Install](#install) | automatico |
| Gemini CLI | `gemini skills install https://github.com/guarriellocristianmichele/supah-skills.git --path skills` | rilanciando il comando |
| Tutti gli altri | `npx skills@latest add guarriellocristianmichele/supah-skills`, con `-a <agente>` per sceglierlo subito e `--skill <nome>` per una sola skill | `npx skills@latest update` |

### Requisiti

Python 3.8 o superiore per gli script (solo libreria standard), git per `ai-slop-audit`. Facoltativi: `gh` e le skill di mattpocock, per pubblicare i risultati dell'audit come issue GitHub.

### Compatibilità

Su Claude Code le skill usano sostituzioni (`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`), output di comandi caricato all'avvio e subagent in background. Ogni skill spiega in una riga come un altro agente deve risolverle da solo. Senza subagent in background, `orchestrate` lavora in sequenza con gli stessi checkpoint.

### Licenza

[MIT](LICENSE)
