#!/usr/bin/env python3
"""Deterministic scanner for AI writing tells in English and Italian prose. Stdlib only.

  scan.py [--lang auto|en|it] [--keep FILE] [--json] FILE...
      List every catalogued tell with line, tier and category, plus density metrics.
      Exit 0 when nothing is left to resolve (S/M hits all kept, no metric flagged), else 1.

  scan.py fix [--lang auto|en|it] FILE...
      Apply the unambiguous corrections (Italian accent errors such as perchè, qual'è,
      E'; double spaces; space before punctuation; missing space after a comma) in place.

  scan.py rules
      Print every rule id with category, tier and language, the metric thresholds
      and the lexicon sizes.

  scan.py verdict ORIGINAL FINAL [--keep FILE] [--source model|human]
      Record the verdicts of a finished sweep (keep reason fp -> fp, other reasons -> kept,
      hit gone from FINAL -> tell) and rebuild the learned model.
  scan.py learn              rebuild the model and print each rule's measured precision
  scan.py audit [--fraction F]   sample the model's fp verdicts as TSV for a human to confirm
  scan.py label FILE         record the confirmed audit file as human verdicts

Context gates resolve hits inside quotes and blockquotes, vocabulary in headings,
capitalised names and Italian dialogue dashes (kept as auto:*); --no-gates shows them.
The learned model lives in SUPAH_PROSE_HOME (default: the user config folder,
supah-skills/prose); --no-learn ignores it.

  scan.py compare ORIGINAL REWRITE
      List numbers, URLs, code spans, quotes and proper nouns present in ORIGINAL
      but missing from REWRITE. Exit 0 when nothing is missing, else 1.

Tiers: S = one hit is enough to rewrite; M = rewrite unless there is a keep reason;
W = acted on only when its density metric is flagged.
Keep file: TSV lines `rule<TAB>matched text<TAB>reason`; matching hits count as resolved.
Reasons: quote, voice, literal, term, dialogue (a real tell kept) or fp (not a tell).
A flagged metric is kept with `metric<TAB><metric name><TAB>reason`.
Per-1k densities need at least 300 words; shorter texts show n/a.
Categories match the headings of TELLS.md.
"""
import argparse
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import learn  # noqa: E402  (sibling module: verdict learning)

HERE = os.path.dirname(os.path.abspath(__file__))
I = re.IGNORECASE
M = re.MULTILINE

