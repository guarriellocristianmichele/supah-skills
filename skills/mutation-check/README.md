# mutation-check

Checks whether your tests notice when the code changes. It makes one small change at a time (a `<` becomes `<=`, an `and` becomes `or`, a return value disappears), runs your own test command after each, and lists the changes the tests let through. A test file that lets every change through is tautological: it checks a mock, a constant, or nothing.

*Versione italiana in fondo: [Italiano](#italiano).*

## Install

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s mutation-check
claude plugin install mutation-check --marketplace guarriellocristianmichele/supah-skills --scope user
```

Every route and scope is in the [repository README](../../README.md#installation-1-minute-setup). Requirements: Python 3.10 or newer on `PATH`, standard library only, and git.

## Use

```text
/mutation-check src/pricing.py --function discount pytest tests/test_pricing.py
```

Or ask in plain words: "do the tests for `discount` really check anything?" The agent also reaches for it when an audit suspects a tautological test.

## What a run looks like

```text
M1    line 2     >= -> >                      killed
M2    line 2     90 -> 91                     killed
M7    line 4     >= -> >                      survived
score 0.9: 9 of 10 mutants killed; 1 survived
```

Each survivor gets a verdict. It is either equivalent (the change behaves the same for every input, so there is nothing to test) or a gap, reported with the input no test tries.

## Safety

The file is changed in place while your tests run and restored after every mutant, on errors and on Ctrl+C. The script refuses a file with uncommitted changes, so `git checkout -- <file>` always brings it back. Your test command runs through the shell exactly as you wrote it.

## Limits

- Python is mutated through `ast`, JavaScript and TypeScript through their operators and literals outside strings and comments.
- Mutants run one at a time, so a slow suite makes a slow run: narrow the scope with `--function` or `--lines`.
- Deciding that a survivor is equivalent is a judgement, made by reading the code; the report says why for each one.

## Italiano

Controlla se i tuoi test si accorgono quando il codice cambia. Fa una piccola modifica alla volta (un `<` diventa `<=`, un `and` diventa `or`, un valore di ritorno sparisce), lancia il tuo comando di test dopo ognuna ed elenca le modifiche che i test lasciano passare. Un file di test che le lascia passare tutte è tautologico: controlla un mock, una costante o niente.

Installazione: `npx skills@latest add guarriellocristianmichele/supah-skills -s mutation-check`, oppure come plugin di Claude Code con `claude plugin install mutation-check --marketplace guarriellocristianmichele/supah-skills --scope user`. Richiede Python 3.10 o superiore e git.

- Ogni modifica sopravvissuta riceve un verdetto: equivalente (stesso comportamento per ogni input) oppure buco nei test, con l'input che nessun test prova.
- Il file viene modificato sul posto e ripristinato dopo ogni mutante, anche in caso di errore; lo script rifiuta file con modifiche non committate.
- `ai-slop-audit` la usa come prova per i test tautologici.
