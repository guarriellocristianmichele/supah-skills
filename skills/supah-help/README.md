# supah-help

A router over the supah skills. Describe what you are trying to do, and it recommends the flow that fits, the commands in order, and the reason behind each step. It also says how the skills pair with [mattpocock/skills](https://github.com/mattpocock/skills).

*Versione italiana in fondo: [Italiano](#italiano).*

## Install

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s supah-help
claude plugin install supah-help --marketplace guarriellocristianmichele/supah-skills --scope user
```

Every route and scope is in the [repository README](../../README.md#installation-1-minute-setup). The skill only routes: install the skills it recommends as well.

## Use

```text
/supah-help
/supah-help my app was built with Cursor and the codebase feels bloated
/supah-help I need to clean the error messages and the landing page copy
/supah-help the scanner keeps flagging a word that is fine in our domain
```

With no arguments it shows the situations and asks which one is yours. It is user-invoked (`disable-model-invocation: true`), so it costs nothing in sessions where you don't call it.

## What it recommends

| Situation | Flow |
|---|---|
| a codebase built fast with AI that feels bloated | `/ai-slop-audit audit` → `plan` → `fix B1` → `verify` |
| sharing the cleanup with a team or agents | `/ai-slop-audit publish`, then `fix #<n>` or `/implement #<n>` |
| a new site or page that must not look generated | `/ai-slop-design craft <brief>` |
| a site that looks generated, low-contrast text, copy-pasted styles | `/ai-slop-design sweep <files>` |
| is my idea worth building? | `/buyer-panel <idea>`, then the real test it names |
| which price, how to pitch it | `/buyer-panel <idea>`: price range and likely buyer types; then `/buyer-panel pitch` |
| the text users see in an app | `/ai-slop-prose sweep src/**/*.tsx locales/*.json` |
| a page, post, email or README | `/ai-slop-prose sweep <file>` plus what it is for |
| a big context before you type, or instructions that fight | `/context-audit` |
| slop kept out of every session | install the `slop-guard` plugin |
| writing something new | nothing: ai-slop-prose drafts to its rules |
| docs that may have drifted from the code | `/doc-truth` |
| tests you don't trust | `/mutation-check <file> <test command>` |
| fine text flagged as slop | keep with reason `fp`, `scan.py verdict`, now and then `scan.py audit` |
| many files, or a slow machine | `orchestrate` runs on its own; `/orchestrate` for your own jobs |
| an interrupted session | run the same command again |
| also using mattpocock/skills | `/setup-matt-pocock-skills` once |

Each recommendation comes with its reason, drawn from five habits: evidence before change, measured not guessed, small reversible steps, people decide what leaves the machine, standalone first and paired by configuration.

## Italiano

Un router sulle skill supah. Descrivi cosa vuoi fare e ti consiglia il percorso adatto, i comandi in ordine e il motivo di ogni passo, compreso come si combina con le skill di mattpocock. Senza argomenti mostra le situazioni e ti chiede qual è la tua. Si avvia solo a mano, quindi non occupa contesto nelle altre sessioni.

```text
/supah-help la mia app è stata fatta con l'AI e il codice è pieno di roba inutile
/supah-help devo sistemare i testi dei messaggi di errore e della landing page
/supah-help vale la pena costruire questa idea?
```

Ogni consiglio spiega il perché con cinque principi: prove prima di cambiare, misurare invece di indovinare, passi piccoli e reversibili, sono le persone a decidere cosa esce dalla macchina, funziona da sola e si integra tramite configurazione.