# (rule id, category, tier, lang, pattern, flags). lang: en | it | any
RULES = [
    # residue: chat leftovers, placeholders, leaked tokens
    ("chat-residue", "residue", "S", "en", r"\b(I hope (this|that|it) helps|Certainly!|Of course!|Great question|Absolutely!|Would you like me to|Let me know if you|Feel free to (ask|reach out)|Happy to help|I'd be happy to|I hope you found)", I),
    ("ai-disclaimer", "residue", "S", "en", r"\b(as of my (last|latest) (knowledge|training)|my knowledge cutoff|as an AI( language model)?\b|I (don't|do not|cannot|can't) browse)", I),
    ("chat-residue", "residue", "S", "it", r"(\bCerto!|\bCertamente!|\bEcco (a te|qui|una versione|il testo|la versione)\b|\bSpero (che )?(questo|ti) (sia|possa essere) (utile|d'aiuto)|\bSe vuoi,? posso\b|\bVuoi che (ti|io)\b|\bFammi sapere se\b|\bSarei felice di\b|\bSono qui per aiutarti\b|\bHai (pienamente |perfettamente |assolutamente )?ragione\b|\bOttima domanda\b)", I),
    ("ai-disclaimer", "residue", "S", "it", r"\b(Come (modello linguistico|intelligenza artificiale)|in base alle mie (ultime )?conoscenze|al mio ultimo aggiornamento)\b", I),
    ("placeholder", "residue", "S", "any", r"(\[(Your|Insert|Add|Describe|Company|Name|Tuo|Tua|Inserisci|Nome|Azienda|Data)\b[^\]\n]{0,40}\]|\b20\d\d-(xx|XX)-(xx|XX)\b|\bINSERT_[A-Z_]+\b|example\.com/source\d)", 0),
    ("citation-leak", "residue", "S", "any", r"(contentReference\[oaicite:\d+\]|oai_citation|utm_source=chatgpt\.com|\bturn\d+(search|view|news|fetch)\d+\b)", 0),

    # contrast: negative parallelism and relatives
    # calibrated 2026-11: an intensifier or article right after "not" separates the trope
    # from conditionals and concessions ("If you are not sure, it is best...")
    ("not-x-its-y", "contrast", "S", "en", r"\b(?:is|are|was|were)(?:n't| not)\s+(?:just|only|merely|simply|about|a|an|the) [^.?!\n]{1,50}?[,;:—–]\s*(?:it|they|this|that)(?:'s|'re|\s+(?:is|are|was|were))\b", I),
    # "not only X but also Y" is the standard correlative, not the trope
    ("not-just-x", "contrast", "S", "en", r"\bnot (?:just|only|merely|simply) [^.?!\n]{1,80}?[,;—–-]\s*(?:but(?! also\b)|it's|it is|they're|they are)\b", I),
    # removed 2026-11: a generic "not X, but Y" hit human concessions as often as AI text (119 vs 101 documents)
    ("not-x-but-y", "contrast", "S", "en", r"\b(?:it|this|that)(?:'s| is| was) not (?:about |just |only )?[^.?!\n]{1,60}\.\s+(?:it|this|that)(?:'s| is| was)\b", I),
    ("not-x-but-y", "contrast", "S", "en", r"\bnot because [^.?!\n]{1,60}, but because\b", I),
    ("rather-than-merely", "contrast", "M", "en", r"\brather than (merely|simply|just)\b|\bless (like )?an? \w+ (and|than) more (like )?an?\b", I),
    ("countdown", "contrast", "M", "any", r"\b(Not|Non) (an? |the |un |una |il |la )?\w+\.\s+(Not|Non) (an? |the |un |una |il |la )?\w+\.", 0),
    # calibrated 2026-11: "non è X, ma Y" is an ordinary concession in Italian news (Il Post, DICE);
    # the trope repeats the verb ("non è X, è Y") or the preposition ("non si tratta di X, ma di Y")
    ("not-x-its-y", "contrast", "S", "it", r"\b[Nn]on (?:è|era|fu|sono|erano)(?: solo| soltanto| semplicemente| più)? [^.;?!\n]{1,50}?[,;:—–]\s*(?:è|era|fu|sono|erano)\b", 0),
    ("not-x-but-y", "contrast", "S", "it", r"\b[Nn]on si tratta (?:solo |soltanto |semplicemente )?di [^.?!\n]{1,60}?[,;:]?\s*(?:ma|bensì) (?:anche )?di\b", 0),
    ("not-x-but-y", "contrast", "S", "it", r"\b[Nn]on (?:è|era|fu) (?:solo |soltanto )?[^.?!\n]{1,60}\.\s+(?:È|Era|Fu)\b", 0),
    ("non-solo-ma-anche", "contrast", "W", "it", r"\bnon solo\b[^.?!\n]{1,80}\bma anche\b", I),

    # suspense: staged reveals and false drama
    ("staged-opener", "suspense", "S", "en", r"\b(Here's the (thing|kicker|catch|twist)|Let's (dive|delve) in(to)?|Let's break (it|this) down|Let's unpack|Buckle up)\b", I),
    ("staged-opener", "suspense", "S", "it", r"\b(Diamo un'occhiata( più da vicino)?|Scopriamo insieme|Vediamo insieme|Immergiamoci|Analizziamo (insieme|nel dettaglio))\b", I),
    ("self-question", "suspense", "M", "any", r"(?:^|(?<=[.!?]\s))[A-ZÀ-Ý][^.?!\n]{0,50}\?\s+[A-ZÀ-Ý][\w'’-]*(?:\s[\w'’-]+){0,2}[.!]", M),
    ("false-candor", "suspense", "M", "en", r"\b(To be clear|Let's be (honest|real)|Make no mistake|The truth is|The reality is|Spoiler( alert)?:|And yes, )", 0),
    ("false-candor", "suspense", "M", "it", r"\b([Dd]iciamolo chiaramente|[Ll]a verità è che|[Ee]cco il punto|[Ii]l punto è (un altro|questo)|[Mm]a c'è un problema|[Uu]na cosa è certa)\b", 0),

    # significance: inflated importance
    ("inflated", "significance", "M", "en", r"\b(pivotal (moment|role)|marking a (pivotal|significant|key|new)|setting the stage|(ever-)?evolving landscape|indelible mark|stands as a testament|a testament to|plays? a (crucial|pivotal|vital|key|significant) role|rich tapestry|in today's (fast-paced|digital|ever-changing|modern)|navigat(e|ing) the complexities|serves as a (stark |powerful )?reminder|deeply rooted|unlock(s|ing)? (the |its |their )?(full )?potential|game[- ]chang(er|ing)|paradigm shift)\b", I),
    ("inflated", "significance", "M", "it", r"\b(nell'attuale panorama|nel panorama (attuale|odierno|digitale|contemporaneo)|in un mondo (in continua evoluzione|sempre più|frenetico)|nel mondo (frenetico|odierno)|nel contesto odierno|riveste un ruolo (fondamentale|cruciale|chiave|centrale)|gioca un ruolo (cruciale|fondamentale|chiave)|punto di svolta|un vero e proprio|nel cuore (di|del|della)|navigare (la complessità|l'incertezza)|un (vivace )?mosaico|sfide e opportunità|funge da|come potente promemoria)\b", I),
    ("importance-flag", "significance", "M", "en", r"\b(this matters|matters because|why (this|it) matters|the distinction matters|and that matters|this is (crucial|important) because|it's (crucial|important|essential) to (note|remember|understand))\b", I),
    ("importance-flag", "significance", "M", "it", r"\b([Èè] importante (notare|sottolineare|ricordare)|[Vv]ale la pena (sottolineare|ricordare|notare)|[Èè] fondamentale (considerare|sottolineare|ricordare)|[Ee] questo conta|[Ee]d è (esattamente|proprio) questo il punto|[Ee]cco perché [^.?!\n]{0,40} è (così )?importante)\b", 0),
    ("ing-tail", "significance", "M", "en", r",\s+(highlighting|underscoring|emphasizing|reflecting|symbolizing|showcasing|fostering|ensuring|cementing|solidifying|contributing to|paving the way)\b", I),
    ("ing-tail", "significance", "M", "it", r",\s+(sottolineando|dimostrando|testimoniando|evidenziando|contribuendo a|consolidando|rafforzando|favorendo)\b", I),
    ("tradeoff-denial", "significance", "M", "en", r"\bwithout (sacrificing|compromising|losing|giving up)\b", I),
    ("copula-avoidance", "significance", "M", "en", r"\b(serves as|stands as|boasts (a|an|over|more)|functions as a)\b", I),
    ("promotional", "significance", "M", "en", r"\b(nestled|in the heart of|breathtaking|world-class|state-of-the-art|cutting-edge|diverse array|vibrant (community|culture|city|scene)|must-see|revolutionary)\b", I),
    ("promotional", "significance", "M", "it", r"\b(all'avanguardia|mozzafiato|di livello mondiale|un'ampia gamma di|imperdibile|rivoluzionari[oa])\b", I),

    # attribution: vague sources and hedges
    ("vague-attribution", "attribution", "M", "en", r"\b(Experts (argue|say|believe|note|agree)|Observers have|Industry (reports|experts|observers)|Critics (argue|say)|Many (experts|believe|argue)|Studies (show|suggest)|Research (shows|suggests))\b", 0),
    ("vague-attribution", "attribution", "M", "it", r"\b([Gg]li esperti (sostengono|affermano|ritengono)|[Ss]econdo (molti|diversi) esperti|[Ss]tudi (dimostrano|mostrano|suggeriscono)|[Mm]olti (ritengono|sostengono))\b", 0),
    ("source-gap", "attribution", "M", "en", r"\b(not widely documented|in the provided sources|based on (the )?available information|while specific details are limited)\b", I),
    ("stacked-hedge", "attribution", "M", "en", r"\b(could|may|might) (potentially|possibly|arguably|perhaps)\b|\barguably (perhaps|potentially)\b", I),
    ("stacked-hedge", "attribution", "M", "it", r"\b(potrebbe|potrebbero) (potenzialmente|eventualmente|forse)\b", I),

    # framing: signposting and talk about the text
    ("signposted-ending", "framing", "M", "en", r"(?:^|(?<=[.!?]\s))(In conclusion|In summary|To summarize|To sum up|All in all|The bottom line|At the end of the day)\b", M),
    ("signposted-ending", "framing", "M", "it", r"(?:^|(?<=[.!?]\s))(In conclusione|In sintesi|In definitiva|Alla fine dei conti|Per concludere|Riassumendo|Non ci resta che)\b", M),
    ("meta-text", "framing", "M", "en", r"\b(In this (article|post|guide|section),? (we|I)('ll| will)|This (article|post|guide) (will )?(explores?|covers?|walks?)|Let's (explore|take a closer look)|the table below (shows|compares))\b", I),
    ("meta-text", "framing", "M", "it", r"\b(In questo (articolo|post|testo|approfondimento),? (vedremo|esploreremo|analizzeremo|scopriremo))\b", I),
    ("filler-transition", "framing", "M", "en", r"(?:^|(?<=[.!?]\s))(It's worth noting|It is worth noting|Notably|Importantly|Interestingly|It's important to note|It is important to (note|remember))\b", M),
    ("analogy-opener", "framing", "M", "en", r"\b(Think of it (as|like)|Imagine a world (where|in which)|Picture this)\b", I),
    ("analogy-opener", "framing", "M", "it", r"\b(Immagina un mondo|Pensalo come|Immagina di)\b", I),

    # formatting: markdown tells
    ("bold-lead-bullet", "formatting", "M", "any", r"^\s*(?:[-*+]|\d+\.)\s+\*\*[^*\n]{1,60}(?::\*\*|\*\*\s*[:—–-])", M),
    ("emoji-marker", "formatting", "M", "any", r"^(?:#{1,6}\s*|\s*[-*+]\s+)[\U0001F300-\U0001FAFF☀-➿✅✨]", M),

    # punctuation: dashes, symbols, spacing, accents
    ("em-dash", "punctuation", "M", "any", r"\s?—\s?", 0),
    ("en-dash-as-dash", "punctuation", "M", "en", r"(?<=\w) – (?=\w)", 0),
    ("hyphen-as-dash", "punctuation", "M", "any", r"(?<=[^\W\d_]) - (?=[^\W\d_])", 0),
    ("exclamation-stack", "punctuation", "M", "any", r"[!?]{2,}", 0),
    ("symbol", "punctuation", "W", "any", r"[→⇒➜➔➤▶•✓✔★⚡](?!\s*$)", M),
    ("colon-capital", "punctuation", "W", "it", r":\s+[A-ZÀ-Ý][a-zà-ÿ]+", 0),
]

