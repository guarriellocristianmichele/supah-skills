# AI writing tells in English: sources behind ai-slop-prose

Researched 2026-11-13 from primary sources. This note is the provenance of `skills/ai-slop-prose/scripts/lexicon/en-*.txt` and of the English rules in `scan.py`. Re-check it when refreshing the lexicons: model vocabulary turns over quickly.

## Sources

| Key | Source | What it gave us |
|---|---|---|
| W | Wikipedia, [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (WikiProject AI Cleanup, Nov 2026 revision) | the category structure, most phrase rules, chat residue, placeholders, leaked citation tokens, the false-positive warnings |
| K | Kobak et al. 2024, *Delving into ChatGPT usage in academic writing through excess vocabulary*, [data](https://github.com/berenslab/llm-excess-vocab), [paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12219543/) | the 379 excess style words, recomputed from the authors' data with their formula (r values match the paper) |
| L | Liang et al. 2024, [arXiv 2403.07183](https://arxiv.org/html/2403.07183) | over-represented adjectives and adverbs in peer reviews |
| E | EQ-Bench [slop-score](https://github.com/sam-paech/slop-score) and the Antislop sampler lists (Paech et al.) | essay slop words, trigrams, and the stage-1 "not X but Y" regexes our contrast rules are modelled on |
| G | Graphite, [AI tells study](https://graphite.io/five-percent/research/ai-tells) | newer model-specific frames ("matters because", "without sacrificing"), em-dash rates by model |
| R | Reinhart et al., PNAS 2025, [PMC11874169](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874169/) | participial clauses and nominalisations as grammatical tells |
| H | [blader/humanizer](https://github.com/blader/humanizer) v4.0.0 | strength ordering, fact-preservation check, voice sample, prompt-injection guard |
| T | [brandhaug/skills `write-like-a-human`](https://github.com/brandhaug/skills) and [tropes.fyi](https://tropes.fyi) | magic adverbs, false ranges, invented labels, stakes inflation, dilution tropes |

Not accessed: the full Antislop paper body, Liang's word lists beyond the published tables, paywalled press (NYT, Economist, Washington Post), Wikipedia's Style and Markup subpages.

## Findings that shaped the design

- **Density, not single hits.** W: "one or two occurrences may be coincidental"; K and L measure whole corpora, never single documents. Hence the tiers: S for unambiguous residue, M for phrases, W for words that count only as density.
- **The signs are not proof.** W calls the page "descriptive, not prescriptive" and warns that false accusations drive editors away. Hence the report wording: "no catalogued tell remains", never "written by a person".
- **Vocabulary turns over.** "Delve" collapsed in 2025; consecutive model versions share roughly 19–45% of their tells (G, via a Pebblous analysis). Hence lexicons as dated plain-text files.
- **Em dashes are a historical tell.** W labels them a sign for 2022 to Sept 2026. G measured humans at 3.14 per 1k words and recent Claude and Gemini models near 0.015. We still flag every em dash because the user wants them gone as a matter of style, and say so in the README.
- **Over-correction is its own slop.** T: cutting every fragment, dash and triad mechanically "produces a different kind of slop"; swapping one trope for another is not a fix. H: rewrites most often drop facts in triad, qualifier and bold-list edits. Hence the rescan loop and `scan.py compare`.
- **Human signals worth keeping** (H, G): specific odd details, mixed feelings, dated references, asides and self-corrections, contractions, exclamations, parentheses.

## Catalogue (by category)

Regex column: Y = a regex catches it, P = needs a density count or POS tags, N = model judgement.

| Category | Tell | Regex | Sources |
|---|---|---|---|
| residue | collaborative residue ("I hope this helps", "Great question!", "Would you like…") | Y | W, H |
| residue | knowledge-cutoff and refusal disclaimers | Y | W, H |
| residue | placeholders (`[Your Name]`, `20XX-xx-xx`, `INSERT_URL`) | Y | W |
| residue | leaked citation tokens (`oaicite`, `utm_source=chatgpt.com`, `turn0search`) | Y | W |
| contrast | negative parallelism (not X but Y; not just/only; split across sentences) | Y | W, E, H, T |
| contrast | "rather than merely", "less like a X and more like a Y" | Y | W, G |
| contrast | countdown ("Not a bug. Not a feature.") | Y | T |
| suspense | staged openers ("Here's the thing", "Let's dive in") | Y | H, T |
| suspense | self-posed question ("The result? Devastating.") | Y | T |
| suspense | false candour ("To be clear", "The truth is") | P | H, T |
| significance | inflated significance ("pivotal moment", "evolving landscape", "a testament to") | Y | W, H, E |
| significance | trailing -ing clause (", highlighting…") | Y | W, H, R |
| significance | importance flagging ("this matters" 116×, "matters because" 132–357×) | Y | G, W |
| significance | tradeoff denial ("without sacrificing") | Y | G |
| significance | copula avoidance ("serves as", "stands as", "boasts") | Y | W, H |
| significance | promotional ("nestled", "breathtaking", "diverse array") | Y | W, H |
| vocabulary | excess style words (lists below) | Y (density) | K, L, E, W |
| vocabulary | magic adverbs (quietly, deeply, fundamentally) | Y | T |
| attribution | vague attribution ("Experts argue", "Studies show") | Y | W, H, T |
| attribution | source-gap disclaimers ("not widely documented") | Y | W, H |
| attribution | stacked hedges ("could potentially") | Y | H |
| framing | signposted conclusion, meta-text about the document | Y | W, T, H |
| framing | filler transitions, analogy openers ("Imagine a world where") | Y | T |
| rhythm | fragment runs, one-line closers, triads, uniform sentence length | P | H, T |
| punctuation | em-dash rate, Unicode arrows, curly-quote mix | Y | W, G, H |
| formatting | bold-first bullets, Title Case headings, emoji markers, excess bold | Y | W, H, T |
| dilution | one point stretched, synonym cycling, invented labels, generic over specific | N | T, W |

## Word lists

### Kobak et al. 2024: excess style words with r ≥ 2.0

These form the bulk of `en-style.txt`; the highest-ratio ones moved to `en-marked.txt`. Full ranked list with r values is appended at the end of this note.

### Liang et al. 2024: top adjectives

commendable, innovative, meticulous, intricate, notable, versatile, noteworthy, invaluable, pivotal, potent, fresh, ingenious, cogent, ongoing, tangible, profound, methodical, laudable, lucid, appreciable, fascinating, adaptable, admirable, refreshing, proficient, intriguing, thoughtful, credible, exceptional, digestible, prevalent, interpretative, remarkable, seamless, economical, proactive, interdisciplinary, sustainable, optimizable, comprehensive, vital, pragmatic, comprehensible, unique, fuller, authentic, foundational, distinctive, pertinent, valuable.

### Liang et al. 2024: top adverbs

meticulously, reportedly, lucidly, innovatively, aptly, methodically, excellently, compellingly, impressively, undoubtedly, scholarly, strategically, intriguingly, competently, intelligently, hitherto, thoughtfully, profoundly, undeniably, admirably, creatively, logically, markedly, thereby, contextually, distinctly, judiciously, cleverly, invariably, successfully.

### EQ-Bench essay list (head)

challenges, strategic, crucial, conclusion, strategies, furthermore, retrieved, moreover, ensuring, ethical, fostering, profound, amid, outcomes, broader, enhance, organizational, implications, societal, technological, initiatives, robust, characterized, sustainability, insights, inherent, resilience, paramount, multifaceted, recognizing, fundamentally, evolving, immense, navigate, rooted, delve, shaping, stakeholders, underscores, prioritize, enduring, pivotal, systemic, complexities, nuanced, proactive, frameworks, crucially, conversely, mitigate, tangible, rigorous, holistic, foundational, cornerstone, relentless, interplay, paradigm, navigating, seamless, tapestry, bedrock, indispensable, transformative, undeniable, intertwined, nascent, overarching, actionable, synergies.

### EQ-Bench essay trigrams (first 40 of 230, stopwords removed)

decision making processes, long term success, plays crucial role, make informed decisions, plays pivotal role, supply chain management, corporate social responsibility, one size fits, ethical decision making, work life balance, key performance indicators, extends far beyond, long term viability, real time data, loyal customer base, data driven decision, culture continuous improvement, address root causes, one must first, double edged sword, provide valuable insights, pivotal role shaping, compelling case study, multi faceted approach, identify areas improvement, maintain competitive edge, increasingly interconnected world, extends beyond mere, essay explores multifaceted, requires multifaceted approach, landscape continues evolve, rapidly evolving landscape, ever evolving landscape, navigate complexities modern, serves stark reminder, testament enduring power, today's fast paced, tapestry woven threads, unlock full potential, delicate balancing act.

### Reinhart et al. 2025: per-model excess (selection)

camaraderie 162×, tapestry 155×, grapple 131× (GPT-4o mini), intricate 119×, underscore 107×, amidst 100×, palpable 95×, unease 63–101× (Llama).

## Prior skills compared

- **humanizer** (26 patterns): strongest process (strength ordering, fact check, voice sample, injection guard); Wikipedia-centric, ~27-word vocabulary, no deterministic scanner, 32 KB long, misses newer frames.
- **write-like-a-human** with tropes.fyi (49 tropes): widest trope coverage; no frequency data, no regex, arbitrary cut-offs ("more than 2–3 em dashes"), no chat-residue or placeholder coverage.
- **ai-slop-prose** takes humanizer's process, the tropes, and adds what neither has: a scanner with exit codes, corpus-derived lexicons, Italian, punctuation fixes, and a fact-preservation diff.

## Appendix: Kobak et al. 2024, all 379 words by excess ratio r

delves (28.0), underscores (13.8), delved (12.2), showcasing (10.7), meticulously (10.4), delve (7.9), intricacies (7.6), underscoring (7.5), intricate (7.4), surpassing (7.1), delving (6.9), commendable (6.8), underscore (6.7), excels (5.8), garnered (5.3), underscored (5.1), intricately (5.0), realm (5.0), encompassed (4.9), renowned (4.9), grappling (4.9), groundbreaking (4.8), emphasizing (4.7), encompassing (4.4), necessitating (4.3), offering (4.3), revolutionizing (4.1), aligning (4.0), revolutionize (3.9), formidable (3.9), showcases (3.8), consolidates (3.8), emphasising (3.8), showcased (3.8), surpasses (3.8), bolstering (3.8), comprehending (3.7), endeavors (3.6), advancements (3.6), heightened (3.6), expediting (3.6), overlooking (3.5), escalating (3.5), notable (3.4), unveiled (3.4), stands (3.3), aiding (3.2), holds (3.2), pioneers (3.2), scrutinizing (3.2), emerges (3.2), pinpointed (3.2), fostering (3.1), meticulous (3.1), advocating (3.1), adept (3.1), discernible (3.1), leveraging (3.1), seamlessly (3.1), encompass (3.1), pivotal (3.1), dependable (3.0), pinpointing (3.0), transformative (3.0), advancing (3.0), aligns (2.9), swift (2.9), multifaceted (2.9), crafting (2.9), urging (2.8), exceptional (2.8), harnesses (2.8), accentuates (2.8), enhancements (2.8), nuanced (2.7), underexplored (2.7), unveils (2.7), unraveling (2.7), refining (2.7), interconnectedness (2.7), upholding (2.7), realms (2.7), emphasizes (2.6), notably (2.6), promise (2.6), inquiries (2.6), fosters (2.6), delineates (2.6), highlighting (2.6), surpassed (2.6), pioneering (2.5), necessitates (2.5), streamlining (2.5), scrutinize (2.5), encapsulates (2.5), exacerbating (2.5), gauged (2.5), discerning (2.5), bolstered (2.4), leverages (2.4), enhancing (2.4), illuminates (2.4), emphasises (2.4), propelling (2.4), paving (2.4), exceeding (2.4), hinges (2.4), poses (2.4), posing (2.4), culminating (2.4), akin (2.4), groundwork (2.4), avenues (2.4), encompasses (2.4), uncharted (2.3), employs (2.3), burgeoning (2.3), exhibiting (2.3), necessitate (2.3), streamlines (2.3), employing (2.3), endeavours (2.3), streamline (2.3), elucidates (2.3), categorizing (2.3), noteworthy (2.3), elucidating (2.3), emulation (2.2), poised (2.2), hinting (2.2), introduces (2.2), surmount (2.2), inadequately (2.2), uphold (2.2), unveiling (2.2), enhances (2.2), juxtaposed (2.2), warranting (2.2), pinpoint (2.2), discerned (2.2), facilitating (2.2), seamless (2.2), unveil (2.2), addressing (2.1), spanning (2.1), empowers (2.1), bolster (2.1), refines (2.1), revolves (2.1), augmenting (2.1), interplay (2.1), crucial (2.1), impressive (2.1), utilizing (2.1), integrates (2.1), discern (2.1), garnering (2.1), necessity (2.1), detrimentally (2.1), foundational (2.1), offers (2.1), solidify (2.1), enduring (2.1), conversely (2.1), explores (2.1), substantiated (2.1), capitalizing (2.0), affirming (2.0), insights (2.0), distinctions (2.0), shedding (2.0), alongside (2.0), pressing (2.0), elevates (2.0), featuring (2.0), equipping (2.0), heighten (2.0), refine (2.0), valuable (2.0), advancement (2.0), emulating (2.0), nuances (2.0), overlook (2.0), imperative (2.0), serves (2.0), expedite (2.0), spurred (2.0), diminishes (2.0), spanned (2.0), compelling (2.0), utilizes (2.0), customizing (2.0), surged (2.0), merges (2.0), harnessing (2.0), incorporates (1.9), substantiates (1.9), strategically (1.9), impacting (1.9), ensuring (1.9), hold (1.9), attains (1.9), dependability (1.9), adhering (1.9), highlights (1.9), afflicted (1.9), additionally (1.9), uncovering (1.9), impeding (1.9), align (1.9), elevating (1.9), exhibited (1.9), innovative (1.9), unlocking (1.9), acknowledges (1.9), addresses (1.9), versatility (1.9), incorporating (1.9), acknowledging (1.9), furnish (1.9), capabilities (1.9), adhered (1.9), surpass (1.8), swiftly (1.8), enabling (1.8), struggle (1.8), avenue (1.8), optimizing (1.8), categorizes (1.8), streamlined (1.8), illuminating (1.8), signifying (1.8), orchestrating (1.8), demonstrating (1.8), crafted (1.8), unparalleled (1.8), offer (1.8), elevate (1.8), scrutinized (1.8), exceptionally (1.8), achieving (1.8), emphasize (1.8), embracing (1.8), focusing (1.8), comprehensive (1.8), exhibit (1.8), enhance (1.8), seeks (1.8), diminishing (1.8), combating (1.7), posed (1.7), correlating (1.7), imbalances (1.7), primarily (1.7), amidst (1.7), thorough (1.7), harness (1.7), integrating (1.7), particularly (1.7), precise (1.7), contributing (1.7), recognizing (1.7), emerged (1.7), complicates (1.7), complicating (1.7), thereby (1.7), stemming (1.7), investigates (1.7), advocates (1.7), broader (1.7), exhibits (1.7), employed (1.7), detailing (1.7), serving (1.7), revealing (1.7), distinctive (1.7), disrupts (1.7), exerting (1.7), invaluable (1.7), elucidate (1.6), diverse (1.6), pose (1.6), substantial (1.6), methodologies (1.6), impede (1.6), inherent (1.6), predominantly (1.6), outlines (1.6), challenges (1.6), yielding (1.6), unexplored (1.6), involves (1.6), evolving (1.6), displaying (1.6), exploration (1.6), evaluates (1.5), hinder (1.5), categorized (1.5), presents (1.5), demonstrates (1.5), ultimately (1.5), pronounced (1.5), examines (1.5), persist (1.5), shaping (1.5), facilitated (1.5), preserving (1.5), comprising (1.5), remarkable (1.5), assessments (1.5), varying (1.5), distinct (1.5), consequently (1.5), prevalent (1.5), facilitates (1.5), utilized (1.5), address (1.4), subsequently (1.4), integration (1.4), highlight (1.4), involving (1.4), reveals (1.4), across (1.4), initially (1.4), typically (1.4), attributed (1.4), providing (1.4), maintaining (1.4), influencing (1.4), leading (1.4), specifically (1.3), challenge (1.3), assessing (1.3), limitations (1.3), elevated (1.3), indicating (1.3), potentially (1.3), linked (1.3), effectively (1.3), demonstrated (1.3), findings (1.3), potential (1.3), understanding (1.3), strategies (1.3), within (1.3), aims (1.3), despite (1.3), remains (1.3), resulting (1.3), techniques (1.3), promising (1.3), enhanced (1.2), approach (1.2), like (1.2), impact (1.2), various (1.2), individuals (1.2), revealed (1.2), need (1.2), while (1.2), assess (1.2), complex (1.2), through (1.2), outcomes (1.2), assessed (1.1), conducted (1.1), these (1.1), into (1.1), conditions (1.1), including (1.1), observed (1.1), primary (1.1), research (1.1), role (1.1), identified (1.1), both (1.1), their (1.1), using (1.0), this (1.0)


Largest frequency gap δ (common words, by absolute excess):

potential (0.052), these (0.042), findings (0.041), crucial (0.037), additionally (0.036), exhibited (0.032), while (0.031), insights (0.030), within (0.028), particularly (0.027), across (0.027), comprehensive (0.026), demonstrated (0.025), this (0.024), through (0.024), into (0.023), enhance (0.023), challenges (0.022), approach (0.022), notably (0.022), revealed (0.022), including (0.021), impact (0.021), various (0.021), enhancing (0.020), understanding (0.020), employed (0.019), valuable (0.019), outcomes (0.018), strategies (0.017)
