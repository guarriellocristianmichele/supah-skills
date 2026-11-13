# slop-guard

A Claude Code plugin with two hooks that keep AI slop out of what Claude writes, at a token cost close to zero. It holds no skill: install it next to the skills, or on its own.

*Versione italiana in fondo: [Italiano](#italiano).*

## Install

```sh
claude plugin install slop-guard --marketplace guarriellocristianmichele/supah-skills --scope user
```

Use `--scope project` (after `claude plugin marketplace add guarriellocristianmichele/supah-skills --scope project`) to share it through `.claude/settings.json`. skills.sh installs skills only, so this plugin has no `npx skills` route. It needs Python 3.10+ and bash (Git Bash on Windows, which Claude Code already uses).

## What it does

| Hook | When | Cost |
|---|---|---|
| `SessionStart` | new session, resume, `/clear`, after compaction | about 150 tokens of rules from [`hooks/rules.md`](hooks/rules.md) |
| `PostToolUse` on `Write`, `Edit`, `MultiEdit` | Claude saves a `.md`, `.mdx`, `.markdown`, `.txt` or `.rst` file | nothing when the text is clean; one line otherwise |

The rules cover code (the categories of [ai-slop-audit](../../skills/ai-slop-audit/AUDIT.md)) and prose (the strongest tells of [ai-slop-prose](../../skills/ai-slop-prose/TELLS.md)). They apply to code and files, never to chat replies.

The second hook runs the ai-slop-prose scanner on the text just written, never on the rest of the file, so text a person wrote earlier is left alone. It reports only the hits the scanner counts as required fixes (S and M tiers after calibration and your recorded verdicts), grouped, at most six:

```text
slop-guard notes.md: chat-residue "I hope this helps"; em-dash "—" x2. Rewrite them; leave a quote or a term as it is.
```

It skips code files and documents written for agents: `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, anything under `.claude/`, and reference files that sit next to a `SKILL.md`.

For a full sweep with voice matching and the fact check, use the [ai-slop-prose](../../skills/ai-slop-prose/README.md) skill.

## For maintainers

`scanner/` is a copy of `skills/ai-slop-prose/scripts`, because an installed plugin can't read files outside its own folder. `python scripts/release.py --sync` refreshes it, and `--check` fails when the copy drifts.

## Italiano

Plugin di Claude Code con due hook che tengono l'AI slop fuori da ciò che Claude scrive, con un costo in token quasi nullo. Non contiene skill: si installa accanto alle skill o da solo.

Installazione: `claude plugin install slop-guard --marketplace guarriellocristianmichele/supah-skills --scope user`, oppure `--scope project` per condividerlo nel repo. skills.sh installa solo skill, quindi qui non serve. Richiede Python 3.10+ e bash (su Windows Git Bash, che Claude Code usa già).

- A inizio sessione, dopo `/clear` e dopo una compattazione aggiunge circa 150 token di regole su codice e testi. Valgono per codice e file, mai per le risposte in chat.
- Quando Claude salva un file Markdown o di testo, lo scanner di ai-slop-prose legge solo il testo appena scritto. Se è pulito non succede nulla; altrimenti Claude riceve una riga con i segnali da correggere, al massimo sei.
- Salta il codice e i documenti per agenti (`SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `.claude/`, i file accanto a un `SKILL.md`).

Per una revisione completa, con la voce dell'autore e il controllo dei dati, usa la skill ai-slop-prose.