# Unambiguous corrections applied by `scan.py fix`. (rule, lang, pattern, replacement)
FIXES = [
    ("accent-error", "it", r"\b([Pp]erch|[Pp]oich|[Aa]ffinch|[Bb]ench|[Gg]iacch|[Ss]icch|[Ff]inch|[Nn]ench|[Cc]osicch|[Pp]urch|[Aa]nzich)è\b", r"\1é"),
    ("accent-error", "it", r"\b([Nn]|[Ss])è\b", lambda m: m.group(1) + "é"),
    ("accent-error", "it", r"\b([Pp])ò\b", r"\1o'"),
    ("accent-error", "it", r"\b([Qq])ual'(è|era)\b", r"\1ual \2"),
    ("accent-error", "it", r"(^|(?<=[.!?]\s))E'(?=\s)", "È"),
    # exactly two spaces, one gap per line; indented lines and wider gaps are alignment
    ("double-space", "any", r"^(?! {4}|\t)(?!(?:.*\S {2,}\S){2})(.*?[^\s.!?:\ue000])  (?=[^\s\ue000])", r"\1 "),
    ("space-after-period", "any", r"(?<=[a-zà-ÿ]{2}[.!?])(?=[A-ZÀ-Ý][a-zà-ÿ])", " "),
    ("space-before-punct", "any", r"(?<=[^\W_]) +(?=[,;.!?](\s|$))", ""),
    ("space-after-comma", "any", r"(?<=[^\W\d_]),(?=[^\W\d_])", ", "),
]

