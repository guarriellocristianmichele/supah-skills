"""Visible-text views of source files for scan.py. Stdlib only.

A source file (markup, script, locale) is reduced to the text its users read: every other
character becomes FILLER, newlines stay, so offsets, lines and columns match the original file.
Comments, docstrings, developer logs and strings that are code (CSS classes, paths, URLs, SQL,
identifiers) are left out. Each kept span carries a purpose (button, label, error...) inferred from
the tag, attribute, key or call around it.
"""
import os
import re

FILLER = ""

PROSE = {".md", ".mdx", ".markdown", ".txt", ".rst", ".adoc", ".text"}
MARKUP = {".html", ".htm", ".vue", ".svelte", ".astro", ".twig", ".hbs", ".handlebars", ".ejs", ".erb",
          ".njk", ".jinja", ".jinja2", ".liquid", ".mustache"}
SCRIPT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".php", ".rb", ".go", ".java", ".kt",
          ".swift", ".cs", ".dart", ".rs", ".scala"}
LOCALE = {".json", ".yaml", ".yml", ".po", ".pot", ".properties", ".arb", ".strings"}
HASH_COMMENTS = {".py", ".rb", ".php", ".yaml", ".yml"}

# purposes whose text is microcopy: a few words, where rhythm and Title Case rules mean nothing
MICROCOPY = {"button", "link", "label", "placeholder", "alt", "tooltip", "option", "heading", "title",
             "hint", "tab", "menu"}

TAG_PURPOSE = {"button": "button", "a": "link", "label": "label", "legend": "label", "th": "label",
               "h1": "heading", "h2": "heading", "h3": "heading", "h4": "heading", "h5": "heading",
               "h6": "heading", "title": "title", "option": "option", "summary": "label", "caption": "label",
               "figcaption": "text", "p": "text", "li": "text", "td": "text", "blockquote": "text",
               "small": "hint", "dt": "label", "dd": "text"}
ATTR_PURPOSE = {"alt": "alt", "placeholder": "placeholder", "title": "tooltip", "aria-label": "label",
                "aria-description": "hint", "label": "label", "content": "meta", "value": "button",
                "data-tooltip": "tooltip", "helpertext": "hint", "tooltip": "tooltip"}
KEY_HINTS = [("error", "error"), ("warning", "error"), ("success", "message"), ("toast", "message"),
             ("notification", "message"), ("message", "message"), ("confirm", "message"),
             ("placeholder", "placeholder"), ("tooltip", "tooltip"), ("hint", "hint"), ("helper", "hint"),
             ("button", "button"), ("cta", "button"), ("action", "button"), ("submit", "button"),
             ("label", "label"), ("subtitle", "text"), ("title", "heading"), ("heading", "heading"),
             ("headline", "heading"), ("alt", "alt"), ("description", "text"), ("summary", "text"),
             ("body", "text"), ("text", "text"), ("empty", "empty-state"), ("onboarding", "onboarding"),
             ("meta", "meta"), ("seo", "meta"), ("email", "email"), ("subject", "email"), ("tab", "tab"),
             ("menu", "menu"), ("nav", "menu")]
I18N_CALL = re.compile(r"(?:\b(?:i18n\.)?t|\$t|__|_e|_x|esc_html__|esc_attr__|gettext|_|translate|"
                       r"intl\.formatMessage|formatMessage|trans|lang)\s*\(\s*$")
DEV_CALL = re.compile(r"(?:\b(?:console\.\w+|logger\.\w+|log\.(?:debug|info|trace|warn|warning)|logging\.\w+|"
                      r"debug|assert\w*|describe|it|test|expect|require|import|jest\.\w+)\s*\(\s*$"
                      r"|\b(?:import|from|require)\b[^;\n]*$)")
ERROR_CALL = re.compile(r"(?:toast\.error|notify\.error|message\.error|alert|confirm|prompt|"
                        r"throw\s+new\s+\w*Error|raise\s+\w*(?:Error|Exception)|abort|flash)\s*\(\s*$")
MESSAGE_CALL = re.compile(r"(?:toast(?:\.\w+)?|notify(?:\.\w+)?|message\.\w+|snackbar\w*|showMessage|"
                          r"setError|setMessage|print|echo|puts|res\.(?:send|json)|json_response)\s*\(?\s*$")
STOP = set("the and of to is a in for with your you we our this that it be are on not can will "
           "il la di che è e per un una non con del della sono come le si gli lo i tuo tua tuoi suoi "
           "nel alla al da su ci ti vi ha hai".split())
CODEY = re.compile(r"^[\w.:/#%@\[\]()=,;{}<>+*|&!?$^~-]*$")


def kind(path):
    p = path.lower()
    if p.endswith(".blade.php"):
        return "markup"
    ext = os.path.splitext(p)[1]
    if ext in PROSE or not ext:
        return "prose"
    if ext in MARKUP:
        return "markup"
    if ext in SCRIPT:
        return "script"
    if ext in LOCALE:
        return "locale"
    return "prose"


