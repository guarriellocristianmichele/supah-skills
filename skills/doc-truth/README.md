# doc-truth

Docs drift. A README keeps a command after its script was renamed, a flag after it was removed, a link after the page moved, an environment variable nobody reads anymore. AI-written docs make it worse: they describe flags and options that never existed. This skill checks every claim a doc makes about the repository against the repository, then fixes the doc or reports the code that lost what the doc promises.

*Versione italiana in fondo: [Italiano](#italiano).*

## Install

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s doc-truth
claude plugin install doc-truth --marketplace guarriellocristianmichele/supah-skills --scope user
```

Every route and scope is in the [repository README](../../README.md#installation-1-minute-setup). Requirements: Python 3.10 or newer on `PATH`, standard library only.

## Use

```text
/doc-truth
/doc-truth README.md docs/install.md
```

With no arguments it checks every tracked Markdown file. It is user-invoked, so it costs nothing in sessions where you don't call it. With more than three files it runs them on parallel agents through [`orchestrate`](../orchestrate/README.md) when that skill is installed. When the history can't tell whether the doc or the code changed on purpose, it asks you, with the answers ready to pick.

## What it checks

| Claim | Finding | Tier |
|---|---|---|
| a relative link | the file does not exist | S |
| a link to `#heading` | no such heading in the target | M |
| `python scripts/x.py` in a shell block | the script does not exist | S |
| `--flag` passed to a local script | the flag is not in the script's source | M |
| `npm run x`, `make x` | no such npm script or make target | S |
| `export X=…` or `` `X_Y` `` in the text | no source file reads the name | M |
| a repo path in a code span | it does not exist (often a path in your project, so review only) | W |
| a command | not installed on this machine (review only) | W |

The script reads files and runs nothing. It exits 0 when nothing is left to resolve, 1 when an S or M finding is open, and 2 when a file you named is missing, a directory or not UTF-8: one line on stderr names it, the other files are still checked, and 2 wins over 1. The agent then reads each finding next to the code: when the code changed on purpose the doc is fixed, when the doc still describes what users need the lost behaviour is reported, and paths that belong to the user's project are kept with a reason. It also reads the prose for claims no pattern can check, such as defaults and output formats.

A claim kept on purpose goes in `.doc-truth-keep.tsv` at the repository root, one line per claim: kind, claim and reason, separated by tabs. The script always reads that file, so once you commit it the next run does not report those claims again.

This repository runs it on its own docs in `python scripts/release.py --check`.

## Italiano

La documentazione invecchia: un README tiene un comando dopo che lo script è stato rinominato, un flag dopo che è stato tolto, un link dopo che la pagina si è spostata, una variabile d'ambiente che nessuno legge più. La documentazione scritta dall'AI peggiora le cose, perché descrive flag e opzioni mai esistiti. Questa skill confronta ogni affermazione dei documenti con il repository, poi corregge il documento o segnala il codice che ha perso quello che il documento promette. Con più di tre file lavora su agenti paralleli tramite `orchestrate`, se installata; quando la storia del repo non dice se è cambiato apposta il documento o il codice, te lo chiede con le risposte pronte.

Installazione: `npx skills@latest add guarriellocristianmichele/supah-skills -s doc-truth`, oppure come plugin di Claude Code con `claude plugin install doc-truth --marketplace guarriellocristianmichele/supah-skills --scope user`. Si avvia a mano (`/doc-truth`), quindi non occupa contesto nelle altre sessioni.

- Controlla link e ancore, script e flag nei blocchi shell, script npm e target make, variabili d'ambiente.
- Lo script legge i file e non esegue niente. Esce con 0 se non resta niente da risolvere, 1 se c'è una segnalazione S o M aperta, 2 se un file indicato manca, è una cartella o non è UTF-8: una riga su stderr lo nomina, gli altri file vengono controllati lo stesso e il 2 prevale sull'1. L'agente decide caso per caso se va corretto il documento o segnalato il codice.
- Legge anche il testo per le affermazioni che nessun controllo automatico vede, come valori predefiniti e formati di output.
- Le eccezioni volute vanno in `.doc-truth-keep.tsv` nella radice del repository (tipo, affermazione e motivo separati da tab): lo script lo legge sempre, quindi una volta committato le esecuzioni successive non le segnalano più.