CONNECTIVES = {
    "en": r"(Additionally|Moreover|Furthermore|However|Ultimately|Overall|Consequently|Importantly)\b",
    "it": r"(Inoltre|Tuttavia|Pertanto|In ogni caso|Di conseguenza|Per questo motivo|Allo stesso modo|Detto questo|Infine)\b",
}
TRIAD = {
    "en": r"\b[\w'-]+(?: [\w'-]+){0,2}, [\w'-]+(?: [\w'-]+){0,2},? (?:and|or) [\w'-]+\b",
    "it": r"\b[\w'-]+(?: [\w'-]+){0,2}, [\w'-]+(?: [\w'-]+){0,2} (?:e|o|ed) [\w'-]+\b",
}
MINOR_EN = set("a an the and or but nor for of on in at to by up as is are be vs via with from into onto over per".split())
STOP = {
    "en": set("the and of to is that it for with as was on are be this by not".split()),
    "it": set("il la di che è e per un una non con del della sono come gli le si".split()),
}
STYLE_CATEGORIES = {"punctuation", "formatting"}  # style rules: enforced, never combined
CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")
_calibration = {}


def calibration():
    """Tiers and thresholds measured by scripts/calibrate.py on human and AI corpora (optional file)."""
    if "data" not in _calibration:
        data = None
        if os.path.exists(CALIBRATION_FILE) and not os.environ.get("SUPAH_PROSE_NO_CALIBRATION"):
            with open(CALIBRATION_FILE, encoding="utf-8") as f:
                data = json.load(f)
        _calibration["data"] = data
    return _calibration["data"]


def calibrated_tier(rule, lang, tier):
    cal = calibration()
    return (cal or {}).get("rules", {}).get(f"{rule}/{lang}", {}).get("tier", tier)


def length_bucket(words):
    return "<150" if words < 150 else "150-400" if words < 400 else "400-1000" if words < 1000 else ">1000"


def calibration_thresholds(lang, words):
    """Bucket threshold when calibrated, else the language-wide one ("*"), else the designed default."""
    by_lang = (calibration() or {}).get("metrics", {}).get(lang, {})
    merged = dict(by_lang.get("*", {}))
    merged.update(by_lang.get(length_bucket(words), {}))
    return merged


MIN_WORDS = 300
THRESHOLDS = {  # metric -> (limit, direction)
    "style_words_per_1k": (12, ">"),
    "dash_per_1k": (4, ">"),
    "connective_sentence_share": (0.20, ">"),
    "triads_per_1k": (5, ">"),
    "bold_per_1k": (6, ">"),
    "sentence_length_cv": (0.40, "<"),
    "short_closer_share": (0.30, ">"),
}


def load_words(name):
    path = os.path.join(HERE, "lexicon", name)
    with open(path, encoding="utf-8") as f:
        return {l.strip().lower() for l in f if l.strip() and not l.startswith("#")}


def mask(text):
    """Blank out front matter, code, URLs and HTML comments, keeping offsets."""
    def blank(m):
        return re.sub(r"[^\n]", "\ue000", m.group(0))  # private-use filler: not space, not word
    text = re.sub(r"\A---\n.*?\n---\n", blank, text, flags=re.S)
    text = re.sub(r"^(```|~~~).*?^\1[^\n]*$", blank, text, flags=re.S | re.M)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(r"`[^`\n]+`", blank, text)
    text = re.sub(r"https?://\S+", blank, text)
    return text


