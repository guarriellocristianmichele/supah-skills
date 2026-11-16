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
| `SessionStart` | new session, resume, `/clear`, after compaction | about 120 tokens of rules from [`hooks/rules.md`](hooks/rules.md) |
| `PostToolUse` on `Write`, `Edit`, `MultiEdit` | Claude saves prose (`.md`, `.mdx`, `.markdown`, `.txt`, `.rst`) or code (Python, JavaScript, TypeScript) | nothing when the new text is clean; one line otherwise |

The rules cover code (the categories of [ai-slop-audit](../../skills/ai-slop-audit/AUDIT.md)); for prose they ask for plain statements and leave the tells of [ai-slop-prose](../../skills/ai-slop-prose/TELLS.md) to the second hook, which names each one when Claude saves. Listing the tells at session start changed nothing measurable in trials (docs/research/2026-11-skill-tuning.md), so the rules leave them out. They apply to code and files, never to chat replies.

The second hook checks only what Claude just wrote, so text and code a person wrote earlier are left alone. Prose goes through the ai-slop-prose scanner; code goes through the ai-slop-audit code scanner, which reads the saved file (an edit alone often does not parse) and keeps the hits on the new lines. Only required fixes are reported (S and M tiers after calibration, and for prose your recorded verdicts), grouped, at most six:

```text
slop-guard notes.md: chat-residue "I hope this helps"; em-dash "—" x2. Rewrite them; leave a quote or a term as it is.
```

It skips other file types and documents written for agents: `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, anything under `.claude/`, and reference files that sit next to a `SKILL.md`.

For a full sweep with voice matching and the fact check, use the [ai-slop-prose](../../skills/ai-slop-prose/README.md) skill.

## For maintainers

`scanner/` and `codescan/` are copies of `skills/ai-slop-prose/scripts` and `skills/ai-slop-audit/scripts`, because an installed plugin can't read files outside its own folder. `python scripts/release.py --sync` refreshes them, and `--check` fails when a copy drifts.

## Italiano

Plugin di Claude Code con due hook che tengono l'AI slop fuori da ciò che Claude scrive, con un costo in token quasi nullo. Non contiene skill: si installa accanto alle skill o da solo.

Installazione: `claude plugin install slop-guard --marketplace guarriellocristianmichele/supah-skills --scope user`, oppure `--scope project` per condividerlo nel repo. skills.sh installa solo skill, quindi qui non serve. Richiede Python 3.10+ e bash (su Windows Git Bash, che Claude Code usa già).

- A inizio sessione, dopo `/clear` e dopo una compattazione aggiunge circa 120 token di regole sul codice e una riga sui testi: i tell dei testi li segnala il secondo hook, quando Claude salva. Valgono per codice e file, mai per le risposte in chat.
- Quando Claude salva un testo (Markdown, txt, rst) o del codice (Python, JavaScript, TypeScript), lo scanner controlla solo la parte appena scritta. Se è pulita non succede nulla; altrimenti Claude riceve una riga con i segnali da correggere, al massimo sei.
- Salta gli altri tipi di file e i documenti per agenti (`SKILL.md`, `AGENTS.md`, `CLAUDE.md`, `.claude/`, i file accanto a un `SKILL.md`).

Per una revisione completa, con la voce dell'autore e il controllo dei dati, usa la skill ai-slop-prose.
