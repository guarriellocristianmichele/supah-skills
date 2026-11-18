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
| a codebase built fast with AI that feels bloated | `/ai-slop-audit audit` → `/clear` → `plan` → `/clear` → `fix all` (or `fix B1` → `verify`) |
| sharing the cleanup with a team or agents | `/ai-slop-audit publish` → `/clear` → `fix #<map>`, or `fix #<n>` or `/implement #<n>` one at a time |
| a plan with many batches, too slow one by one | `/ai-slop-audit fix all`, `/ai-slop-design sweep all` |
| a new site or page that must not look generated | `/ai-slop-design craft <brief>` |
| a site that looks generated, low-contrast text, copy-pasted styles | `/ai-slop-design sweep <files>`; with no files, above 5 surfaces or 40 frontend files it asks to audit first |
| a page a sweep handed off because it sits in a whole lane | `/ai-slop-design craft <surface>` |
| a whole platform that looks generated, before fixing anything | `/ai-slop-design audit [path]` → `/ai-slop-design plan` → `/ai-slop-design publish` (to share the batches) → `/ai-slop-design sweep all` (or `/ai-slop-design sweep B<n>`, one batch at a time, `B1` first) or `/ai-slop-design craft <surface>` for a handoff, `audit` again after fixes to reconcile |
| sharing a design cleanup with a team or agents | `/ai-slop-design publish` after `plan`, then the command on each issue's Work line |
| is my idea worth building? | `/buyer-panel <idea>`, then the real test it names |
| what would remove the top objection? | `/buyer-panel fix [reason]` after a first panel |
| which of two offers or names, or what if a competitor cuts its price | `/buyer-panel compare A B`, `/buyer-panel competitor` |
| which price, how to pitch it | `/buyer-panel <idea>`, then `/buyer-panel price` and `/buyer-panel pitch` |
| testing the idea on real people | `/buyer-panel test`: interview script, landing brief, go and stop thresholds |
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

Between commands that keep their state on disk it writes `/clear`, so each step starts in a fresh context. Each recommendation comes with its reason, drawn from five habits: evidence before change, measured not guessed, small reversible steps, people decide what leaves the machine, standalone first and paired by configuration.

## Italiano

Un router sulle skill supah. Descrivi cosa vuoi fare e ti consiglia il percorso adatto, i comandi in ordine e il motivo di ogni passo, compreso come si combina con le skill di mattpocock. Senza argomenti mostra le situazioni e ti chiede qual è la tua. Si avvia solo a mano, quindi non occupa contesto nelle altre sessioni.

```text
/supah-help la mia app è stata fatta con l'AI e il codice è pieno di roba inutile
/supah-help devo sistemare i testi dei messaggi di errore e della landing page
/supah-help vale la pena costruire questa idea?
```

Tra un comando e l'altro, quando lo stato resta su disco, scrive `/clear`, così ogni passo parte da un contesto pulito. Ogni consiglio spiega il perché con cinque principi: prove prima di cambiare, misurare invece di indovinare, passi piccoli e reversibili, sono le persone a decidere cosa esce dalla macchina, funziona da sola e si integra tramite configurazione.