def detect_lang(text):
    words = re.findall(r"[a-zàèéìòù']+", text.lower())
    score = {k: sum(w in v for w in words) for k, v in STOP.items()}
    return max(score, key=score.get)


def sentences(text):
    # headings, table rows and link-only lines are labels, not sentences
    flat = re.sub(r"^\s*(#{1,6}\s.*|\|.*|\[[^\]]*\]\([^)]*\)\s*)$", "", text, flags=M)
    flat = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", flat, flags=M)
    parts = re.split(r"(?<=[.!?…])\s+(?=[\"“«(]?[A-ZÀ-Ý0-9])|\n\s*\n", flat)
    return [p.strip() for p in parts if re.search(r"\w", p)]


def line_col(text, pos):
    line = text.count("\n", 0, pos) + 1
    return line, pos - (text.rfind("\n", 0, pos) + 1) + 1


QUOTE_PAIRS = (("“", "”"), ("«", "»"))


def context_window(raw, start, end):
    """Five tokens either side of a hit: the unit verdicts are learned on."""
    left = re.findall(r"\S+", raw[max(0, start - 80):start])[-5:]
    right = re.findall(r"\S+", raw[end:end + 80])[:5]
    return " ".join(left + ["[" + raw[start:end] + "]"] + right).replace("\n", " ")


def gate(raw, start, end, rule, cat, lang):
    """Contexts where a hit is not the author's own prose or is a legitimate use."""
    ls = raw.rfind("\n", 0, start) + 1
    le = raw.find("\n", end)
    line = raw[ls:len(raw) if le < 0 else le]
    before, after = line[:start - ls], line[start - ls + (end - start):]
    if line.lstrip().startswith(">"):
        return "auto:quote"
    if before.count('"') % 2 == 1 and '"' in after:
        return "auto:quote"
    for opener, closer in QUOTE_PAIRS:
        if before.rfind(opener) > before.rfind(closer) and closer in after:
            return "auto:quote"
    if cat == "vocabulary" and line.lstrip().startswith("#"):
        return "auto:heading"
    if rule == "marked-word" and raw[start].isupper() and not re.search(r"(^\W*|[.!?:]\s+)$", before):
        return "auto:name"
    if rule == "em-dash" and lang == "it" and re.match(r"\s*[—–]\s", line):
        return "auto:dialogue"
    return None


def scan_file(path, lang_opt, keep, gates=True, model=None):
    with open(path, encoding="utf-8") as f:
        return scan_text(f.read(), lang_opt, keep, gates=gates, model=model, path=path)


