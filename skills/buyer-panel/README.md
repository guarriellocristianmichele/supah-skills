# buyer-panel

The popular shortcut for testing an idea is a prompt that asks a model to invent 100 buyers, pitch them and count BUY or PASS. The answers come back warm, alike and expensive: a model judging an idea it knows is yours turns agreeable, synthetic buyers spread about half as much as people do, they never walk away unless told they may, they pick whatever is listed first, and they state prices two to three times too high. This skill runs the same kind of panel built against each of those failures, says on its first line that the panel is simulated, and ends with the first real test to run.

*Versione italiana in fondo: [Italiano](#italiano).*

## Install

```sh
npx skills@latest add guarriellocristianmichele/supah-skills -s buyer-panel
claude plugin install buyer-panel --marketplace guarriellocristianmichele/supah-skills --scope user
```

Every route and scope is in the [repository README](../../README.md#installation-1-minute-setup). Requirements: Python 3.10 or newer on `PATH`, standard library only.

### Works best with orchestrate

Interviews run through [orchestrate](../orchestrate/README.md) when it is installed: small batches of buyers, mixed across segments, each in a fresh context that never sees another batch. Without it the skill interviews one buyer at a time and the report says that independence was partial. Prices of competitors come from a web search, and from their pricing pages once you allow a browser on screen (an isolated Playwright browser, your own Chrome, or none).

## Use

```text
/buyer-panel a time tracker that starts itself when you open a client's files
/buyer-panel
/buyer-panel fix already-paid
/buyer-panel price 9 14 24
/buyer-panel compare "Tickr, a tracker that starts itself" "Tickr, for studios that quote by project"
/buyer-panel competitor Clockify at 4 EUR
/buyer-panel ground
```

It is user-invoked, so it costs nothing in sessions where you don't call it.

- With an idea, it builds the brief from it: the idea in one line, the audience, the price, the alternatives. With none, it drafts the brief from the project you are in (README, product and design notes, pricing and landing copy) and asks you to confirm it, with ready answers.
- It researches competitors, their prices and what the audience spends in the category before inventing anyone, and keeps every source in `research.md`.
- It asks for 30, 100 or 200 buyers (100 by default), plans segments with shares and budget ranges from the research, and writes each buyer with habits, a current solution, a last spend and one honest objection. The script rejects a buyer that misses a field or falls outside the plan.
- Each buyer sees your idea as another company's product on a plain card, next to the real competitors at their real prices and "buy nothing", in an order shuffled per buyer and recorded. They react in their own words first, then choose, say what they would give up to pay, and answer the four Van Westendorp price questions.
- A separate judge, who sees only the reactions, places each one on five fixed anchor statements and tags the reason.
- The script turns the round into the raw BUY share next to a discounted one (the weighting scheme is named), the top five reasons with counts, the three buyer types most likely to buy, and the price range as an upper bound with out-of-order answers dropped and counted.
- Five checks then flag a round you shouldn't trust: intent too uniform, reactions too alike, too much praise, more buyers choosing the offer than people ever say they would, or the option listed first chosen too often. A failed check turns the verdict into "do not trust this round". The thresholds, their sources and the reason for each are in the skill's `READING.md`.
- A devil's advocate, in a context of its own, argues the strongest case against the idea. Its critique gets its own section of the report and never mixes with the buyers' answers.
- The report is a Markdown file with the full buyer table, the checks, the critique, a verdict, and the first real test for this week: five interviews, a smoke test or a pre-sale.
- The script also writes the round as one HTML file you can open anywhere: the simulated-panel line on top, the summary, the price curves and the buyer table with filters by segment, decision and reason, in light and dark themes. After the report it asks whether to publish that page privately (with Claude's Artifact tool, when available), keep it as a local file, or skip it.

The panel lives in `.buyer-panel/<idea>/` in your project; on first use it asks whether to commit it or keep it out of git. `/buyer-panel fix [reason]` reuses the same buyers: it takes the top reason they passed (or the one you name), writes three offer changes tied to the words of the buyers who gave it, tries each on those buyers, runs the best on the whole panel in fresh contexts and shows buyer by buyer who flipped, which option each one moved to, the new top reasons and what the change cost in buyers and price.

`/buyer-panel price [low mid high]` runs the same buyers at three prices, each in its own round with fresh contexts. Without prices it proposes three from the first round's price range and asks you to confirm them. For each price it shows raw and discounted buyers and the revenue (price times discounted buyers), names the price that earns most, and says when counting raw buyers alone would have picked another one. Since synthetic buyers overstate what they would pay, the report treats the pick as an upper bound and ends with the real test that would confirm it: a pre-sale at that price, or a smoke test that shows two prices to two halves of the visitors.

`/buyer-panel pitch [type]` writes a 30-second pitch (about 75 words) for the buyer type most likely to buy, or the one you name, from that type's own words: every borrowed phrase is quoted and traced to the buyer who said it. The script holds out half of that type's buyers before you see any quote, and the pitch is tried on them in fresh contexts; the report sets their answers to the pitch against their first-round answers. With ai-slop-prose installed, the pitch is swept with purpose `pitch`.

`/buyer-panel test` turns the last round into the kit for the first test on people. It writes a Mom Test interview script from the top reasons buyers passed: questions about what people did last time and what they paid, nothing about your idea until the end, and a closing that asks for a commitment of time, an introduction or a pre-order. For a smoke test it writes a landing brief (the offer, the price, the one action to count) and hands it to `/ai-slop-design craft` when installed. Before anything goes live it writes the go and stop thresholds (sign-ups or pre-orders per visit, interviews that end in a commitment) to `test/test.json`, which the script validates and the kit never edits afterwards.

`/buyer-panel compare A B` tests two offers, names or positionings without letting one colour the other. The script splits the panel into two halves balanced by segment, so each buyer sees one variant and no buyer can contrast them. The report puts the BUY share of each half side by side with the reasons each variant drew, and next to the difference it prints the noise: the standard error of a difference between halves this size, and how far one buyer moves the smaller half. A difference within twice the noise is reported as no difference.

`/buyer-panel competitor` adds a competitor at its real price, or changes one's price as a what-if, and runs the same buyers again in fresh contexts. The round diff then shows who switched to the competitor and from what, who left it after a price rise, and who stayed on each option with the reasons that held them, each with the buyer's own words.

`/buyer-panel ground` takes what real people did after a panel: a smoke test's visits and conversions, interviews that ended with a commitment, or a pre-sale. The script checks the counts, compares them with the round that showed the same offer at the same price, and stores the ratio in the panel. From then on every round's summary shows a corrected figure under the raw and discounted shares, naming the real test it came from and its counts.

## What it will not claim

A synthetic panel is a hypothesis generator. It can tell you which objection to test first and who to talk to; it can't tell you that people will buy. Differences between buyer types are reported as descriptive only, since synthetic panels invent and flip them. The evidence behind every choice is in [the research note](../../docs/research/2026-11-synthetic-panels.md) and the design is recorded in [ADR 0014](../../docs/adr/0014-buyer-panel-counters-each-known-failure-of-synthetic-respondents.md).

## Italiano

Il modo più diffuso per provare un'idea è chiedere a un modello di inventare 100 acquirenti, presentargliela e contare chi compra. Le risposte tornano gentili, tutte simili e con prezzi troppo alti: un modello che sa che l'idea è tua diventa accomodante, gli acquirenti sintetici variano la metà delle persone vere, non se ne vanno mai se nessuno glielo permette, scelgono la prima opzione e dichiarano prezzi due o tre volte più alti. Questa skill costruisce lo stesso tipo di panel contro ognuno di questi difetti, dice nella prima riga che è simulato e chiude con il primo test reale da fare.

Installazione: `npx skills@latest add guarriellocristianmichele/supah-skills -s buyer-panel`, oppure come plugin di Claude Code con `claude plugin install buyer-panel --marketplace guarriellocristianmichele/supah-skills --scope user`. Si avvia a mano, quindi non occupa contesto nelle altre sessioni.

- `/buyer-panel <idea>` parte dall'idea; senza argomenti scrive il brief dal progetto in cui lavori e te lo fa confermare con risposte pronte.
- Prima di inventare acquirenti cerca i concorrenti, i loro prezzi e quanto spende il pubblico nella categoria, con le fonti in `research.md`. Apre un browser solo dopo il tuo permesso a schermo.
- Chiede 30, 100 o 200 acquirenti (100 di default), divisi in segmenti con quote e budget presi dalla ricerca; lo script scarta chi manca di un campo.
- Ogni acquirente vede l'idea come il prodotto di un'altra azienda, accanto ai concorrenti veri e a "non compro niente", in un ordine casuale registrato. Prima reagisce a parole, poi sceglie, dice a cosa rinuncerebbe per pagare e risponde alle quattro domande di prezzo di Van Westendorp.
- Un giudice separato, che legge solo le reazioni, le colloca su cinque frasi di riferimento fisse. Lo script calcola la quota di acquisto grezza e quella scontata, i motivi principali con i conteggi, i tre tipi di acquirente più propensi e la fascia di prezzo come limite superiore.
- Cinque controlli segnalano un giro di cui non fidarsi: intenzioni troppo uniformi, reazioni troppo simili, troppe lodi, più acquisti di quanti le persone ne dichiarino mai, o la prima opzione della lista scelta troppo spesso. Se un controllo fallisce, il verdetto diventa "non fidarti di questo giro".
- Un avvocato del diavolo, in un contesto tutto suo, sostiene la tesi più forte contro l'idea; la sua critica ha una sezione a parte nel report e non si mescola mai alle risposte degli acquirenti.
- `/buyer-panel fix [motivo]` prende il motivo principale per cui gli acquirenti hanno rinunciato (o quello che indichi), scrive tre modifiche all'offerta legate alle loro parole, le prova su chi ha dato quel motivo, rifà il giro con la migliore su tutto il panel e mostra acquirente per acquirente chi ha cambiato idea e quanto è costata la modifica.
- `/buyer-panel price [basso medio alto]` ripropone gli stessi acquirenti a tre prezzi, ognuno in un giro a sé; senza prezzi ne propone tre dalla fascia del primo giro e te li fa confermare. Per ogni prezzo mostra acquirenti grezzi e scontati e il ricavo (prezzo per acquirenti scontati), e indica il prezzo che rende di più come limite superiore, con il test reale che lo conferma.
- Il report in Markdown chiude con un verdetto e il primo test reale della settimana. Lo script scrive anche una pagina HTML del round, con la riga sul panel simulato in cima, le curve di prezzo e la tabella filtrabile; la skill ti chiede se pubblicarla in privato, tenerla come file locale o lasciar perdere. Il panel resta in `.buyer-panel/` nel progetto, e la skill ti chiede se metterlo nel commit.
- `/buyer-panel pitch [tipo]` scrive una presentazione da 30 secondi (circa 75 parole) per il tipo di acquirente più propenso, o per quello che indichi, con le sue stesse parole: ogni frase presa in prestito è tra virgolette con l'acquirente che l'ha detta. Lo script tiene da parte metà degli acquirenti di quel tipo, e la presentazione viene provata su di loro in contesti nuovi, confrontando le risposte con quelle del primo giro.
- `/buyer-panel compare A B` prova due offerte, nomi o posizionamenti su due metà del panel bilanciate per segmento, così ogni acquirente ne vede una sola. Il report mette a confronto la quota di acquisto e i motivi delle due metà e accanto alla differenza mostra il rumore del panel: una differenza entro il doppio del rumore vale come nessuna differenza.
- `/buyer-panel competitor` aggiunge un concorrente o ne cambia il prezzo e rifà il giro sugli stessi acquirenti in contesti nuovi; il confronto mostra chi è passato al concorrente, chi è rimasto e i motivi che lo hanno trattenuto.
- `/buyer-panel test` prepara il primo test con persone vere: una traccia di intervista secondo il Mom Test, con domande su cosa hanno fatto l'ultima volta e quanto hanno speso e una richiesta di impegno alla fine; il brief di una landing di prova, passato a `/ai-slop-design craft` se installata; le soglie per andare avanti o fermarsi, scritte in `test/test.json` prima che il test parta.
- `/buyer-panel ground` importa i risultati veri (visite e conversioni di uno smoke test, colloqui finiti con un impegno, prevendite), li confronta con il round che mostrava la stessa offerta allo stesso prezzo e salva il rapporto: da lì ogni report mostra anche la cifra corretta, con il test da cui viene.
