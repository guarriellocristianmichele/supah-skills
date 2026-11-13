# Supah Skills

[![skills.sh](https://skills.sh/b/guarriellocristianmichele/supah-skills)](https://skills.sh/guarriellocristianmichele/supah-skills)

Agent skills for cleaning up after AI: the dead code and needless layers it leaves in a codebase, and the tics it leaves in prose.

Agents write a lot, fast. Some of it is excellent, and some of it is slop: a wrapper around a wrapper, a test that checks the mock it just configured, a README that `delves into` a `rich tapestry`. These skills find that slop with evidence instead of vibes, and remove it in small steps that keep behaviour, meaning and voice intact.

They're built for Claude Code first and work with any agent that reads the [Agent Skills](https://agentskills.io) format. Take them, change them, make them yours.

*Versione italiana in fondo: [Italiano](#italiano).*

## Installation (1-minute setup)

### 1. Decide where the skills live

| Scope | Where | Who gets them |
|---|---|---|
| Global | your home folder | you, in every project |
| Project | inside the repo, committed | everyone who works on the repo |
| Local (Claude Code only) | inside the repo, kept out of git | you, in this repo only |

You'll be asked for this choice (or pass it as a flag) in the next step. Pick one route per agent: installing the same skills twice gives you every skill twice.

### 2. Get the skills

<details>
<summary><strong>Any agent</strong> (asks for the scope; manual updates)</summary>

```bash
npx skills@latest add guarriellocristianmichele/supah-skills
```

It asks which skills, which agents, and the installation scope (*Project* or *Global*). It knows the folders of Claude Code, Codex, Copilot, Gemini CLI, Cursor, OpenCode, Windsurf, Amp, Goose, Cline, Roo, Kiro, Junie, Pi, Factory, Qwen Code, Continue and more.

To answer on the command line: `-g` for global (omit it for project), `-a <agent>` to pick agents, `-s <skill>` to pick skills (for example `-s ai-slop-prose`, or `-s ai-slop-prose orchestrate`), `-y` to skip the prompts. Update with `npx skills@latest update`, and re-run `add` to pick up new skills.

</details>

<details>
<summary><strong>Claude Code</strong> (plugin; updates itself)</summary>

Global:

```bash
claude plugin install supah-skills --marketplace guarriellocristianmichele/supah-skills --scope user
```

Project (then commit `.claude/settings.json`, so everyone on the repo gets the same skills):

```bash
claude plugin marketplace add guarriellocristianmichele/supah-skills --scope project
claude plugin install supah-skills@guarriellocristianmichele --scope project
```

Local: the two project commands with `--scope local`.

One skill only: replace `supah-skills` with the skill's name. Each skill is also its own plugin in the same marketplace.

```bash
claude plugin install ai-slop-prose --marketplace guarriellocristianmichele/supah-skills --scope user
claude plugin install ai-slop-audit@guarriellocristianmichele --scope project      # after the project marketplace add above
claude plugin install orchestrate@guarriellocristianmichele --scope project
```

Pick either the full set or single skills: installing `supah-skills` and `ai-slop-prose` together loads `ai-slop-prose` twice.

</details>

<details>
<summary><strong>Codex</strong> (plugin, global; updates itself)</summary>

```bash
codex plugin marketplace add guarriellocristianmichele/supah-skills
codex plugin add supah-skills@guarriellocristianmichele
```

If your Codex has no `plugin add`, install `supah-skills` from the app's Plugins Directory. For a project install, use the *Any agent* route: Codex reads `.agents/skills/`.

</details>

<details>
<summary><strong>GitHub Copilot CLI</strong> (plugin, global; updates itself)</summary>

```bash
copilot plugin marketplace add guarriellocristianmichele/supah-skills
copilot plugin install supah-skills@guarriellocristianmichele
```

For a project install, use the *Any agent* route: Copilot reads `.agents/skills/`.

</details>

<details>
<summary><strong>Gemini CLI</strong> (manual updates)</summary>

```bash
gemini skills install https://github.com/guarriellocristianmichele/supah-skills.git --path skills --scope user        # global
gemini skills install https://github.com/guarriellocristianmichele/supah-skills.git --path skills --scope workspace   # project
```

Re-run to update. For one skill, point `--path` at its folder, for example `--path skills/ai-slop-prose`. Where Gemini CLI has been replaced by Antigravity CLI, use the *Any agent* route with `-a antigravity`.

</details>

<details>
<summary><strong>From a local clone</strong></summary>

Link a skill folder into the agent's skill directory: `~/.claude/skills/` (global) or `.claude/skills/` (project) for Claude Code, `~/.agents/skills/` or `.agents/skills/` for most other agents.

```bash
ln -s "$PWD/skills/ai-slop-prose" ~/.claude/skills/ai-slop-prose
```

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\ai-slop-prose" -Target "$PWD\skills\ai-slop-prose"
```

</details>

The scripts inside the skills need Python 3.8+ on your `PATH` (standard library only, nothing to pip install) and git. On Windows: `winget install Python.Python.3.13`.

### 3. Optional: pair with mattpocock/skills

Everything works standalone: `/ai-slop-audit publish` files GitHub issues through `gh`, or local files when the repo isn't on GitHub. If you also use [mattpocock/skills](https://github.com/mattpocock/skills), run `/setup-matt-pocock-skills` once in the repo: the audit then publishes to the tracker and labels it configured, so `/triage` and `/implement` pick the issues up, and hands design work to `/improve-codebase-architecture`. The two sets never write each other's files.

### 4. That's it.

Try `/ai-slop-audit audit` on a codebase, or ask your agent to write something. `ai-slop-prose` steps in on its own.

## Why these skills exist

I built these to fix the failure modes I kept hitting with Claude Code, Codex and the rest.

### #1: The code works, but nobody can change it

> "Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."
>
> Antoine de Saint-Exupéry, *Wind, Sand and Stars*

**The Problem**: Agents add. They wrap a function to "keep things flexible", guard a value that can't be null, write a test that asserts the mock returns what it was told to return, and re-implement a helper that already exists two folders over. Each addition looks reasonable alone. Together they bury the code that matters.

The usual cleanup makes it worse: an agent asked to "remove dead code" deletes a function that a route loads by string, and nothing catches it until production.

**The Fix** is an audit that has to prove every claim:

- [`/ai-slop-audit`](./skills/ai-slop-audit/SKILL.md) inventories every module, finds the entrypoints, and checks every way code can be reached (dynamic imports, string references, DI tokens, framework conventions, the public API) before it calls anything dead. Each finding carries the commands that prove it and a confidence level.
- Nothing changes until you name a finding: `fix SLOP-012`. Then it writes a characterization test if the behaviour isn't covered, makes the smallest change, and runs your checks against the baseline.
- `publish` turns the plan into GitHub issues that [`/implement`](https://github.com/mattpocock/skills/tree/main/skills/engineering/implement) can build from, so the cleanup can run as AFK tickets.

### #2: Everything reads like ChatGPT wrote it

> "Never use a long word where a short one will do. If it is possible to cut a word out, always cut it out."
>
> George Orwell, *Politics and the English Language*

**The Problem**: You can spot agent prose in a sentence: `It's not just a tool, it's a mindset.` `Let's dive in.` Em dashes everywhere, `pivotal` and `seamless` in every paragraph, a `Here's the thing:` before every point. In Italian it's `Nell'attuale panorama`, `non si tratta solo di… ma di…` and an `In conclusione` nobody asked for.

Asking the agent to "write more naturally" swaps one tic for another.

**The Fix** is a checklist the agent can't skip:

- [`ai-slop-prose`](./skills/ai-slop-prose/SKILL.md) runs a deterministic scanner over the text: 40+ rules across eleven categories, word lists built from the research (Kobak et al.'s 379 excess words, Liang et al., Wikipedia's *Signs of AI writing*, slop-score, and two Italian studies), every kind of dash, and the classic punctuation errors.
- Its tiers and thresholds are calibrated on about 5,200 human and AI documents in both languages: on held-out human text, under 1% of documents end up with a required fix (4/592 English, 0/454 Italian), while every Italian Claude answer in the test set is caught. Each verdict it makes is recorded, and rules that keep misfiring lose tier on their own.
- It rewrites each hit in the author's voice, then proves the rewrite kept every number, name and link, and rescans until nothing catalogued is left.
- It fires on its own whenever your agent writes for humans: READMEs, docs, posts, release notes, emails.

<details>
<summary>Example</summary>

```text
Before: In today's fast-paced world, remote work isn't just a trend — it's a revolution, highlighting the need for flexibility.
After:  Remote work is changing how teams operate, and it only works when schedules are flexible.
```

</details>

### #3: Big jobs fall over

> "Adding manpower to a late software project makes it later."
>
> Fred Brooks, *The Mythical Man-Month*

**The Problem**: A codebase with 200 modules doesn't fit in one context window, so you fan the work out to subagents. Then the test suites they launch eat the RAM, the machine swaps, and when you kill the session you lose track of what was done.

**The Fix** is to size the team to the machine:

- [`orchestrate`](./skills/orchestrate/SKILL.md) measures the free RAM before every dispatch and starts only as many agents as fit. A watchdog script (no tokens) watches memory while they run.
- When memory gets tight it stops the newest agents first. Each saves the unit it just finished, and the rest goes into `STOPPED_AGENTS_WORK.md`.
- The next run, in this session or tomorrow's, picks up from that file. Small jobs just run inline.

### Summary

Agents are fast at adding. These skills are about taking away, carefully, with proof. Enjoy.

## Reference

User-invoked skills run only when you type them. Model-invoked skills can be typed too, and the agent also reaches for them when the task fits.

**User-invoked**

- [ai-slop-audit](./skills/ai-slop-audit/README.md): evidence-backed audit and cleanup of needless complexity across a codebase. Modes: `audit [path]`, `plan`, `publish [batches]`, `fix <ID>`, `verify`. Keeps its state in `.slop-audit/` across sessions, and never reports a partial scan as complete.

**Model-invoked**

- [ai-slop-prose](./skills/ai-slop-prose/README.md): strips AI writing tells from English or Italian prose with a deterministic scanner, safe punctuation fixes and a fact-preservation check, then rewrites each hit in the author's voice. Works while drafting or as a sweep over existing files.
- [orchestrate](./skills/orchestrate/README.md): runs a job of independent units inline or on parallel subagents sized to free RAM, with per-unit checkpoints, memory-pressure shedding into `STOPPED_AGENTS_WORK.md`, and resume across sessions. Used by the other two for large jobs.

## Other agents

On Claude Code the skills use argument substitution, command output injected at load time, and background subagents. Each skill tells other agents, in one line, how to do the same by hand. Without background subagents, `orchestrate` runs jobs inline with the same checkpoints. To upload a skill to claude.ai or the Skills API, keep only the `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools` frontmatter keys.

## Development

```bash
claude plugin validate . --strict                      # check the plugin manifests
python skills/ai-slop-prose/scripts/scan.py rules      # list every prose rule
python skills/ai-slop-prose/scripts/scan.py README.md  # sweep a README before committing it
python skills/orchestrate/scripts/mem.py status        # RAM budget for parallel agents
```

New skills go in `skills/<name>/` and in `.claude-plugin/plugin.json`. Bump `version` there on every release: managed installs update only when it changes.

## License

[MIT](LICENSE)

## Italiano

Skill per agenti che ripuliscono quello che l'AI lascia dietro di sé: codice morto e livelli inutili nella codebase, tic di scrittura nei testi. Pensate per Claude Code, funzionano con qualsiasi agente che legga il formato Agent Skills.

### Installazione

1. Scegli dove installarle: globale (cartella utente, tutti i progetti), progetto (dentro il repo, nel commit, per tutto il team) o locale (solo Claude Code, dentro il repo ma fuori da git).
2. Installa con uno di questi comandi.
   - qualsiasi agente: `npx skills@latest add guarriellocristianmichele/supah-skills`, che chiede skill, agenti e ambito (*Project* o *Global*); `-g` lo fissa a globale;
   - Claude Code, globale: `claude plugin install supah-skills --marketplace guarriellocristianmichele/supah-skills --scope user`;
   - Claude Code, progetto: `claude plugin marketplace add guarriellocristianmichele/supah-skills --scope project`, poi `claude plugin install supah-skills@guarriellocristianmichele --scope project`, e commit di `.claude/settings.json`;
   - una sola skill: con skills.sh aggiungi `-s ai-slop-prose`; con il plugin di Claude Code sostituisci `supah-skills` con il nome della skill (`ai-slop-audit`, `ai-slop-prose` o `orchestrate`). Scegli il pacchetto completo oppure le skill singole: installarli entrambi duplica le skill;
   - Codex, Copilot CLI e Gemini CLI: i comandi nei riquadri della sezione [Installation](#installation-1-minute-setup).
3. Facoltativo: tutto funziona da solo, ma se usi anche le skill di mattpocock lancia `/setup-matt-pocock-skills` una volta nel repo. L'audit userà il suo tracker e le sue label (così `/triage` e `/implement` vedono le issue) e passerà i problemi di design a `/improve-codebase-architecture`. Le due raccolte non scrivono mai nei file dell'altra.

Servono Python 3.8 o superiore (solo libreria standard) e git.

### Le skill

- `ai-slop-audit` (la avvii tu) fa un audit di un'intera codebase con prove riproducibili e livello di confidenza per ogni problema. Modalità `audit`, `plan`, `publish`, `fix <ID>`, `verify`. Corregge solo ciò che indichi per ID, a piccoli lotti protetti dai test.
- `ai-slop-prose` (si attiva da sola) usa uno scanner deterministico per i segnali di scrittura AI in inglese e italiano, trattini e punteggiatura compresi, con correzioni sicure, controllo che nessun dato vada perso e riscrittura nella voce dell'autore.
- `orchestrate` (si attiva da sola) esegue lavori grandi inline o su agenti paralleli dimensionati sulla RAM libera, ferma i più recenti quando la memoria scarseggia salvando il lavoro in `STOPPED_AGENTS_WORK.md` e riprende alla sessione successiva.

### Licenza

[MIT](LICENSE)