def scan_text(raw, lang_opt, keep, gates=True, model=None, path="<text>"):
    text = mask(raw)
    lang = detect_lang(text) if lang_opt == "auto" else lang_opt
    hits = []

    def add(rule, cat, tier, start, end):
        match = raw[start:end].replace("\n", " ").strip()
        line, col = line_col(raw, start)
        tier = calibrated_tier(rule, lang, tier)
        hit = {"line": line, "col": col, "tier": tier, "category": cat, "rule": rule,
               "match": match[:90], "context": context_window(raw, start, end)}
        hit["kept"] = keep.get((rule, match.lower())) or (gate(raw, start, end, rule, cat, lang) if gates else None)
        if not hit["kept"] and model:
            hit["tier"], hit["kept"] = learn.apply(model, hit, lang)
        hits.append(hit)

    for rule, cat, tier, rlang, pattern, flags in RULES:
        if rlang in (lang, "any"):
            for m in re.finditer(pattern, text, flags):
                add(rule, cat, tier, m.start(), m.end())

    for rule, rlang, pattern, _ in FIXES:
        if rlang in (lang, "any"):
            for m in re.finditer(pattern, text, M):
                add(rule, "punctuation", "M", m.start(), max(m.end(), m.start() + 1))
    if text.count('"') >= 2 and re.search("[“”«»]", text):
        pos = re.search("[“”«»]", text).start()
        add("quote-mix", "punctuation", "W", pos, pos + 1)

    demoted = set((calibration() or {}).get("demoted_words", {}).get(lang, []))
    marked = load_words(f"{lang}-marked.txt") - demoted  # words common in human text count as density only
    style = load_words(f"{lang}-style.txt") | demoted
    words = list(re.finditer(r"[^\W\d_]+(?:['’][^\W\d_]+)?", text))
    n_words = max(1, len(words))
    style_count = 0
    marked_hits = [w for w in words if w.group(0).lower() in marked]
    # calibrated: a single marked word is ordinary human writing; the tell is several distinct ones
    marked_min = (calibration() or {}).get("marked_min", {}).get(lang, 1)
    marked_tier = "M" if len({w.group(0).lower() for w in marked_hits}) >= marked_min else "W"
    for w in words:
        lw = w.group(0).lower()
        if lw in marked:
            add("marked-word", "vocabulary", marked_tier, w.start(), w.end())
        elif lw in style:
            style_count += 1

    for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, M):
        title = m.group(2).strip()
        tokens = [t for t in re.findall(r"[^\W\d_][\w'’-]*", title)]
        rest = tokens[1:]
        if lang == "en":
            content = [t for t in rest if t.lower() not in MINOR_EN]
            caps = [t for t in content if t[0].isupper()]
            if len(content) >= 2 and len(caps) == len(content):
                add("title-case", "formatting", "M", m.start(2), m.end(2))
        else:
            caps = [t for t in rest if t[0].isupper() and not t.isupper()]
            if len(caps) >= 2:
                add("title-case", "formatting", "W", m.start(2), m.end(2))

    sents = sentences(text)
    lengths = [len(re.findall(r"\w+", s)) for s in sents]
    run, cursor = 0, 0
    for s, n in zip(sents, lengths):
        pos = text.find(s, cursor)
        cursor = pos + len(s) if pos >= 0 else cursor
        is_fragment = n <= 3 and re.search(r"[^\W\d_]{2}", s) and not s.endswith(":")
        run = run + 1 if is_fragment else 0
        if run == 2 and pos >= 0:
            add("fragment-run", "rhythm", "M", pos, pos + len(s))

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if len(sentences(p)) >= 3
                  and not re.match(r"\s*([-*+]|\d+\.|#|\|)", p)]
    closers = sum(1 for p in paragraphs if len(re.findall(r"\w+", sentences(p)[-1])) <= 6)
    em = text.count("—") + len(re.findall(r" [–-] ", text))
    conn = sum(1 for s in sents if re.match(CONNECTIVES[lang], s))

    def per_1k(count):  # densities mean little on short texts
        return round(count * 1000 / n_words, 1) if n_words >= MIN_WORDS else None

    metrics = {
        "words": n_words,
        "style_words_per_1k": per_1k(style_count),
        "dash_per_1k": per_1k(em),
        "connective_sentence_share": round(conn / len(sents), 2) if len(sents) >= 10 else None,
        "triads_per_1k": per_1k(len(re.findall(TRIAD[lang], text))),
        "bold_per_1k": per_1k(len(re.findall(r"\*\*[^*\n]+\*\*", text))),
        "sentence_length_cv": round(statistics.pstdev(lengths) / statistics.mean(lengths), 2)
        if len(lengths) >= 15 else None,
        "short_closer_share": round(closers / len(paragraphs), 2) if len(paragraphs) >= 4 else None,
    }
    flags = []
    calibrated = calibration_thresholds(lang, n_words)
    for key, (limit, op) in THRESHOLDS.items():
        limit = calibrated.get(key, limit)
        v = metrics.get(key)
        if v is not None and (v > limit if op == ">" else v < limit):
            flags.append(key)
    kept_flags = [f for f in flags if ("metric", f) in keep]
    flags = [f for f in flags if f not in kept_flags]
    # calibrated combined evidence: without an S hit, M hits are required fixes only when enough
    # distinct M rules agree; an isolated one stays visible as W (scripts/calibrate.py, evidence_min)
    evidence_min = (calibration() or {}).get("evidence_min", {}).get(lang, 1)
    authorship = [h for h in hits if not h["kept"] and h["category"] not in STYLE_CATEGORIES]
    strong = any(h["tier"] == "S" for h in authorship)
    medium_rules = {h["rule"] for h in authorship if h["tier"] == "M"}
    if not strong and len(medium_rules) < evidence_min:
        for h in authorship:
            if h["tier"] == "M":
                h["tier"], h["isolated"] = "W", True
    hits.sort(key=lambda h: (h["line"], h["col"]))
    return {"file": path, "lang": lang, "hits": hits, "metrics": metrics,
            "flags": flags, "kept_flags": kept_flags}


def load_keep(path):
    keep = {}
    if path:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3 and not line.startswith("#"):
                    keep[(parts[0], parts[1].strip().lower())] = parts[2]
    return keep


def print_report(result):
    hits = result["hits"]
    open_hits = [h for h in hits if not h["kept"] and h["tier"] in ("S", "M")]
    print(f"## {result['file']} · lang {result['lang']} · {result['metrics']['words']} words\n")
    if hits:
        print("| line | tier | category | rule | match | kept |\n|---|---|---|---|---|---|")
        for h in hits:
            match = h["match"].replace("|", "\\|")
            note = h["kept"] or ("isolated" if h.get("isolated") else "")
            print(f"| {h['line']}:{h['col']} | {h['tier']} | {h['category']} | {h['rule']} | {match} | {note} |")
    else:
        print("No pattern hits.")
    print("\n| metric | value | limit | flag |\n|---|---|---|---|")
    for key, value in result["metrics"].items():
        limit = THRESHOLDS.get(key)
        lim = f"{limit[1]} {limit[0]}" if limit else ""
        print(f"| {key} | {'n/a' if value is None else value} | {lim} | {'FLAG' if key in result['flags'] else 'kept' if key in result['kept_flags'] else ''} |")
    by_tier = {t: sum(1 for h in open_hits if h["tier"] == t) for t in ("S", "M")}
    kept = sum(1 for h in hits if h["kept"])
    print(f"\nOpen: S {by_tier['S']} · M {by_tier['M']} · flagged metrics {len(result['flags'])} · kept {kept}\n")
    return bool(open_hits or result["flags"])