def natural(s):
    """True when a string reads as words for people rather than code."""
    t = s.strip()
    if len(t) < 2 or not re.search(r"[^\W\d_]{2}", t):
        return False
    if re.match(r"^(?:https?:|mailto:|/|\./|\.\./|#[\w-]+$|[\w.-]+\.(?:js|ts|css|png|svg|jpg|json|php|html)$)", t):
        return False
    if re.search(r"\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b", t) and t.upper() == t:
        return False
    words = t.split()
    if len(words) == 1:
        # a single word is text only when capitalised like a label or ending in punctuation ("Salva", "Done!")
        return bool(re.match(r"^[A-ZÀ-Ý][a-zà-ÿ'’]+[.!?…]?$", t))
    if all(CODEY.match(w) for w in words) and not any(w.lower().strip(".,:;!?") in STOP for w in words):
        # "flex items-center gap-2", "user.name asc": no stop word, every token code-shaped
        if not re.search(r"[A-ZÀ-Ý][a-zà-ÿ]+ [a-zà-ÿ]+", t):
            return False
    return True


def purpose_from_key(key):
    k = key.lower()
    for hint, purpose in KEY_HINTS:
        if hint in k:
            return purpose
    return None


def tag_purpose(before):
    """Purpose of text from the innermost tag opened before it."""
    m = None
    for m in re.finditer(r"<\s*([A-Za-z][\w.-]*)\b[^<>]*>", before[-400:]):
        pass
    if not m:
        return "text"
    tag = m.group(1).lower()
    if tag in TAG_PURPOSE:
        return TAG_PURPOSE[tag]
    for hint in ("button", "btn", "link", "label", "title", "heading", "tooltip", "error", "alert", "toast",
                 "hint", "tab", "menu"):
        if hint in tag:
            return purpose_from_key(hint) or "text"
    return "text"


def context_purpose(code_before):
    """Purpose of a string literal from the code right before it."""
    tail = code_before[-160:]
    if DEV_CALL.search(tail):
        return None  # developer-facing: logs, tests, imports
    attr = re.search(r"([\w-]+)\s*=\s*\{?\s*$", tail)
    if attr:
        name = attr.group(1).lower()
        if name in ATTR_PURPOSE:
            return ATTR_PURPOSE[name]
        if name in ("class", "classname", "id", "href", "src", "type", "key", "ref", "style", "name", "for",
                    "role", "rel", "target", "method", "action", "lang", "dir", "width", "height"):
            return None
        return purpose_from_key(name) or "string"
    if ERROR_CALL.search(tail):
        return "error"
    if MESSAGE_CALL.search(tail):
        return "message"
    if I18N_CALL.search(tail):
        return "i18n"
    key = re.search(r"[\"']?([\w-]+)[\"']?\s*[:=]>?\s*$", tail)
    if key:
        return purpose_from_key(key.group(1)) or "string"
    return "string"


def script_spans(raw, ext):
    """String literals worth reading in a script, skipping comments and docstrings."""
    spans, i, n = [], 0, len(raw)
    hash_comments = ext in HASH_COMMENTS
    code = []  # characters of code outside strings and comments, for context
    while i < n:
        c = raw[i]
        if raw.startswith("//", i) and ext not in (".py",):
            j = raw.find("\n", i)
            i = n if j < 0 else j
            continue
        if raw.startswith("/*", i):
            j = raw.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "#" and hash_comments:
            j = raw.find("\n", i)
            i = n if j < 0 else j
            continue
        if ext == ".py" and (raw.startswith('"""', i) or raw.startswith("'''", i)):
            q = raw[i:i + 3]
            j = raw.find(q, i + 3)
            i = n if j < 0 else j + 3  # docstrings and block strings: documentation, not UI
            continue
        if c in "\"'`":
            j, start = i + 1, i + 1
            while j < n and raw[j] != c:
                if raw[j] == "\\":
                    j += 1
                elif raw[j] == "\n" and c != "`":
                    break
                j += 1
            content = raw[start:j]
            if c == "`":
                content = re.sub(r"\$\{[^}]*\}", lambda m: " " * len(m.group(0)), content)
            purpose = context_purpose("".join(code))
            if purpose and natural(content):
                spans.append((start, j, purpose))
            code.append(" ")
            i = j + 1
            continue
        code.append(c)
        i += 1
    # JSX / template text between tags in script files
    if ext in (".jsx", ".tsx", ".js", ".ts", ".php"):
        spans += markup_text_spans(raw, blanked=strings_and_comments_blanked(raw, ext))
    return spans


