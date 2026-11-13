# context-audit

Every Claude Code session starts with a pile of text you never typed: instructions, memories, the skill and tool listings of every plugin, and whatever hooks inject. This skill measures that pile from your own transcripts, says who put each part there, and finds the parts that contradict each other or hold development back.

*Versione italiana in fondo: [Italiano](#italiano).*

## Install

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s context-audit
claude plugin install context-audit --marketplace guarriellocristianmichele/supah-skills --scope user
```

Every route and scope is in the [repository README](../../README.md#installation-1-minute-setup). Requirements: Python 3.10 or newer on `PATH`, standard library only.

## Use

```text
/context-audit
/context-audit ~/code/my-app
```

It is user-invoked (`disable-model-invocation: true`), so it costs nothing in sessions where you don't call it.

## What it measures

`ctx.py measure` reads the latest transcripts of the project. The first request's input tokens come from the API's usage record, so that number is exact. The rest is split by what the transcript records, each part by owner:

```text
session 4723ce1f: first request 76560 tokens (measured), 9 prompts
    7488 est  skill listing            (built-in or user) 2464, stripe 1603, superpowers 721, ...
    6912 est  deferred tool names      claude_ai_Adobe_for_creativity 1565, claude_ai_META 1264, ...
    4170 est  MCP server instructions  claude.ai Supermetrics Marketing Analytics 1039, ...
    1218 est  agent listing            (built-in or user) 1127, code-simplifier 57, stripe 34
     851 est  hook x1    SessionStart: <EXTREMELY_IMPORTANT>
     333 est  hook x11   UserPromptSubmit: CAVEMAN MODE ACTIVE (full). ...
   55451      system prompt and tool schemas (not in the transcript)
```

Estimated parts (`est`) are characters divided by four. A hook on `UserPromptSubmit` is paid on every prompt, so its row shows how many times it ran.

## What it checks

`ctx.py check` lists candidates and the agent judges each one:

| Kind | Example |
|---|---|
| contradiction | a plugin demands a skill before any reply; a project rule asks for quick action |
| duplicate trigger | two plugins both ship a TDD skill, so the agent picks one at random |
| stale reference | a memory links a memory that no longer exists; `AGENTS.md` cites a missing ADR |
| sediment | a memory that repeats a rule the repo already records |
| limit | a pinned runtime past end of life; a process forced on every action |

The report ends with fixes ranked by tokens saved or conflicts removed. Memories and repo files are changed once you approve; settings and plugins stay yours, and you get the exact command.

Transcripts contain your conversations. The script reads listings, usage records and hook output, and never prints a prompt.

## Limits

- The system prompt and the tool schemas are not in the transcript, so they show up as one remainder.
- Transcript fields are not a documented format. The script skips what it does not recognise instead of failing, and a Claude Code update can empty a category until the parser catches up.
- `measure` and `sources` know Claude Code only; `check` also reads `AGENTS.md` for other agents.

## Italiano

Ogni sessione di Claude Code parte con molto testo che non hai scritto tu: istruzioni, memorie, gli elenchi di skill e tool di ogni plugin, quello che iniettano gli hook. Questa skill lo misura dai tuoi transcript, dice chi ha messo ogni parte e trova le parti che si contraddicono o frenano lo sviluppo.

Installazione: `npx skills@latest add guarriellocristianmichele/supah-skills -s context-audit`, oppure come plugin di Claude Code con `claude plugin install context-audit --marketplace guarriellocristianmichele/supah-skills --scope user`. Si avvia solo a mano (`/context-audit`), quindi non occupa contesto nelle altre sessioni.

- I token della prima richiesta sono misurati dall'API; il resto è diviso per categoria e per plugin, con una stima a quattro caratteri per token.
- Gli hook su `UserPromptSubmit` si pagano a ogni prompt, e il report lo conta.
- Il controllo cerca contraddizioni, skill duplicate, riferimenti rotti, memorie che ripetono il repo e regole che bloccano lo sviluppo; ogni candidato riceve un verdetto.
- Memorie e file del repo vengono modificati dopo la tua approvazione; impostazioni e plugin restano tuoi, ricevi il comando esatto.
- Lo script non stampa mai i tuoi prompt.