FACT_PATTERNS = [
    ("number", r"(?<![\w.])\d[\d.,:/%]*\d%?|(?<![\w.])\d%?"),
    ("url", r"https?://[^\s)\]>\"']+[^\s)\]>\"'.,;:]"),
    ("code", r"`[^`\n]+`"),
    ("quote", r"[\"“«][^\"”»\n]{3,80}[\"”»]"),
    ("name", r"(?<=[a-zà-ÿ,;:] )[A-ZÀ-Ý][\w'’-]+(?: [A-ZÀ-Ý][\w'’-]+)*"),
]


def compare(original, rewrite):
    a = open(original, encoding="utf-8").read()
    b = open(rewrite, encoding="utf-8").read()
    missing = []
    for kind, pattern in FACT_PATTERNS:
        for token in sorted(set(re.findall(pattern, a))):
            if token not in b:
                missing.append((kind, token))
    if missing:
        print("| kind | missing from rewrite |\n|---|---|")
        for kind, token in missing:
            print(f"| {kind} | {token.replace('|', chr(92) + '|')} |")
    print(f"\nMissing: {len(missing)}")
    return 1 if missing else 0


def fix(path, lang_opt):
    with open(path, encoding="utf-8", newline="") as f:
        original = f.read()
    newline = "\r\n" if "\r\n" in original else "\n"  # written back in the file's own style
    raw = original.replace("\r\n", "\n")
    counts = {}
    for _ in range(5):  # overlapping edits land on the next pass
        text = mask(raw)
        lang = detect_lang(text) if lang_opt == "auto" else lang_opt
        edits = []
        for rule, rlang, pattern, repl in FIXES:
            if rlang in (lang, "any"):
                for m in re.finditer(pattern, text, M):
                    new = m.expand(repl) if isinstance(repl, str) else repl(m)
                    edits.append((m.start(), m.end(), new, rule))
        if not edits:
            break
        edits.sort()
        out, last = [], 0
        for start, end, new, rule in edits:
            if start < last:
                continue
            out.append(raw[last:start] + new)
            last = end
            counts[rule] = counts.get(rule, 0) + 1
        out.append(raw[last:])
        raw = "".join(out)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(raw.replace("\n", newline))
    for rule, n in sorted(counts.items()):
        print(f"{rule}: {n}")
    print(f"Fixed: {sum(counts.values())} in {path}")
    return 0


def list_rules():
    rows = []
    for rule, cat, tier, lang, _, _ in RULES:
        rows.append((rule, cat, tier, lang))
    for rule, lang, _, _ in FIXES:
        rows.append((rule, "punctuation", "M, auto-fixed by `fix`", lang))
    rows += [  # computed in scan_file rather than by a single pattern
        ("marked-word", "vocabulary", "M", "en, it"),
        ("title-case", "formatting", "M (en), W (it)", "en, it"),
        ("fragment-run", "rhythm", "M", "any"),
        ("quote-mix", "punctuation", "W", "any"),
    ]
    print("| rule | category | tier | lang |\n|---|---|---|---|")
    for row in dict.fromkeys(rows):
        print("| " + " | ".join(row) + " |")
    print("\n| metric | flagged when |\n|---|---|")
    for key, (limit, op) in THRESHOLDS.items():
        print(f"| {key} | {op} {limit} |")
    print("\n| lexicon | words |\n|---|---|")
    for name in sorted(os.listdir(os.path.join(HERE, "lexicon"))):
        print(f"| {name} | {len(load_words(name))} |")
    return 0


KEPT_REASONS = {"quote", "voice", "literal", "term", "dialogue"}


