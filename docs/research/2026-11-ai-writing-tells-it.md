# AI writing tells in Italian: sources behind ai-slop-prose

Researched 2026-11-13. Provenance of `skills/ai-slop-prose/scripts/lexicon/it-*.txt` and of the Italian rules in `scan.py`.

## How solid the evidence is

Italian has no equivalent of English Wikipedia's *Signs of AI writing*: Italian Wikipedia's [Intelligenza artificiale](https://it.wikipedia.org/wiki/Wikipedia:Intelligenza_artificiale) page only advises checking for hallucinations, source mismatch and style. Every "Wikipedia list" in the Italian press is a translation of the English page.

| Source | Kind | Notes |
|---|---|---|
| Antonelli 2025, [*Storia brevissima (ma molto intensa) dell'IA-taliano*](https://riviste.unimi.it/index.php/LCdM/article/download/29341/24571/85920) | study, small sample | ChatGPT, Claude, Gemini, Copilot, 2023–2025. Finds grammar slips and English interference "sostanzialmente" gone by mid-2025 |
| Ondelli & Santoro, [ChatGPT-4 rewriting an administrative text](https://riviste.unimi.it/index.php/promoitals/article/download/30514/25430/90532) | study | capitalised list items, capital after colon, bold and markdown overuse |
| De Cesare et al., TU Dresden, [abstract](https://eventi.unitn.it/sites/eventi/files/2025-03/CL_De_Cesare_Abstract.pdf) | study, abstract only | English interference at three levels (punctuation and graphics, lexicon, syntax) in GPT-3/4/4o Italian |
| Pangram, [Segnali di scrittura AI](https://www.pangram.com/it/signs-of-ai-writing) | vendor counts, method undisclosed | per-phrase AI vs human counts; em dash 17 vs 2 per 10k words |
| Pillitteri ([1](https://pasqualepillitteri.it/news/402/riconoscere-testo-scritto-ai-detector-checker), [2](https://pasqualepillitteri.it/news/11194/nuovi-segnali-dopo-em-dash), [3](https://pasqualepillitteri.it/news/13500/come-non-sembrare-ai-metodo-scrittura)), StudioCataldi, Punto Informatico, studenti.it, Il Post, Libero, Linkiesta | press and blogs | community observation; several lists are translations of English ones |

Not accessed: De Cesare's monograph *L'italiano sintetico dell'intelligenza artificiale generativa* (Cesati 2026), De Cesare's Chimera article (bot protection), any Accademia della Crusca or Treccani commentary on LLM style, any CLiC-it corpus study of lexical overuse.

## Lexicon and phrases

| Phrases | Evidence |
|---|---|
| "nell'attuale panorama", "nell'ambito di", "cruciale", "fondamentale", "imprescindibile", "approfondire", "esplorare", "favorire", "promuovere", "nel cuore di", "punto di svolta", "navigare la complessità" | Pillitteri (likely translated from the English list) |
| "È importante notare/sottolineare che", "vale la pena ricordare", "è fondamentale considerare" | community and Pangram (≈3,000) |
| openers "In un mondo in continua evoluzione", "Nel mondo frenetico di oggi", "Nel contesto odierno" | Pangram (≈11,000), community |
| "funge da", "come potente promemoria", "un mosaico vivace", "un intricato intreccio", "fornendo preziose informazioni" | Pangram (3,000–49,000) |
| "riveste un ruolo fondamentale", "la lingua è in continua evoluzione", "è importante promuovere" | Antonelli (studied) |
| closers "In conclusione", "In sintesi", "In definitiva", "Non ci resta che", "Una cosa è certa" | community |
| sentence-initial "Inoltre", "Tuttavia", "Pertanto", "In ogni caso", "Di conseguenza" | Antonelli: placed "sistematicamente a inizio di periodo" |
| "Certo! Ecco…" (Pangram: 0 human vs 94 AI), "Sarei felice di aiutarti", "Hai perfettamente ragione", "Se vuoi, posso…" | Antonelli, Pangram, Il Post |
| "La verità è che", "Ecco il punto", "Diciamolo chiaramente", "E questo conta" | anecdotal (Pillitteri, after Ruben Hassid) |

"Un vero e proprio" and "sfide e opportunità" appeared in no source; they are in `scan.py` from our own observation and should be the first candidates for removal if they cause false positives.

## Structural and typographic tells

| Tell | Regex | Source |
|---|---|---|
| em dash; unspaced `\S—\S` is the clearest signal, since Italian asides take a spaced en dash ( – ) | Y | Pangram, Il Post, tuttotech |
| negative parallelism: "Non è X, è Y", "Non si tratta (solo) di X, ma di Y", two-sentence form | P | Pangram (3×), Il Post via Barron's (4× in corporate text 2023–2025) |
| triads ("Più veloce, più economico, più intelligente") | P | Pangram (4×) |
| verbless fragment runs ("Veloce. Semplice.") | P | Pillitteri |
| capitalised list items without the Italian ";" terminator | Y, high false-positive risk | Ondelli & Santoro |
| capital after a colon | Y, exclude proper nouns and direct speech | Ondelli & Santoro |
| Title Case headings (Italian capitalises only the first word) | Y | Linkiesta (calls it anglophile, not AI-specific) |
| bold and markdown overuse | Y | Pangram (bold 43×), Ondelli & Santoro, Antonelli |
| Unicode symbols and emoji (`─` 940×, `✅` 167× per Pangram) | Y | Pangram, Antonelli |
| trailing gerund clause (", sottolineando…", ", contribuendo a…") | P | Libero (summarising W) |
| binomials joined by polysyndeton ("la grammatica e la sintassi") | P | Antonelli |
| chatbot leftovers at the end ("Se vuoi, posso…", "Fammi sapere") | Y | Il Post (a published article ended with one) |

## False-positive risks

- Connectives (inoltre, tuttavia, pertanto, quindi, dunque, insomma) are core Italian; plain-language guidelines recommend them. Score density and sentence-initial position only.
- Bureaucratic Italian ("nell'ambito di", "al fine di", "riveste un ruolo", "favorire", "promuovere") predates LLMs.
- "panorama", "approfondire", "fondamentale", "sfide" are normal in journalism.
- "In conclusione" and "In sintesi" are taught for school essays.
- "Non solo… ma anche" is a standard correlative; "Non X, ma Y" is classical antithesis.
- Gerund openers are native syntax. "Giocare un ruolo" was criticised as an anglicism in 2022, before ChatGPT ([Linkiesta](https://www.linkiesta.it/2022/10/giocare-un-ruolo-lingua-italiana/)).
- Capitalised institution names ("Camera dei Deputati") break naive Title Case checks.

## Calibration run

On Antonelli 2025 (≈19,600 words of human academic prose that quotes many AI outputs), the scanner's S and M hits were almost all inside the quoted AI answers, which is correct. Two metrics flagged on the human prose: `dash_per_1k` (the author's correct spaced en dashes) and `short_closer_share` (PDF extraction artefacts). Both are W-tier and resolvable with a `metric` keep entry.

## Mined from modern Italian AI text (2026-11-13)

With 277 WildChat-1M answers (GPT-4 and GPT-3.5, 2023–2024) and 80 Claude answers to realistic Italian requests on the calibration split, contrasted with 1,145 human documents, these assistant formulas recur in both AI sources and almost never in human text, and are now rules:

| Formula | Human | WildChat | Claude | Rule |
|---|---|---|---|---|
| "posso aiutarti", "aiutarti a" | 0 | 12 | 9 | `chat-residue` S |
| opening "Certo!", "Perfetto!", "Ottimo!" | 0 | 8 | 1 | `chat-residue` S |
| "non esitare a…" | 0 | 2 | 0 | `chat-residue` S |
| "Ecco una/un/alcuni…" at line start | 2 | 22 | 23 | `ecco-opener` M |
| "In sintesi" | 0 | 8 | 1 | `signposted-ending` M |
| a whole line in bold as a heading | 0 | 1 | 48 | `bold-heading` (formatting) |

Rejected despite strong ratios: second-person address ("le tue", "potresti", "assicurati di", "ricorda che"). Assistants address the reader, but so do human guides and blogs, and our human Italian corpus has no how-to genre, so the contrast measures genre, not authorship. "In conclusione", "In definitiva" and "Riassumendo" appear in 9 human documents and moved to `summary-closer` (W).

Gap: a human Italian corpus of second-person practical writing (guides, recipes, product pages) would let the second-person formulas be tested properly.
