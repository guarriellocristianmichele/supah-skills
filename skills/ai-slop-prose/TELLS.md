# Tells

Eleven categories, swept in this order. `rule` names are scanner rule ids; tells without one are read for by the model. Tiers: **S** rewrite on one sighting; **M** rewrite unless a keep reason applies; **W** act only when the scanner flags its metric, then thin the pattern out instead of fixing each instance.

The tiers below are the designed ones. Calibration admits many rules one tier lower for a language (`scripts/calibration.json`), and each hit carries the tier it was admitted at: that tier is the one to act on. A hit at W, or marked `auto:` or `learned:`, leaves the rescan clean; rewrite it when it is in fact a tell.

Every fix states the point plainly, in the author's voice. A fix that swaps one tell for another (a contrast turned into a rhetorical question, a fragment into a colon reveal) is not done.

## 1. residue

Leftovers of a chat, never meant for the reader.

- S `chat-residue`: "I hope this helps", "Great question", "Let me know if…", "Certo! Ecco…", "Se vuoi, posso…", "Hai perfettamente ragione".
- M `ecco-opener` (IT): a reply that opens by presenting itself, "Certo! Ecco una versione…", "Ecco come…".
- S `ai-disclaimer`: "as of my last knowledge update", "As an AI language model", "Come modello linguistico".
- S `placeholder`: `[Your Name]`, `[Inserisci data]`, `2025-xx-xx`, `INSERT_URL`.
- S `citation-leak`: `contentReference[oaicite:1]`, `utm_source=chatgpt.com`, `turn0search3`.
- Reasoning leaks addressed to the user: "I want to be exact about my own role here".

Fix: delete. A placeholder becomes the real value, or a question to the user when the value is unknown.

## 2. contrast

Denying a claim nobody made in order to assert another.

- S `not-x-its-y`: "It isn't just a tool — it's a mindset", "Non è solo una tendenza, è una rivoluzione".
- S `not-just-x`: "not just X, but Y" (the correlative "not only X but also Y" is ordinary English and is not matched).
- S `not-x-but-y`: the split form, "This isn't about speed. It's about trust.", "Non è X. È Y.", "not because X, but because Y", "Non si tratta di X, ma di Y".
- M `rather-than-merely`: "rather than merely", "less a tool than a mirror".
- M `countdown`: "Not a bug. Not a feature. A design flaw."
- W `non-solo-ma-anche`: standard Italian correlative, suspicious only in clusters.

Fix: state Y directly ("Remote work changed how teams hire"). Keep when X is a real misconception the text names and answers.

## 3. suspense

Staging a reveal the content does not earn.

- S `staged-opener`: "Here's the thing", "Let's dive in", "Let's break it down", "Scopriamo insieme", "Diamo un'occhiata più da vicino".
- M `self-question`: "The result? Devastating." "Il risultato? Produttività alle stelle."
- M `false-candor`: "To be clear", "Let's be honest", "The truth is", "La verità è che", "Ecco il punto", "Una cosa è certa".
- Withheld subject ("This one change transformed everything"), cliffhanger paragraph ends.

Fix: give the answer in the sentence that raises it. "Productivity rose 12% in the first quarter."

## 4. significance

Telling the reader something matters instead of showing why.

- M `inflated`: "plays a pivotal role", "a testament to", "evolving landscape", "in today's fast-paced world", "riveste un ruolo fondamentale", "nell'attuale panorama", "in un mondo in continua evoluzione", "punto di svolta", "un vero e proprio".
- M `importance-flag`: "This matters because", "It's crucial to note", "È importante sottolineare", "Vale la pena ricordare", "E questo conta".
- M `ing-tail`: a trailing participle that asserts meaning: ", highlighting the need for…", ", sottolineando l'importanza di…".
- M `tradeoff-denial`: "without sacrificing quality".
- M `copula-avoidance`: "serves as", "stands as", "boasts", "funge da" where *is* or *has* is meant.
- M `promotional`: "nestled", "breathtaking", "cutting-edge", "all'avanguardia", "mozzafiato".
- Stakes inflation: "will define the next decade".

Fix: replace the claim of importance with the fact that makes it important, or cut it. "serves as" → "is".

## 5. vocabulary

Words models over-use relative to human writers.

- M `marked-word`: delve, tapestry, testament, underscore, showcase, meticulous, intricate, pivotal, seamless, multifaceted, transformative; arazzo, intricato, sinergia, olistico, poliedrico. Lists: `scripts/lexicon/*-marked.txt`.
- W `style_words_per_1k`: density of the broader list (`*-style.txt`): crucial, comprehensive, foster, leverage, robust; cruciale, fondamentale, approfondire, panorama.
- Magic adverbs: quietly, deeply, fundamentally, remarkably, profondamente.
- Stiff synonyms: utilize, commence, endeavor.