def cmd_verdict(argv):
    """Turn a finished sweep into verdicts: kept-file `fp` -> fp, other reasons -> kept,
    a hit gone from the final text -> tell. Hits still present without a keep entry are skipped."""
    p = argparse.ArgumentParser(prog="scan.py verdict")
    p.add_argument("original")
    p.add_argument("final")
    p.add_argument("--keep")
    p.add_argument("--lang", choices=("auto", "en", "it"), default="auto")
    p.add_argument("--source", choices=("model", "human"), default="model")
    a = p.parse_args(argv)
    keep = load_keep(a.keep)
    before = scan_file(a.original, a.lang, {}, model=None)
    after = scan_file(a.final, before["lang"], {}, model=None)
    remaining = {}
    for h in after["hits"]:
        k = (h["rule"], h["match"].lower())
        remaining[k] = remaining.get(k, 0) + 1
    rows, counts = [], {"tell": 0, "kept": 0, "fp": 0}
    for h in before["hits"]:
        if h["kept"]:  # gated (quote, heading, name, dialogue): never reviewed
            continue
        k = (h["rule"], h["match"].lower())
        reason = keep.get(k)
        if reason == "fp":
            label = "fp"
        elif reason in KEPT_REASONS:
            label = "kept"
        elif remaining.get(k, 0) > 0:
            remaining[k] -= 1
            continue
        else:
            label, reason = "tell", "rewritten"
        counts[label] += 1
        rows.append({"lang": before["lang"], "rule": h["rule"], "category": h["category"], "tier": h["tier"],
                     "label": label, "reason": reason, "source": a.source, "match": h["match"],
                     "context": h["context"]})
    learn.record(rows)
    model = learn.rebuild()
    changed = [f"{k}: {r['base']} -> {r['tier']}" for k, r in model["rules"].items() if r["tier"] != r["base"]]
    print(f"Recorded {len(rows)} verdicts (tell {counts['tell']}, kept {counts['kept']}, fp {counts['fp']}) "
          f"in {learn.paths()[0]}")
    print("Tier changes: " + (", ".join(changed) if changed else "none"))
    return 0


def cmd_learn(argv):
    """Rebuild the model from the verdict log and print per-rule precision."""
    argparse.ArgumentParser(prog="scan.py learn").parse_args(argv)
    model = learn.rebuild()
    print(f"{model['verdicts']} verdicts · {len(model['suppress'])} suppressed contexts · "
          f"{len(model['nb'])} trained context classifiers · {learn.paths()[1]}\n")
    print("| rule/lang | verdicts | precision (mean) | 95% lower bound | tier |\n|---|---|---|---|---|")
    for key, r in sorted(model["rules"].items(), key=lambda kv: kv[1]["lower95"]):
        tier = r["tier"] if r["tier"] == r["base"] else f"{r['base']} -> {r['tier']}"
        print(f"| {key} | {r['n']} | {r['mean']:.2f} | {r['lower95']:.2f} | {tier} |")
    return 0


def cmd_audit(argv):
    """Print a random sample of the model's fp verdicts as TSV for a human to confirm."""
    p = argparse.ArgumentParser(prog="scan.py audit")
    p.add_argument("--fraction", type=float, default=0.1)
    a = p.parse_args(argv)
    sample = learn.audit_sample(a.fraction)
    print("# Set label to fp (not a tell), kept, or tell, then: scan.py label <this file>")
    print("label\tlang\trule\tcategory\ttier\tmatch\tcontext")
    for r in sample:
        print("\t".join([r["label"], r["lang"], r["rule"], r["category"], r["tier"], r["match"], r["context"]]))
    return 0


def cmd_label(argv):
    """Record human verdicts from an edited audit file; they override model verdicts."""
    p = argparse.ArgumentParser(prog="scan.py label")
    p.add_argument("file")
    a = p.parse_args(argv)
    rows = []
    with open(a.file, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if line.startswith("#") or parts[0] == "label" or len(parts) < 7:
                continue
            label, lang, rule, cat, tier, match, context = parts[:7]
            if label in ("fp", "kept", "tell"):
                rows.append({"lang": lang, "rule": rule, "category": cat, "tier": tier, "label": label,
                             "reason": "audit", "source": "human", "match": match, "context": context})
    learn.record(rows)
    learn.rebuild()
    print(f"Recorded {len(rows)} human verdicts.")
    return 0


LEARN_COMMANDS = {"verdict": cmd_verdict, "learn": cmd_learn, "audit": cmd_audit, "label": cmd_label}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] in LEARN_COMMANDS:
        return LEARN_COMMANDS[sys.argv[1]](sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "rules":
        return list_rules()
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        p = argparse.ArgumentParser(prog="scan.py fix")
        p.add_argument("files", nargs="+")
        p.add_argument("--lang", choices=("auto", "en", "it"), default="auto")
        a = p.parse_args(sys.argv[2:])
        return max(fix(f, a.lang) for f in a.files)
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        p = argparse.ArgumentParser(prog="scan.py compare")
        p.add_argument("original")
        p.add_argument("rewrite")
        a = p.parse_args(sys.argv[2:])
        return compare(a.original, a.rewrite)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+")
    p.add_argument("--lang", choices=("auto", "en", "it"), default="auto")
    p.add_argument("--keep")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-gates", action="store_true", help="report hits in quotes, headings, names and dialogue too")
    p.add_argument("--no-learn", action="store_true", help="ignore the learned model (rule tiers, suppressions)")
    a = p.parse_args()
    keep = load_keep(a.keep)
    model = None if a.no_learn else learn.load_model()
    results = [scan_file(f, a.lang, keep, gates=not a.no_gates, model=model) for f in a.files]
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        dirty = any(r["flags"] or any(not h["kept"] and h["tier"] in "SM" for h in r["hits"]) for r in results)
    else:
        dirty = any([print_report(r) for r in results])
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())