def strings_and_comments_blanked(raw, ext):
    out = list(raw)
    i, n = 0, len(raw)
    while i < n:
        if raw.startswith("//", i) or raw.startswith("/*", i) or (raw[i] == "#" and ext in HASH_COMMENTS):
            if raw.startswith("/*", i):
                close = raw.find("*/", i + 2)
                end = n if close < 0 else close + 2
            else:
                close = raw.find("\n", i)
                end = n if close < 0 else close
            for k in range(i, end):
                if out[k] != "\n":
                    out[k] = " "
            i = end
            continue
        if raw[i] in "\"'`":
            q, j = raw[i], i + 1
            while j < n and raw[j] != q and not (raw[j] == "\n" and q != "`"):
                j += 2 if raw[j] == "\\" else 1
            for k in range(i, min(j + 1, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j + 1
            continue
        i += 1
    return "".join(out)


def markup_text_spans(raw, blanked=None):
    """Text between tags, and readable attribute values, in markup."""
    src = blanked if blanked is not None else raw
    hidden = []
    for pat in (r"<!--.*?-->", r"<script\b.*?</script\s*>", r"<style\b.*?</style\s*>",
                r"\{\{.*?\}\}", r"\{%.*?%\}", r"\{#.*?#\}", r"<\?(?:php|=)?.*?\?>", r"@\w+\([^)]*\)"):
        for m in re.finditer(pat, src, re.S | re.I):
            hidden.append((m.start(), m.end()))

    def is_hidden(a, b):
        return any(s <= a and b <= e for s, e in hidden)
    spans = []
    # text counts only after a real tag (<p>, </div>, <>), never after an arrow or a comparison
    for m in re.finditer(r"(?:<[A-Za-z][\w.:-]*(?:\s[^<>]*?)?/?>|</[A-Za-z][\w.:-]*\s*>|<>|</>)([^<>]+)(?=<)", src):
        a, b = m.start(1), m.end(1)
        text = raw[a:b]
        if is_hidden(a, b) or not re.search(r"[^\W\d_]{2}", text):
            continue
        # blank {expressions} inside JSX or template text, keep the readable runs around them
        clean = text
        while re.search(r"\{[^{}]*\}", clean):
            clean = re.sub(r"\{[^{}]*\}", lambda e: "\x00" * len(e.group(0)), clean)
        for run in re.finditer(r"[^\s\x00{}][^\x00{}]*[^\s\x00{}]|[^\s\x00{}]", clean):
            ra, rb = a + run.start(), a + run.end()
            if re.search(r"[^\W\d_]{2}", raw[ra:rb]):
                spans.append((ra, rb, tag_purpose(src[:a])))
    if blanked is None:
        for m in re.finditer(r"\b([\w:-]+)\s*=\s*([\"'])(.*?)\2", raw, re.S):
            name = m.group(1).lower().split(":")[-1]
            if name in ATTR_PURPOSE and not is_hidden(m.start(3), m.end(3)) and natural(m.group(3)):
                spans.append((m.start(3), m.end(3), ATTR_PURPOSE[name]))
        # strings inside <script> blocks of single-file components
        for m in re.finditer(r"<script\b[^>]*>(.*?)</script\s*>", raw, re.S | re.I):
            body = m.group(1)
            for a, b, p in script_spans(body, ".ts"):
                spans.append((m.start(1) + a, m.start(1) + b, p))
    return spans


def locale_spans(raw, ext):
    spans = []
    if ext in (".po", ".pot"):
        for m in re.finditer(r'^msgstr(?:\[\d+\])?\s+"(.*)"\s*$', raw, re.M):
            if natural(m.group(1)):
                spans.append((m.start(1), m.end(1), "i18n"))
        return spans
    if ext in (".properties", ".strings"):
        for m in re.finditer(r'^\s*"?([\w.\-]+)"?\s*[=:]\s*"?(.*?)"?;?\s*$', raw, re.M):
            if natural(m.group(2)):
                spans.append((m.start(2), m.end(2), purpose_from_key(m.group(1)) or "i18n"))
        return spans
    if ext in (".yaml", ".yml"):
        for m in re.finditer(r'^\s*([\w.\-]+)\s*:\s*(["\']?)(.+?)\2\s*$', raw, re.M):
            if not m.group(3).startswith(("#", "|", ">", "&", "*")) and natural(m.group(3)):
                spans.append((m.start(3), m.end(3), purpose_from_key(m.group(1)) or "i18n"))
        return spans
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', raw):  # JSON / ARB: values only
        if not m.group(1).startswith("@") and natural(m.group(2)):
            spans.append((m.start(2), m.end(2), purpose_from_key(m.group(1)) or "i18n"))
    return spans


def view(raw, path):
    """Return (text, spans, kind). For prose, text is None: the caller applies its own masking."""
    k = kind(path)
    if k == "prose":
        return None, [], k
    ext = ".php" if path.lower().endswith(".blade.php") else os.path.splitext(path.lower())[1]
    if k == "markup":
        spans = markup_text_spans(raw)
    elif k == "script":
        spans = script_spans(raw, ext)
    else:
        spans = locale_spans(raw, ext)
    spans = sorted(set(spans))
    out = [ch if ch == "\n" else FILLER for ch in raw]
    for a, b, _ in spans:
        out[a:b] = list(raw[a:b])
    for a, b, _ in spans:  # a boundary between two texts reads as a line break, so no rule matches across
        if a > 0 and out[a - 1] == FILLER:
            out[a - 1] = "\n"
        if b < len(out) and out[b] == FILLER:
            out[b] = "\n"
    return "".join(out), spans, k


def purpose_at(spans, pos):
    for a, b, p in spans:
        if a <= pos < b:
            return p
    return None