Fix: the plain word the author would say ("look at", "shows", "careful", "important"), or nothing. Keep a word used in its literal sense (an underscore character, a tapestry on a wall) or as a domain term.

## 6. attribution

Claims dressed as sourced, or hedged until empty.

- M `vague-attribution`: "Experts argue", "Studies show", "Gli esperti sostengono", "Studi dimostrano" with no source attached.
- M `source-gap`: "not widely documented", "based on available information".
- M `stacked-hedge`: "could potentially", "might arguably", "potrebbe potenzialmente".

Fix: name the source, or state the claim as the author's own, or cut it. One hedge, placed where the doubt is real.

## 7. framing

Talking about the text instead of saying the thing.

- M `signposted-ending`: "In conclusion", "In summary", "At the end of the day", "In sintesi", "Per riassumere", "Non ci resta che".
- W `summary-closer` (IT): "In conclusione", "In definitiva", "Per concludere", "Riassumendo".
- M `meta-text`: "In this article we will explore", "the table below compares", "In questo articolo vedremo".
- M `filler-transition`: "It's worth noting", "Notably", "Interestingly" at sentence start.
- M `analogy-opener`: "Think of it as", "Imagine a world where", "Immagina un mondo".
- A closing paragraph that recaps the whole piece; a first sentence that repeats the heading; answering an objection nobody raised ("One might think…").

Fix: delete the frame and keep the content. An ending says the last new thing, or stops.

## 8. rhythm

Cadence that reads as machine-shaped.

- M `fragment-run`: two or more fragments of three words or fewer in a row. "No fluff. Just results." "Veloce. Semplice."
- W `short_closer_share`: paragraphs ending on a one-line punch.
- W `triads_per_1k`: reflexive lists of three ("fast, simple, and reliable").
- W `sentence_length_cv`: every sentence the same length.
- W `connective_sentence_share`: sentences opening with Additionally / Moreover / Inoltre / Tuttavia / Pertanto.
- Anaphora runs, false ranges ("from startups to enterprises"), quotable one-liners closing sections.

Fix: merge fragments into the sentence they belong to; keep the number of items the content has; vary length where the meaning shifts. Keep a fragment the author uses sparingly for real emphasis.

## 9. punctuation

Dashes and decorations models lean on, plus mechanical errors.

- M `em-dash`: every em dash, spaced or not.
- M `hyphen-as-dash`, M `en-dash-as-dash` (EN): " - " or " – " between words standing in for a dash. Ranges (2020–2024) and compounds are not hits.
- M `exclamation-stack`: "!!", "?!".
- M `accent-error` (IT): perchè → perché, qual'è → qual è, E' → È, pò → po', nè → né, sè → sé.
- M `double-space`, `space-before-punct`, `space-after-comma`, `space-after-period`.
- W `dash_per_1k`: all dashes together, correct Italian en dashes included; dash-heavy prose stays a tell.
- W `quote-mix`: straight and curly quotes in one text.
- W `colon-capital` (IT): capital after a colon, an English habit; proper nouns and direct speech excepted.
- W `symbol`: → • ✓ ★ in running prose.

Fix: `scan.py fix` applies accents and spacing. Each dash becomes the mark the sentence needs: a comma for a light aside, a colon before an explanation, parentheses for a true aside, a full stop for two thoughts. Italian asides take commas or a spaced en dash ( – ). One quote style per text: Italian «» or “”, English the house style. Keep dashes in dialogue (Italian fiction) and quoted material.

## 10. formatting

- M `bold-lead-bullet`: bullets starting "**Label:** …".
- M `bold-heading`: a bold line standing in for a heading.
- M `emoji-marker`: emoji opening headings or bullets.
- M `title-case` (EN), W (IT): "Understanding The Impact Of Remote Work". Italian capitalises only the first word and proper nouns.
- W `bold_per_1k`: bold scattered through prose.
- Bullets where the content is an argument; a horizontal rule between every section; an H1 that repeats the title.

Fix: prose for arguments, lists for parallel items; bold only for what a skimming reader must not miss; sentence case headings.

## 11. dilution

Model-only: the scanner cannot see these.

- One point stretched across paragraphs; the same idea restated in each section.
- Synonym cycling: renaming one thing each sentence (the tool, the platform, the solution).
- Re-explaining what the stated audience already knows.
- Generic over specific: "a leading company" where the text knows the name.
- Invented concept labels ("the supervision paradox") used once.
- Analogy stacking: two or more metaphors for one point.

Fix: say it once, where it lands hardest; keep one name per thing; replace generic with the specific detail the source holds; cut the extra analogy.
