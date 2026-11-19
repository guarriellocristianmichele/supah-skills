#!/usr/bin/env python3
"""Deterministic scanner for design reflexes in frontend source. Stdlib only.

  designscan.py [--json] [--keep FILE] FILE...
      List every catalogued reflex with line, rule, category, tier and context.
      Exit 0 when nothing is left to resolve (no open S or M hit), else 1. A FILE that does not
      exist, is a directory or cannot be read is one line on stderr, the others are still scanned
      and reported, and the exit is 2, which wins over 1 (look at the report for hits).
  designscan.py rules
      Print every rule with category and tier.
  designscan.py surfaces [ROOT] [--out FILE]
      Inventory of surfaces as JSON: the framework detected from package.json (Next.js, Nuxt,
      SvelteKit, Astro, react-router), each route with the files only it reaches, the shared unit
      (files reached by several routes or by none), or units by directory when no route convention
      matches. Every frontend file is in exactly one unit. With --out the JSON goes to FILE and
      one line is printed: surfaces, shared units, frontend files and the framework.
  designscan.py --surfaces INVENTORY --out HITS [--keep FILE]
      Scan every file of the inventory in one run, write the results grouped by unit to HITS
      and print a summary per unit plus the duplication groups. A report, not a gate: exit 0 once
      HITS is written, open hits or not (reconcile and a FILE rescan gate them). A file of the
      inventory deleted since is one line on stderr, left out of HITS, and the exit is 2.
      HITS records the commit and, as dirty, the scanned files with uncommitted changes.
  designscan.py hits HITS [UNIT]
      The summary again, or one unit's results as JSON without its duplication hits. A route
      unit is found without its leading slash too (pricing for /pricing), and through Git Bash's
      rewrite of /pricing into C:/Program Files/Git/pricing.
  designscan.py reconcile FINDINGS HITS [--keep FILE] [--json] [--write]
      Compare a fresh hits file with the ledger's findings.md and keep file: each finding is
      fixed (its hit is gone), open (still there) or resolved (kept since), with the status it
      takes; hits no finding or keep line covers are new. Exit 1 while any is open or new.
      --write rewrites FINDINGS in place: each status, the line of a single-file Where:, and
      Scanned: set to the fresh commit (<sha>-dirty for a finding in an uncommitted file; a
      duplication group over several files names the uncommitted ones: <sha>-dirty (a.tsx)).
  designscan.py verdict ORIG FILE [ORIG FILE...] [--keep FILE]
      Record a verdict for every hit in ORIG: fixed in FILE = reflex, kept = chosen
      (or reflex for reason `handoff`), kept with reason `fp` = fp. Appends to the verdict log.
  designscan.py verdict --judged FINDINGS [--keep FILE]
      Record an audit's judgments once: each scanner finding not rejected = reflex, each keep
      line = fp, reflex (handoff) or chosen. Prints each rule's progress toward 30 verdicts.
  designscan.py learn | audit [--fraction F] [--rule RULE] | label FILE | export [--out FILE]
      Rebuild the learned model and print each rule's precision; sample the model's fp verdicts
      for a human to confirm; record that confirmed file; write per-rule counts (no matches) to
      attach to an issue. The model lives in SUPAH_DESIGN_HOME (default: the user config folder,
      supah-skills/design); --no-learn ignores it in a file scan (ADR 0018).

A reflex is a design choice that appears whatever the subject. The scanner reads HTML, CSS,
SCSS, JSX/TSX, Vue, Svelte and Astro source: class strings (class, className, :class, cn,
clsx, twMerge, cva), CSS declarations and style objects, and visible text. It never renders.
A file that is not UTF-8 is read as cp1252 (or Latin-1), and the scan names it with the encoding.

Tiers: S = one hit is enough; M = fix unless there is a keep reason; W = review only.
Keep file: TSV lines `rule<TAB>matched text<TAB>reason`; matching hits count as resolved.
The scanner finds candidates; whether a hit is a reflex is decided by reading it (ADR 0003).
"""
import argparse
import bisect
import json
import os
import posixpath
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import learn  # noqa: E402  (a copy of ai-slop-prose's learn.py, kept equal by release.py --sync)
EXTS = {".html", ".htm", ".css", ".scss", ".less", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".vue", ".svelte", ".astro"}
STYLE_EXTS = {".css", ".scss", ".less"}
MARKUP_EXTS = {".html", ".htm", ".vue", ".svelte", ".astro"}

# rule -> (category, designed tier, check); filled by @rule in catalogue order.
# A check takes a Source and yields (offset, matched text); duplication rules (check None) run across files.
RULES = {}


def rule(category, tier):
    def register(check):
        RULES[check.__name__[2:].replace("_", "-")] = (category, tier, check)
        return check
    return register


def calibration_file():
    return os.environ.get("SUPAH_DESIGN_CALIBRATION") or os.path.join(HERE, "designscan-calibration.json")


def tier_of(rule):
    tier = RULES[rule][1]
    path = calibration_file()
    if os.path.exists(path) and not os.environ.get("SUPAH_DESIGN_NO_CALIBRATION"):
        with open(path, encoding="utf-8") as f:
            tier = json.load(f).get("rules", {}).get(rule, {}).get("tier", tier)
    return tier


# --- reading the source -------------------------------------------------------------------

CLASS_ATTR = re.compile(r"""(?<![\w-])(?:class|className|:class)\s*=\s*(?:"([^"]*)"|'([^']*)'|\{\s*`([^`]*)`\s*\}|\{\s*"([^"]*)"\s*\}|\{\s*'([^']*)'\s*\})""")
CLASS_CALL = re.compile(r"\b(?:cn|clsx|classnames|twMerge|cva|tw)\s*\(")
STRING = re.compile(r"""`([^`]*)`|"([^"\n]*)"|'([^'\n]*)'""")
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
STYLE_ATTR = re.compile(r"""(?<![\w:-])style\s*=\s*(?:"([^"]*)"|'([^']*)')""")


class Source:
    """One file, with its class strings, its CSS text and its visible text, each with offsets."""

    def __init__(self, text, path):
        self.text = text
        self.path = path
        self.ext = os.path.splitext(path)[1].lower()
        self.starts = [0] + [m.end() for m in re.finditer(r"\n", text)]
        self.lines = text.split("\n")
        self.classes = list(self._classes())
        self.css = list(self._css())
        self.texts = list(self._texts())

    def line_of(self, pos):
        return bisect.bisect_right(self.starts, pos)

    def context(self, line):
        return self.lines[line - 1].strip()[:160] if 0 < line <= len(self.lines) else ""

    def _classes(self):
        if self.ext in STYLE_EXTS:
            return
        for m in CLASS_ATTR.finditer(self.text):
            value = next(g for g in m.groups() if g is not None)
            binding = m.group(0).startswith(":") or value.lstrip()[:1] in ("[", "{")
            inner = list(STRING.finditer(value)) if binding else []
            if inner:  # a binding such as :class="['a b', cond && 'c']": read its string literals
                for s in inner:
                    yield m.start(), next(g for g in s.groups() if g is not None)
            else:
                yield m.start(), value
        for m in re.finditer(r"<[A-Za-z][^<>]*\bclass:[^<>]*>", self.text):  # Svelte class:name={cond} directives
            names = re.findall(r"(?<![\w-])class:([^\s=>{}]+)", m.group(0))
            if names:
                yield m.start(), " ".join(names)
        for m in CLASS_CALL.finditer(self.text):
            call = balanced(self.text, m.end() - 1, 2000)
            for s in STRING.finditer(call):
                yield m.end() - 1 + s.start(), next(g for g in s.groups() if g is not None)

    def _css(self):
        """Spans that hold CSS or style values: whole stylesheets and scripts, style blocks and attributes."""
        if self.ext not in MARKUP_EXTS:
            yield 0, self.text
            return
        for m in STYLE_BLOCK.finditer(self.text):
            yield m.start(1), m.group(1)
        for m in STYLE_ATTR.finditer(self.text):
            g = 1 if m.group(1) is not None else 2
            yield m.start(g), m.group(g)

    def _texts(self):
        """Visible text nodes in markup and JSX: what sits between a tag's `>` and the next `<`."""
        if self.ext in STYLE_EXTS:
            return
        blanked = STYLE_BLOCK.sub(lambda m: " " * len(m.group(0)), self.text)
        blanked = re.sub(r"<script\b.*?</script>", lambda m: " " * len(m.group(0)), blanked, flags=re.S | re.I)
        blanked = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), blanked, flags=re.S)
        for m in re.finditer(r"(?<![=\-])>([^<>{}=;]+)<", blanked):
            if m.group(1).strip():
                yield m.start(1) + len(m.group(1)) - len(m.group(1).lstrip()), m.group(1).strip()

    def tag_at(self, pos):
        """The opening tag that contains pos."""
        start = self.text.rfind("<", 0, pos)
        end = self.text.find(">", pos)
        return self.text[start:end + 1] if start >= 0 and end >= 0 else ""

    def find_css(self, pattern, flags=re.I):
        for offset, text in self.css:
            for m in re.finditer(pattern, text, flags):
                yield offset + m.start(), m


def tokens(value):
    return set(value.split())


def has(value, pattern):
    return re.search(pattern, value) is not None


def balanced(text, start, limit=600):
    """The text from start through the parenthesis that closes the first one opened."""
    depth, i = 0, start
    while i < len(text) and i - start < limit:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return text[start:i]


def balanced_braces(text, start, limit=2000):
    """The text from start (a `{`) through its matching `}`."""
    depth, i = 0, start
    while i < len(text) and i - start < limit:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
        if depth == 0:
            break
    return text[start:i]


def in_custom_property(text, pos):
    """True when the declaration around pos defines a custom property (`--name: value`)."""
    start = max(text.rfind(";", 0, pos), text.rfind("{", 0, pos), text.rfind("\n", 0, pos)) + 1
    return text[start:pos].lstrip().startswith("--")


# --- rules --------------------------------------------------------------------------------
# Each rule takes a Source and yields (offset, matched text).

PURPLE = r"(?:purple|violet|indigo|fuchsia)"
PAIR = r"(?:blue|indigo|pink|cyan|sky|purple|violet|fuchsia)"
PURPLE_HEX = ("667eea", "764ba2", "6366f1", "4f46e5", "4338ca", "7c3aed", "6d28d9", "8b5cf6", "a855f7", "9333ea",
              "a78bfa", "c084fc", "818cf8")


@rule("colour", "M")
def r_purple_gradient(src):
    for pos, value in src.classes:
        if (has(value, r"\bfrom-%s-\d{2,3}\b" % PURPLE) and has(value, r"\bto-%s-\d{2,3}\b" % PAIR)) or \
                (has(value, r"\bfrom-%s-\d{2,3}\b" % PAIR) and has(value, r"\bto-%s-\d{2,3}\b" % PURPLE)):
            yield pos, value
    for offset, text in src.css:
        for m in re.finditer(r"(?:linear|radial|conic)-gradient\s*\(", text, re.I):
            call = balanced(text, m.start()).lower()
            if any("#" + h in call for h in PURPLE_HEX) or has(call, r"\b(?:purple|violet|indigo)\b"):
                yield offset + m.start(), call


SWATCH = re.compile(r"^(?:[\w-]+:)*bg-(?:(?:indigo|violet|purple)-(?:500|600|700)|blue-600)$")


@rule("colour", "W")
def r_stock_swatch(src):
    for pos, value in src.classes:
        for t in value.split():
            if SWATCH.match(t):
                yield pos, t


CREAM = r"#(?:f4f1ea|faf8f5|f5f1e8|faf7f2|f7f3ec|f5f0e8|fbf8f3|f6f1e9)(?![0-9a-f])"
CLAY = r"#(?:d97757|cc785c|e07a5f|c96442|da7756|b85c38|c15f3c)(?![0-9a-f])"


@rule("colour", "W")
def r_cream_clay(src):
    cream = next(src.find_css(CREAM), None)
    if cream:
        for pos, m in src.find_css(CLAY):
            yield pos, "cream %s + clay %s" % (cream[1].group(0).lower(), m.group(0).lower())
            return


@rule("colour", "W")
def r_pure_black_white(src):
    for offset, text in src.css:
        for m in re.finditer(r"#(?:000(?:000)?|fff(?:fff)?)(?![0-9a-f])", text, re.I):
            if not in_custom_property(text, m.start()):
                yield offset + m.start(), m.group(0)


@rule("colour", "W")
def r_near_black(src):
    for pos, m in src.find_css(r"#(?:0b0b0b|0a0a0a|0d0d0d|111111|111|121212)(?![0-9a-f])"):
        yield pos, m.group(0)


_PALETTE = {}


def palette():
    if not _PALETTE:
        with open(os.path.join(HERE, "tailwind-colors.json"), encoding="utf-8") as f:
            _PALETTE.update({k: v for k, v in json.load(f).items() if not k.startswith("_")})
    return _PALETTE


def rgb_of(colour):
    """(r, g, b) of a hex, rgb() or rgba() colour, or None."""
    colour = colour.strip().lower()
    m = re.match(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)", colour)
    if m:
        return tuple(int(x) for x in m.groups())
    if colour in ("white", "black"):
        return (255, 255, 255) if colour == "white" else (0, 0, 0)
    h = colour.lstrip("#")
    if re.fullmatch(r"[0-9a-f]{3,4}", h):
        h = "".join(c * 2 for c in h[:3])
    if re.fullmatch(r"[0-9a-f]{6}(?:[0-9a-f]{2})?", h):
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return None


def alpha_of(colour):
    """Opacity of a 4- or 8-digit hex or an rgba()/rgb(... / a) colour, 1.0 for any other colour."""
    colour = colour.strip().lower()
    m = re.match(r"rgba?\(\s*\d+[\s,]+\d+[\s,]+\d+\s*[,/]\s*(\d*\.?\d+)(%?)", colour)
    if m:
        return min(float(m.group(1)) / (100 if m.group(2) else 1), 1.0)
    h = colour.lstrip("#")
    if re.fullmatch(r"[0-9a-f]{4}|[0-9a-f]{8}", h):
        return int(h[3] * 2 if len(h) == 4 else h[6:], 16) / 255
    return 1.0


def luminance(rgb):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def blend(fg, bg, alpha):
    return tuple(round(alpha * f + (1 - alpha) * b) for f, b in zip(fg, bg))


def large_text(value):
    """WCAG large text: 24px and up, or 18.66px and up in bold (text-xl is 20px)."""
    t = tokens(value)
    bold = bool(t & {"font-semibold", "font-bold", "font-extrabold", "font-black"})
    return any(re.match(r"^text-[2-9]xl$", x) for x in t) or ("text-xl" in t and bold)


def pairs(value):
    """(text colour, alpha, background colour) per variant group ('' and 'dark:') of one class string."""
    groups = {}
    for t in value.split():
        # a palette name (text-gray-400) or an arbitrary hex value (text-[#d97757]), with an optional /alpha
        m = re.match(r"^((?:dark:)?)(text|bg)-([a-z]+(?:-\d{2,3})?|\[#[0-9a-fA-F]{3,8}\])(?:/(\d{1,3}))?$", t)
        colour = m and (palette().get(m.group(3)) or (m.group(3)[1:-1] if m.group(3).startswith("[") else None))
        if colour and rgb_of(colour):
            alpha = (int(m.group(4)) / 100 if m.group(4) else 1.0) * alpha_of(colour)
            groups.setdefault(m.group(1), {})[m.group(2)] = (rgb_of(colour), alpha, t)
    for g in groups.values():
        if "text" in g and "bg" in g and g["bg"][1] == 1.0:
            yield g["text"], g["bg"]


NOT_TEXT = r"(?:^|[\s>+~,(])(?:hr|svg|path|img)\b|icon|social-link|::?(?:before|after)\b"


@rule("colour", "M")
def r_low_contrast(src):
    for pos, value in src.classes:
        large = large_text(value)
        for (fg, alpha, ft), (bg, _, bt) in pairs(value):
            ratio = contrast(blend(fg, bg, alpha), bg)
            if ratio < (3.0 if large else 4.5):
                yield pos, "%s on %s %.1f:1" % (ft, bt, ratio)
    for pos, selector, body in css_blocks(src):
        if re.search(NOT_TEXT, selector, re.I):  # colour on icons and rules is not text contrast
            continue
        fg = re.search(r"(?<![\w-])color\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))", body)
        bg = re.search(r"background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8}|rgb\([^)]*\))\s*(?:;|}|$)", body)
        # a translucent background hides what shows through it, so there is nothing to measure
        if fg and bg and rgb_of(fg.group(1)) and rgb_of(bg.group(1)) and alpha_of(bg.group(1)) == 1.0:
            size = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", body)
            bold = re.search(r"font-weight\s*:\s*(?:bold|[6-9]00)", body)
            large = size and (float(size.group(1)) >= 24 or (float(size.group(1)) >= 18.66 and bold))
            back = rgb_of(bg.group(1))
            ratio = contrast(blend(rgb_of(fg.group(1)), back, alpha_of(fg.group(1))), back)
            if ratio < (3.0 if large else 4.5):
                yield pos, "%s { %s on %s %.1f:1 }" % (selector, fg.group(1), bg.group(1), ratio)


# Training-data defaults as of 2026-11 (sources: docs/research/2026-11-design-reflexes.md). Date the list when it changes.
REFLEX_FONTS = ("Inter", "Geist", "Geist Mono", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins",
                "Space Grotesk", "Space Mono", "Instrument Sans", "Instrument Serif", "Fraunces", "Plus Jakarta Sans",
                "Syne", "Sora", "DM Sans", "DM Serif Display", "DM Serif Text", "DM Mono", "Outfit",
                "Playfair Display", "Cormorant", "Cormorant Garamond", "Newsreader", "Lora", "Crimson Pro",
                "Crimson Text", "IBM Plex Sans", "IBM Plex Serif", "IBM Plex Mono", "Bricolage Grotesque",
                "Young Serif", "Recoleta", "Mona Sans")
FONT_KEYS = {f.lower().replace(" ", ""): f for f in REFLEX_FONTS}


def font_key(name):
    return name.strip().strip("'\"`").lower().replace(" ", "").replace("_", "").replace("+", "")


@rule("type", "W")
def r_reflex_font(src):
    for pos, m in src.find_css(r"font-family\s*:\s*([^;{}\n]+)|--font-[\w-]+\s*:\s*([^;{}\n]+)|"
                               r"fontFamily\s*:\s*\[?\s*(['\"][^\]};\n]+)"):
        stack = m.group(1) or m.group(2) or m.group(3)
        first = font_key(stack.split(",")[0])
        if first in FONT_KEYS:
            yield pos, "%s (%s)" % (FONT_KEYS[first], m.group(0).strip())
    for m in re.finditer(r"fontFamily\s*:\s*\{", src.text):  # Tailwind config: fontFamily: { sans: ["Inter", …] }
        for face in re.finditer(r"[\w'\"-]+\s*:\s*\[\s*['\"]([^'\"]+)['\"]", balanced_braces(src.text, m.end() - 1)):
            if font_key(face.group(1)) in FONT_KEYS:
                yield m.start() + face.start(), FONT_KEYS[font_key(face.group(1))]
    for m in re.finditer(r"fonts\.googleapis\.com/css2?\?([^\"'\s>]+)", src.text):
        for fam in re.findall(r"family=([^:&;]+)", m.group(1)):
            if font_key(fam) in FONT_KEYS:
                yield m.start(), FONT_KEYS[font_key(fam)]
    for m in re.finditer(r"import\s*\{([^}]*)\}\s*from\s*['\"](?:next/font/google|@fontsource[^'\"]*)['\"]", src.text):
        for name in m.group(1).split(","):
            if font_key(name) in FONT_KEYS:
                yield m.start(), FONT_KEYS[font_key(name)]
    for m in re.finditer(r"['\"]@fontsource(?:-variable)?/([\w-]+)['\"]", src.text):
        if font_key(m.group(1).replace("-", "")) in FONT_KEYS:
            yield m.start(), FONT_KEYS[font_key(m.group(1).replace("-", ""))]


HEADING = re.compile(r"<h([1-3])\b[^>]*>(.{0,600}?)</h\1>", re.S | re.I)
ACCENT = re.compile(r"<(?:em|i)\b|<span\b[^>]*(?:class|className)\s*=\s*[\"'{`][^\"'}`]*"
                    r"\b(?:italic|bg-clip-text|text-transparent|font-serif|text-(?!white\b|black\b|xs\b|sm\b|base\b|lg\b|"
                    r"\d?xl\b|left\b|center\b|right\b|balance\b|pretty\b)[a-z]+-\d{2,3})\b", re.I)


@rule("type", "W")
def r_accent_word_heading(src):
    for m in HEADING.finditer(src.text):
        if ACCENT.search(m.group(2)):
            yield m.start(), re.sub(r"<[^>]+>", "", m.group(2))


CAPS = r"\buppercase\b"
TRACKED = r"\btracking-(?:wide|wider|widest|\[[^\]]+\])"
SMALL = r"\btext-(?:xs|sm|\[(?:9|10|11|12|13|14)px\])"


def next_tag_after_close(text, pos):
    """The name of the first element opened after the element that holds pos closes."""
    close = text.find("</", pos)
    m = re.compile(r"<([A-Za-z][\w.]*)").search(text, close + 2) if close >= 0 else None
    return m.group(1).lower() if m else ""


def caps_labels(src):
    for pos, value in src.classes:
        if has(value, CAPS) and has(value, TRACKED) and has(value, SMALL):
            yield pos, value, next_tag_after_close(src.text, pos) in ("h1", "h2", "h3")


@rule("type", "W")
def r_eyebrow(src):
    for pos, value, before_heading in caps_labels(src):
        if before_heading:
            yield pos, value


@rule("type", "W")
def r_tracked_caps(src):
    for pos, value, before_heading in caps_labels(src):
        if not before_heading:
            yield pos, value


@rule("type", "W")
def r_mono_label(src):
    for pos, value in src.classes:
        if has(value, r"\bfont-mono\b") and (has(value, SMALL) or has(value, CAPS)):
            yield pos, value


GRADIENT_CLIP_CSS =r"(?:-webkit-)?background-clip\s*:\s*text|webkitBackgroundClip\s*:\s*['\"]text|backgroundClip\s*:\s*['\"]text"


@rule("surface", "M")
def r_gradient_text(src):
    for pos, value in src.classes:
        t = tokens(value)
        if "bg-clip-text" in t and ("text-transparent" in t or has(value, r"\bbg-(?:gradient|linear)-")):
            yield pos, value
    for pos, m in src.find_css(GRADIENT_CLIP_CSS):
        yield pos, m.group(0)


CSS_BLOCK = re.compile(r"([^{}]*)\{([^{}]*)\}")


def css_blocks(src):
    """(offset, selector, body) for every innermost CSS rule block."""
    for offset, text in src.css:
        for m in CSS_BLOCK.finditer(text):
            yield offset + m.start(2), m.group(1).strip(), m.group(2)


def chromatic(colour):
    """True when an rgb()/rgba()/hex colour has visible hue (not a grey)."""
    rgb = rgb_of(colour)
    return rgb is not None and max(rgb) - min(rgb) >= 40


COLOUR = r"rgba?\([^)]*\)|#[0-9a-fA-F]{3,8}\b"
GLOW_HUES = r"(?:indigo|purple|violet|blue|cyan|pink|fuchsia|emerald|sky|teal|green|lime|rose)"


@rule("surface", "W")
def r_glass_card(src):
    for pos, value in src.classes:
        t = tokens(value)
        if has(value, r"\bbackdrop-blur\b|\bbackdrop-blur-\w+") and has(value, r"\bbg-[\w\[\]#-]+/\d+|\bbg-opacity-") \
                and not t & {"sticky", "fixed"}:
            yield pos, value
    for pos, selector, body in css_blocks(src):
        blur = re.search(r"backdrop-filter\s*:\s*blur\(\s*(\d+(?:\.\d+)?)", body, re.I)
        if blur and float(blur.group(1)) >= 2 and re.search(r"background(?:-color)?\s*:\s*(?:rgba|hsla)\(", body, re.I) \
                and not re.search(r"position\s*:\s*(?:sticky|fixed)", body, re.I):
            yield pos, "%s { %s }" % (selector, blur.group(0))


@rule("surface", "W")
def r_coloured_glow(src):
    for pos, value in src.classes:
        for t in value.split():
            arb = re.match(r"^(?:[\w-]+:)*shadow-\[0_0_[^\]]*\]$", t)
            if (arb and any(chromatic(c) for c in re.findall(COLOUR, t))) or \
                    re.match(r"^(?:[\w-]+:)*shadow-%s-\d{3}(?:/\d+)?$" % GLOW_HUES, t):
                yield pos, t
    for pos, m in src.find_css(r"(?:box|text)-shadow\s*:\s*0(?:px)?\s+0(?:px)?\s+\d+(?:px)?[^;}\n]*"):
        if any(chromatic(c) for c in re.findall(COLOUR, m.group(0))):
            yield pos, m.group(0)


@rule("surface", "M")
def r_accent_stripe(src):
    for pos, value in src.classes:
        t = tokens(value)
        stripe = has(value, r"(?:^|\s)(?:[\w-]+:)*border-[lt]-(?:2|4|8|\[\d+px\])(?=\s|$)")
        coloured = has(value, r"(?:^|\s)(?:[\w-]+:)*border-(?:[a-z]+-\d{2,3}|\[#[0-9a-fA-F]+\])(?=\s|/|$)")
        rounded = any(re.match(r"^(?:[\w-]+:)*rounded(?:-(?!full|none)\w+)?$", x) for x in t)
        if stripe and coloured and rounded and "animate-spin" not in t:
            yield pos, value
    for pos, selector, body in css_blocks(src):
        width = re.search(r"(?<![\w-])border-(?:left|top)(?:-width)?\s*:\s*(\d+)px", body, re.I)
        if width and int(width.group(1)) >= 2 and re.search(r"border-radius\s*:\s*(?!0[;\s}]|50%)", body, re.I):
            yield pos, "%s { %s }" % (selector, width.group(0))


@rule("surface", "W")
def r_shadcn_card(src):
    for pos, value in src.classes:
        t = tokens(value)
        if {"border", "bg-card", "text-card-foreground", "shadow-sm"} <= t:
            yield pos, value


def dominant(counts, minimum=6, share=0.8):
    total = sum(counts.values())
    if total >= minimum:
        value, n = max(counts.items(), key=lambda kv: kv[1])
        if n / total >= share:
            return value, n, total
    return None


def density(src, token_re, css_re):
    counts, first = {}, {}
    for pos, value in src.classes:
        for t in value.split():
            m = re.match(token_re, t)
            if m:
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
                first.setdefault(m.group(1), pos)
    for pos, m in src.find_css(css_re):
        key = " ".join(m.group(1).split()).lower()
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, pos)
    found = dominant(counts)
    if found:
        value, n, total = found
        yield first[value], "%s on %d of %d" % (value, n, total)


@rule("surface", "W")
def r_uniform_radius(src):
    return density(src, r"^(?:[\w-]+:)*(rounded(?:-(?:sm|md|lg|xl|2xl|3xl))?)$",
                   r"border-radius\s*:\s*([^;{}\n]+?)\s*(?:;|}|$)")


@rule("surface", "W")
def r_soft_shadow(src):
    return density(src, r"^(?:[\w-]+:)*(shadow-(?:md|lg|xl|2xl))$",
                   r"box-shadow\s*:\s*(0(?:px)?\s+\d+px\s+\d+px[^;{}\n]*rgba\(\s*0\s*,\s*0\s*,\s*0[^)]*\))")


ICON_MARK = re.compile(r"Icon\b|<svg\b|lucide|\bicon\b|\b(?:w|h|size)-(?:10|12|14|16)\b", re.I)


@rule("layout", "W")
def r_icon_card_grid(src):
    starts = [(pos, value) for pos, value in src.classes if has(value, r"(?:^|\s)(?:\w+:)?grid-cols-3(?=\s|$)")]
    starts += [(pos, m.group(0)) for pos, m in src.find_css(r"grid-template-columns\s*:\s*repeat\(\s*3\s*,")]
    for pos, value in starts:
        window = src.text[pos:pos + 1500]
        cards = len(re.findall(r"<h3\b", window))
        if cards and (".map(" in window or cards >= 3) and ICON_MARK.search(window):
            yield pos, value


@rule("layout", "W")
def r_numbered_markers(src):
    marks = [(pos, t) for pos, t in src.texts if re.fullmatch(r"0[1-9]\.?", t)]
    marks += [(m.start(), m.group(1)) for m in re.finditer(r"""(?<![\w-])['"](0[1-9])['"]""", src.text)
              if src.ext not in STYLE_EXTS]
    if len({t.rstrip(".") for _, t in marks}) >= 2:
        marks.sort()
        yield marks[0][0], ", ".join(sorted({t.rstrip(".") for _, t in marks}))


STAT = re.compile(r"\d[\d.,]*\s*[%+×xkKMB]+|\d+/\d+|\$\d[\d.,]*[kKMB]?\+?")


@rule("layout", "W")
def r_stat_banner(src):
    stats = [(pos, t) for pos, t in src.texts if STAT.fullmatch(t)]
    for i in range(len(stats) - 2):
        if src.line_of(stats[i + 2][0]) - src.line_of(stats[i][0]) <= 20:
            yield stats[i][0], " · ".join(t for _, t in stats[i:i + 3])
            return


VH = r"(?:^|\s)(?:[\w-]+:)*(?:min-)?h-(?:screen|lvh|\[\d+(?:vh|lvh)\])(?=\s|$)"  # svh/dvh are the fix


@rule("layout", "W")
def r_vh_hero(src):
    for pos, value in src.classes:
        if has(value, VH):
            tag = src.tag_at(pos).lower()
            if "hero" in tag or re.match(r"<(?:section|header)\b", tag):
                yield pos, value
    for pos, selector, body in css_blocks(src):
        h = re.search(r"(?:min-)?height\s*:\s*(\d+)(?:vh|lvh)\b", body, re.I)
        if h and int(h.group(1)) >= 80 and "hero" in selector.lower():
            yield pos, "%s { %s }" % (selector, h.group(0))


CHROME = r"traffic[-_]?lights?|url[-_]?(?:bar|pill)|title[-_]?bar|window[-_]?(?:dots|controls)|browser[-_]?(?:chrome|frame|bar)"


@rule("layout", "M")
def r_faux_chrome(src):
    for pos, value in src.classes:
        m = re.search(CHROME, value, re.I)
        if m:
            yield pos, m.group(0)
    for m in re.finditer(r"bg-red-\d{3}", src.text):
        window = src.text[max(0, m.start() - 80):m.start() + 400]
        if re.search(r"bg-(?:yellow|amber)-\d{3}", window) and re.search(r"bg-(?:green|emerald)-\d{3}", window) \
                and window.count("rounded-full") >= 3:
            yield m.start(), "red, yellow and green dots"


EMOJI = "[\U0001f300-\U0001faff\u2600\u2601\u2614\u2615\u26a0\u26a1\u26d4\u2705\u2728\u274c\u2753\u2757\u2764\u27a1\u2b50\u2b06\u2b07\u23f0\u23f3]"  # pictographs; text glyphs such as hamburger or check marks are not emoji


@rule("glyph", "M")
def r_emoji_icon(src):
    for pos, t in src.texts:
        if re.match(EMOJI, t) or (re.search(EMOJI, t) and len(t.split()) <= 4):
            yield pos, t
    for m in re.finditer(r"""\b(?:icon|emoji)\s*:\s*['"`](%s[^'"`]*)['"`]""" % EMOJI, src.text):
        yield m.start(), m.group(1)


@rule("glyph", "W")
def r_middot_meta(src):
    for pos, t in src.texts:
        if re.search(r"\S\s+·\s+\S", t) and len(t) <= 100:
            yield pos, t


@rule("glyph", "W")
def r_glued_arrow(src):
    for pos, t in src.texts:
        # a label that ends in an arrow; text that also starts with one draws a flow
        if re.search(r"(?:→|↗|&rarr;)$", t) and len(t) > 1 and not re.match(r"(?:→|↗|&rarr;)", t):
            yield pos, t


@rule("glyph", "W")
def r_word_dash_label(src):
    for pos, t in src.texts:
        if re.match(r"[A-Z][A-Z0-9&]+(?:\s[A-Z0-9&]+)*\s+[—–]\s+\S", t):
            yield pos, t


@rule("glyph", "W")
def r_pulsing_dot(src):
    for pos, value in src.classes:
        if has(value, r"\banimate-(?:ping|pulse)\b") and has(value, r"\brounded-full\b") and \
                has(src.text[max(0, pos - 200):pos + len(value)], r"\b(?:h|w|size)-(?:1|1\.5|2|2\.5|3)\b"):
            yield pos, value


@rule("motion", "M")
def r_transition_all(src):
    for pos, value in src.classes:
        for t in value.split():
            if re.match(r"^(?:[\w-]+:)*transition-all$", t):
                yield pos, t
    for pos, m in src.find_css(r"transition(?:-property)?\s*:\s*['\"]?all\b[^;}\n'\"]*"):
        yield pos, m.group(0)


REVEALS = (r"\bwhileInView\b", r"\bdata-aos\s*=", r"\bdata-sal\s*=", r"(?<![\w-])(?:animate-)?fade-(?:in-)?up(?![\w-])",
           r"\bscrollTrigger\b")


@rule("motion", "W")
def r_reveal_every_section(src):
    for pattern in REVEALS:
        found = list(re.finditer(pattern, src.text))
        if len(found) >= 4:
            yield found[0].start(), "%s on 4 or more elements" % found[0].group(0).strip(" =")
            return


BOUNCE = r"ease-?(?:in-?|out-?|in-?out-?)?(?:back|elastic|bounce)\b|ease(?:In|Out|InOut)(?:Back|Elastic|Bounce)\b|" \
         r"\b(?:elastic|back|bounce)\.(?:in|out|inOut)\b|(?<![\w-])animate-bounce(?![\w-])|bounce\s*:\s*0?\.[3-9]"


@rule("motion", "W")
def r_bounce_easing(src):
    number = r"-?(?:\d+\.?\d*|\.\d+)"
    for pos, m in src.find_css(r"cubic-bezier\(\s*%s\s*,\s*(%s)\s*,\s*%s\s*,\s*(%s)\s*\)" % (number, number, number, number)):
        if not 0 <= float(m.group(1)) <= 1 or not 0 <= float(m.group(2)) <= 1:
            yield pos, m.group(0)
    for m in re.finditer(BOUNCE, src.text):
        yield m.start(), m.group(0)


@rule("motion", "W")
def r_hover_scale(src):
    hits = [(pos, t) for pos, value in src.classes for t in value.split()
            if re.match(r"^(?:[\w-]+:)*(?:group-)?hover:(?:scale-(?:102|103|105|110|\[1\.\d+\])|-translate-y-[\w.\[\]]+)$", t)]
    hits += [(m.start(), m.group(0)) for m in re.finditer(r"whileHover=\{\{\s*scale\s*:\s*1\.\d+", src.text)]
    if len(hits) >= 3:
        hits.sort()
        yield hits[0][0], "%s on 3 or more elements" % hits[0][1]


ANIMATION = r"@keyframes\b|(?<![\w-])animation\s*:|(?<![\w-])animate-(?!none\b)[a-z]|\bwhileInView\b|\bdata-aos\s*="
REDUCED = r"prefers-reduced-motion|motion-reduce:|motion-safe:|useReducedMotion|reducedMotion"


@rule("motion", "W")
def r_no_reduced_motion(src):
    first = re.search(ANIMATION, src.text)
    if first and not re.search(REDUCED, src.text):
        yield first.start(), "%s without a reduced-motion path" % first.group(0).strip(" :=")


@rule("placeholder", "M")
def r_placeholder_name(src):
    for m in re.finditer(r"(?<![@/\w.-])(?:Acme|Jane Doe|John Doe|Lorem ipsum)\b", src.text, re.I):
        yield m.start(), m.group(0)


@rule("placeholder", "M")
def r_placeholder_phone(src):
    for m in re.finditer(r"\(555\)\s*\d{3}[-.\s]\d{4}|\b555[-.]\d{3}[-.]\d{4}\b|\b555-\d{4}\b", src.text):
        yield m.start(), m.group(0)


@rule("placeholder", "M")
def r_dead_link(src):
    for m in re.finditer(r"""\bhref\s*=\s*(?:["']#["']|\{\s*["']#["']\s*\})""", src.text):
        yield m.start(), m.group(0)


BREAKPOINT = r"(?:sm|md|lg|xl|2xl|min-\[[^\]]+\]|@\w+)"


def responsive_prefixed(token):
    return re.match(r"^(?:[\w-]+:)*%s:" % BREAKPOINT, token) is not None


def media_ranges(text):
    """(start, end) of every @media and @container block in a stylesheet."""
    out = []
    for m in re.finditer(r"@(?:media|container)\b[^{]*\{", text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append((m.start(), i))
    return out


def plain_blocks(src):
    """CSS blocks outside @media and @container, which apply at every width."""
    for offset, text in src.css:
        ranges = media_ranges(text)
        for m in CSS_BLOCK.finditer(text):
            if not any(a <= m.start() < b for a, b in ranges) and not m.group(1).strip().startswith("@"):
                yield offset + m.start(2), m.group(1).strip(), m.group(2), bool(ranges)


@rule("responsive", "M")
def r_missing_viewport(src):
    m = re.search(r"<head\b|<html\b", src.text, re.I)
    if m and src.ext in MARKUP_EXTS and not re.search(r"<meta\b[^>]*name\s*=\s*[\"']?viewport", src.text, re.I):
        yield m.start(), "no <meta name=\"viewport\">"


@rule("responsive", "W")
def r_fixed_width(src):
    for pos, value in src.classes:
        t = value.split()
        if any(x.startswith("max-w-") or responsive_prefixed(x) and "max-w-" in x for x in t):
            continue
        for x in t:
            m = re.match(r"^(?:w|min-w)-\[(\d+)px\]$", x)
            if m and int(m.group(1)) >= 400:
                yield pos, x
    for pos, selector, body, _ in plain_blocks(src):
        m = re.search(r"(?<![\w-])(?:min-)?width\s*:\s*(\d+)px", body)
        if m and int(m.group(1)) >= 400 and not re.search(r"max-width", body):
            yield pos, "%s { %s }" % (selector, m.group(0))


@rule("responsive", "W")
def r_unprefixed_grid(src):
    for pos, value in src.classes:
        t = value.split()
        cols = [x for x in t if re.match(r"^grid-cols-(?:[3-9]|1[0-2])$", x)]
        if cols and not any(responsive_prefixed(x) and "grid-cols-" in x for x in t):
            yield pos, cols[0]
    for pos, selector, body, has_media in plain_blocks(src):
        m = re.search(r"grid-template-columns\s*:\s*repeat\(\s*(?:[3-9]|1[0-2])\s*,", body)
        if m and not has_media:
            yield pos, "%s { %s }" % (selector, m.group(0))


REVEAL_ON_HOVER = r"^(?:group-)?hover:(?:opacity-100|block|flex|inline-flex|grid|visible)$"


@rule("responsive", "W")
def r_hover_only(src):
    for pos, value in src.classes:
        t = value.split()
        revealed = [x for x in t if re.match(REVEAL_ON_HOVER, x)]
        hidden = {"opacity-0", "hidden", "invisible"} & set(t)
        if revealed and hidden and not any("focus" in x.split(":")[0] for x in t if ":" in x):
            yield pos, revealed[0]
    for pos, selector, body in css_blocks(src):
        if ":hover" in selector and ":focus" not in selector and \
                re.search(r"opacity\s*:\s*1\b|display\s*:\s*(?:block|flex|grid)|visibility\s*:\s*visible", body):
            yield pos, selector


@rule("responsive", "W")
def r_tiny_text(src):
    for pos, value in src.classes:
        for x in value.split():
            m = re.match(r"^(?:[\w-]+:)*text-\[(\d+(?:\.\d+)?)(px|rem)\]$", x)
            if m and float(m.group(1)) * (16 if m.group(2) == "rem" else 1) < 12:
                yield pos, x
    for pos, m in src.find_css(r"font-size\s*:\s*(\d*\.?\d+)(px|rem)\b"):
        if float(m.group(1)) * (16 if m.group(2).lower() == "rem" else 1) < 12:
            yield pos, m.group(0)


@rule("responsive", "W")
def r_viewport_width(src):
    for pos, value in src.classes:
        for x in value.split():
            if re.match(r"^(?:[\w-]+:)*(?:w|min-w)-(?:screen|\[100vw\])$", x):
                yield pos, x
    for pos, m in src.find_css(r"(?<![\w-])(?:min-)?width\s*:\s*100vw"):
        yield pos, m.group(0)




# --- duplication across the files of one run ----------------------------------------------
# Styles repeated where a shared component, class or token would hold them once.

MIN_TOKENS, MIN_REPEATS, MIN_DECLARATIONS, MIN_COLOUR_USES = 6, 3, 3, 5
RULES["repeated-class-string"] = ("duplication", "W", None)
RULES["duplicate-css-block"] = ("duplication", "W", None)
RULES["untokened-colour"] = ("duplication", "W", None)


def first_per_file(occurrences, rule, match):
    """One hit per file, at the first occurrence there."""
    done = set()
    for src, pos in sorted(occurrences, key=lambda o: (o[0].path, o[1])):
        if src.path not in done:
            done.add(src.path)
            yield src, pos, rule, match


def run_hits(sources):
    strings, blocks, colours = {}, {}, {}
    for src in sources:
        for pos, value in src.classes:
            t = value.split()
            if len(t) >= MIN_TOKENS and not has(value, r"\$\{|\{\{"):
                strings.setdefault(" ".join(sorted(t)), []).append((src, pos))
        for pos, selector, body in css_blocks(src):
            decls = sorted(" ".join(d.split()).lower() for d in body.split(";") if ":" in d)
            if len(decls) >= MIN_DECLARATIONS:
                blocks.setdefault("; ".join(decls), []).append((src, pos, selector))
        for offset, text in src.css:
            for m in re.finditer(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text):
                hexa = m.group(0).lower()
                if hexa not in ("#000", "#fff", "#000000", "#ffffff") and not in_custom_property(text, m.start()):
                    colours.setdefault(hexa, []).append((src, offset + m.start()))
    for key, occ in strings.items():
        if len(occ) >= MIN_REPEATS:
            yield from first_per_file(occ, "repeated-class-string", key)
    for key, occ in blocks.items():
        if len({sel for _, _, sel in occ}) >= 2:
            yield from first_per_file([(s, p) for s, p, _ in occ], "duplicate-css-block",
                                      "%s: %s" % (", ".join(sorted({sel for _, _, sel in occ})), key))
    for key, occ in colours.items():
        if len(occ) >= MIN_COLOUR_USES:
            yield from first_per_file(occ, "untokened-colour", key)


# --- scanning -----------------------------------------------------------------------------

def scan_many(files, keep=None, model=None):
    """Scan (text, path) pairs as one run: per-file rules, then duplication across every file of the run.
    With a learned model, a rule's tier and context suppressions come from the user's verdicts."""
    keep = keep or {}
    results, sources, raw = [], [], {}
    for text, path in files:
        result = {"file": path, "skipped": None, "hits": []}
        if path in READ_AS:
            result["read_as"] = READ_AS[path]
        results.append(result)
        if os.path.splitext(path)[1].lower() not in EXTS:
            result["skipped"] = "not a frontend source file"
            continue
        src = Source(text, path)
        sources.append(src)
        raw[path] = [(pos, name, match) for name, (_, _, check) in RULES.items() if check
                     for pos, match in check(src)]
    for src, pos, rule, match in run_hits(sources):
        raw[src.path].append((pos, rule, match))
    by_path = {s.path: s for s in sources}
    for result in results:
        src, seen = by_path.get(result["file"]), set()
        if src is None:
            continue
        for line, _, rule, match in sorted((src.line_of(p), p, r, " ".join(m.split())[:120]) for p, r, m in raw[src.path]):
            if (rule, line, match) in seen:
                continue
            seen.add((rule, line, match))
            hit = {"line": line, "rule": rule, "category": RULES[rule][0], "tier": tier_of(rule),
                   "match": match, "context": src.context(line), "kept": keep.get((rule, match))}
            if model:
                hit["tier"], learned = learn.apply(model, hit, learn.NO_LANG)
                hit["kept"] = hit["kept"] or learned
            result["hits"].append(hit)
    return results


def scan_text(text, path, keep=None):
    return scan_many([(text, path)], keep)[0]


def load_keep(path):
    keep = {}
    if path:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3 and not line.startswith("#"):
                    keep[(parts[0], parts[1])] = parts[2]
    return keep


def open_hits(result):
    return [h for h in result["hits"] if not h["kept"] and h["tier"] in ("S", "M")]


READ_AS = {}  # path -> the encoding a file that is not UTF-8 was read with


def read(path):
    """A file's text: UTF-8, else cp1252 (Windows Latin-1), else Latin-1, which decodes any byte.
    A fallback is recorded in READ_AS, so a scan reports it instead of matching replacement characters."""
    with open(path, "rb") as f:
        data = f.read()
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if encoding != "utf-8":
            READ_AS[path] = encoding
        return text.replace("\r\n", "\n").replace("\r", "\n")



def read_inputs(paths):
    """(text, path) for every path that can be read, and whether any could not: a missing path, a directory
    or an unreadable file is one line on stderr and the rest go on. A file that is not UTF-8 is read (read())."""
    pairs, failed = [], False
    for path in paths:
        if os.path.isdir(path):
            reason = "a directory, not a file"
        else:
            try:
                pairs.append((read(path), path))
                continue
            except FileNotFoundError:
                reason = "no such file"
            except OSError as e:
                reason = "cannot be read (%s)" % (e.strerror or e)
        print("designscan.py: %s: %s" % (path, reason), file=sys.stderr, flush=True)
        failed = True
    return pairs, failed


# --- surfaces -----------------------------------------------------------------------------
# A surface is a route or page plus the files only it reaches. Files reached by several
# surfaces, or by none a static read can find, form the shared unit. Every frontend file
# lands in exactly one unit, so an audit's coverage k/N means what it says.

SKIP_DIRS = {"node_modules", "vendor", "vendors", "third_party", "dist", "build", "out", "coverage"}
SPLIT_UNIT_ABOVE = 40  # files; a unit above this splits by directory, so one worker context holds it
IMPORT = re.compile(r"""(?:\bimport\s*(?:[\w*{}\s,$]+?\s*from\s*)?|\bexport\s*[\w*{}\s,$]*?\s*from\s*|"""
                    r"""\b(?:require|import)\s*\(\s*)["']([^"'\n]+)["']""")
CSS_IMPORT = re.compile(r"""@(?:import|use|forward)\s+(?:url\(\s*)?["']([^"']+)["']""")
HTML_REF = re.compile(r"""<(?:link|script)\b[^>]*?\b(?:href|src)\s*=\s*["']([^"'#?]+)""", re.I)
ALIASES = (("~~/", ("",)), ("@@/", ("",)), ("@/", ("src/", "")), ("~/", ("src/", "app/", "")),
           ("$lib/", ("src/lib/",)))


def find_exe(name):
    """The full path of name on PATH, searching absolute entries only. On Windows, CreateProcess and
    shutil.which (Python 3.10) look in the current folder first, where a scanned repository could plant
    a git.exe; a relative entry, an empty one or the current folder itself is skipped for the same
    reason. FileNotFoundError when name is on no such entry."""
    here = os.path.normcase(os.path.abspath(os.getcwd()))
    exts = [""]
    if os.name == "nt":
        exts = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep) if e]
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        folder = folder.strip().strip('"')
        if not folder or not os.path.isabs(folder) or os.path.normcase(os.path.abspath(folder)) == here:
            continue
        for ext in exts:
            candidate = os.path.join(folder, name + ext)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    raise FileNotFoundError("%s: not found on PATH" % name)


def list_files(root):
    """Frontend files under root, relative and with forward slashes, plus the ones left out and why."""
    try:
        out = subprocess.run([find_exe("git"), "-C", root, "ls-files", "-co", "--exclude-standard", "-z"],
                             capture_output=True, timeout=120)
        names = out.stdout.decode("utf-8", "replace").split("\0") if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        names = None
    if names is None:
        names = []
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith(".") and x != "node_modules"]
            names += [os.path.relpath(os.path.join(d, f), root) for f in files]
    kept, skipped = [], []
    for name in sorted(n.replace("\\", "/") for n in names if n):
        parts = name.split("/")
        if os.path.splitext(name)[1].lower() not in EXTS or name.endswith(".d.ts") or \
                any(p.startswith(".") or p == "node_modules" for p in parts[:-1]):
            continue
        if any(p in SKIP_DIRS for p in parts[:-1]):
            skipped.append({"file": name, "reason": "vendored or generated"})
        elif re.search(r"\.min\.(?:js|css)$", name):
            skipped.append({"file": name, "reason": "minified"})
        else:
            kept.append(name)
    return kept, skipped


def git_dirty(root):
    """Files under root, relative with forward slashes, that differ from HEAD (staged, unstaged or untracked).
    Empty outside a git work tree or before the first commit."""
    names = set()
    for args in (["diff", "--name-only", "--relative", "-z", "HEAD"], ["ls-files", "-o", "--exclude-standard", "-z"]):
        try:
            out = subprocess.run([find_exe("git"), "-C", root] + args, capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return set()
        if out.returncode:
            return set()
        names |= {n.replace("\\", "/") for n in out.stdout.decode("utf-8", "replace").split("\0") if n}
    return names


def root_path(root, rel):
    """A file as the inventory names it: ROOT as given, then the path relative to it."""
    prefix = root.replace("\\", "/").rstrip("/")
    return rel if prefix in ("", ".") else prefix + "/" + rel


def detect_framework(root):
    try:
        with open(os.path.join(root, "package.json"), encoding="utf-8") as f:
            pkg = json.load(f)
    except (OSError, ValueError):
        return None
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    return next((name for name, packages, _ in FRAMEWORKS if any(p in deps for p in packages)), None)


def route_id(segments):
    """A route from directory segments, without route groups `(x)` and parallel slots `@x`."""
    kept = [s for s in segments if s and not (s.startswith("(") and s.endswith(")")) and not s.startswith("@")]
    return "/" + "/".join(kept)


def is_under(directory, path):
    return directory == "" or path.startswith(directory + "/")


NEXT_LAYOUTS = ("layout", "template", "loading", "error", "not-found", "default", "global-error")


def page_route(rest, stem):
    """A route from the directory below the pages folder and a file stem; `index` is the directory itself."""
    return route_id((rest or "").split("/") + ([] if stem == "index" else [stem]))


# Each framework's place(f, d, name, stem) says what a file is: ("route", id), ("layout", directory whose
# routes it reaches) or None. f is the file, d its directory, name its basename, stem the name before any dot.

def place_nextjs(f, d, name, stem):
    m = re.match(r"(?:src/)?app(?:/|$)(.*)", d)
    if m and d.split("/")[0] in ("app", "src"):
        if stem == "page":
            return "route", route_id(m.group(1).split("/"))
        return ("layout", d) if stem in NEXT_LAYOUTS else None
    m = re.match(r"(?:src/)?pages(?:/(.*))?$", d)
    if m and d.split("/")[0] in ("pages", "src"):
        if stem in ("_app", "_document"):
            return "layout", d
        if (m.group(1) or "").split("/")[0] != "api":
            return "route", page_route(m.group(1), stem)
    return None


def place_sveltekit(f, d, name, stem):
    m = re.match(r"src/routes(?:/(.*))?$", d)
    if m and stem == "+page":
        return "route", route_id((m.group(1) or "").split("/"))
    return ("layout", d) if m and stem in ("+layout", "+error") else None


def place_nuxt(f, d, name, stem):
    m = re.match(r"(?:app/)?pages(?:/(.*))?$", d)
    if m and name.endswith(".vue"):
        return "route", page_route(m.group(1), stem)
    if re.match(r"(?:app/)?layouts(?:/|$)", d) or f in ("app.vue", "error.vue", "app/app.vue", "app/error.vue"):
        return "layout", ""
    return None


def place_astro(f, d, name, stem):
    m = re.match(r"src/pages(?:/(.*))?$", d)
    if m and not any(s.startswith("_") for s in f.split("/")):
        return "route", page_route(m.group(1), stem)
    return None


def place_react_router(f, d, name, stem):
    if f in ("app/root.tsx", "app/root.jsx"):
        return "layout", ""
    if d == "app/routes" or (d.startswith("app/routes/") and stem == "route"):
        flat = (posixpath.basename(d) if stem == "route" else name.rsplit(".", 1)[0]).split(".")
        return "route", "/" + "/".join(s.replace("$", ":").strip("_") for s in flat
                                       if s not in ("_index", "route") and not s.startswith("_"))
    return None


# name, the package.json dependencies that select it, and how it places a file
FRAMEWORKS = (("nextjs", ("next",), place_nextjs), ("nuxt", ("nuxt",), place_nuxt),
              ("sveltekit", ("@sveltejs/kit",), place_sveltekit), ("astro", ("astro",), place_astro),
              ("react-router", ("react-router", "react-router-dom", "@remix-run/react"), place_react_router))


def find_routes(framework, files):
    """(entries: route -> files, layouts: file -> directory whose routes it reaches) for a framework."""
    entries, layouts = {}, {}
    place = next((fn for name, _, fn in FRAMEWORKS if name == framework), None)
    for f in files if place else ():
        d, name = posixpath.split(f)
        found = place(f, d, name, name.split(".")[0])
        if found and found[0] == "route":
            entries.setdefault(found[1], []).append(f)
        elif found:
            layouts[f] = found[1]
    return entries, layouts


def resolve(spec, importer, known):
    spec = spec.split("?")[0]
    if spec.startswith(("./", "../")):
        bases = [posixpath.join(posixpath.dirname(importer), spec)]
    elif spec.startswith("/"):
        bases = [spec[1:], "public/" + spec[1:]]
    else:
        bases = next(([t + spec[len(p):] for t in targets] for p, targets in ALIASES if spec.startswith(p)), [])
    for base in (posixpath.normpath(b) for b in bases):
        for candidate in [base] + [base + e for e in sorted(EXTS)] + [base + "/index" + e for e in sorted(EXTS)]:
            if candidate in known:
                return candidate
    return None


def pascal(text):
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[-_]", text) if p)


def nuxt_components(files):
    """Nuxt auto-imports components by name: components/base/Button.vue is <BaseButton>."""
    names = {}
    for f in files:
        m = re.match(r"(?:app/)?components/(.*)\.vue$", f)
        if m:
            *dirs, stem = m.group(1).split("/")
            stem = re.sub(r"\.(?:client|server)$", "", stem)
            prefix = "".join(pascal(d) for d in dirs)
            own = pascal(stem) if stem != "index" else ""
            names[own if own.startswith(prefix) and prefix else prefix + own] = f
    return names


def import_graph(root, files, framework):
    known = set(files)
    components = nuxt_components(files) if framework == "nuxt" else {}
    graph = {}
    for f in files:
        text = read(os.path.join(root, f))
        specs = [m.group(1) for pattern in (IMPORT, CSS_IMPORT, HTML_REF) for m in pattern.finditer(text)]
        targets = {t for t in (resolve(s, f, known) for s in specs) if t and t != f}
        if components and f.endswith(".vue"):
            for tag in re.findall(r"<((?:Lazy)?[A-Z][A-Za-z0-9]*|[a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b", text):
                name = pascal(tag) if "-" in tag else tag
                target = components.get(name) or components.get(re.sub(r"^Lazy", "", name))
                if target and target != f:
                    targets.add(target)
        graph[f] = targets
    return graph


def split_by_directory(files, prefix=""):
    """Group files by their next directory below prefix; groups above SPLIT_UNIT_ABOVE split again."""
    groups = {}
    for f in files:
        rest = f[len(prefix):].split("/")
        groups.setdefault(prefix + rest[0] if len(rest) > 1 else prefix.rstrip("/") or ".", []).append(f)
    out = {}
    for key, members in groups.items():
        deeper = [f for f in members if "/" in f[len(key) + 1:]] if key != prefix.rstrip("/") and key != "." else []
        if len(members) > SPLIT_UNIT_ABOVE and deeper:
            out.update(split_by_directory(members, key + "/"))
        else:
            out[key] = members
    return out


def surfaces(root):
    files, skipped = list_files(root)
    framework = detect_framework(root)
    entries, layouts = find_routes(framework, files)
    units = []
    if entries:
        graph = import_graph(root, files, framework)
        owner, reach = {}, {f: set() for f in files}
        for route, roots in entries.items():
            for f in roots:
                owner[f] = route
            dirs = {posixpath.dirname(f) for f in roots}
            todo = list(roots) + [f for f, d in layouts.items() if any(is_under(d, x) for x in dirs)]
            seen = set()
            while todo:
                f = todo.pop()
                if f not in seen:
                    seen.add(f)
                    reach[f].add(route)
                    todo += graph.get(f, ())
        members = {route: list(roots) for route, roots in entries.items()}
        shared, unreached = [], []
        for f in files:
            if f in owner:
                continue
            if len(reach[f]) == 1:
                members[next(iter(reach[f]))].append(f)
            else:
                shared.append(f)
                if not reach[f]:
                    unreached.append(f)
        for route in sorted(members):
            units.append({"unit": route, "kind": "route", "entries": sorted(entries[route]),
                          "files": sorted(members[route])})
        groups = {"shared": shared} if len(shared) <= SPLIT_UNIT_ABOVE else \
            {"shared:" + k: v for k, v in split_by_directory(shared).items()}
        for name in sorted(groups):
            if groups[name]:
                units.append({"unit": name, "kind": "shared", "entries": [], "files": sorted(groups[name]),
                              "unreached": sorted(set(groups[name]) & set(unreached))})
    else:
        base = "src/" if files and all(f.startswith("src/") for f in files) else ""
        for name, members in sorted(split_by_directory(files, base).items()):
            units.append({"unit": name, "kind": "directory", "entries": [], "files": sorted(members)})
    for u in units:
        for key in ("entries", "files", "unreached"):
            if key in u:
                u[key] = [root_path(root, f) for f in u[key]]
    dirty = git_dirty(root)
    return {"root": root, "framework": framework, "fallback": None if entries else "directories",
            "files": len(files), "units": units, "skipped": [dict(s, file=root_path(root, s["file"])) for s in skipped],
            "dirty": [root_path(root, f) for f in files if f in dirty]}


def cmd_surfaces(argv):
    p = argparse.ArgumentParser(prog="designscan.py surfaces", description="inventory of surfaces, as JSON")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--out", help="write the inventory to this file and print one line of counts")
    a = p.parse_args(argv)
    inv = surfaces(a.root)
    text = json.dumps(inv, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        shared = sum(u["kind"] == "shared" for u in inv["units"])
        print("%d surfaces, %d shared unit%s, %d frontend files (%s)%s" % (
            len(inv["units"]) - shared, shared, "" if shared == 1 else "s", inv["files"],
            inv["fallback"] or inv["framework"],
            "; %d with uncommitted changes" % len(inv["dirty"]) if inv["dirty"] else ""))
    else:
        print(text)
    return 0


def scan_inventory(inventory_path, keep, out):
    """One scan over every file of the inventory, so duplication counts across the whole platform."""
    with open(inventory_path, encoding="utf-8") as f:
        inv = json.load(f)
    files = [f for u in inv["units"] for f in u["files"]]
    pairs, failed = read_inputs(files)
    readable = {path for _, path in pairs}
    results = iter(scan_many(pairs, keep))
    try:
        commit = subprocess.run([find_exe("git"), "-C", inv["root"], "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, timeout=30).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        commit = None
    dirty = {root_path(inv["root"], f) for f in git_dirty(inv["root"])} if commit else set()
    data = {"root": inv["root"], "framework": inv["framework"], "commit": commit,
            "dirty": [f for f in files if f in dirty],
            "units": [{"unit": u["unit"], "kind": u["kind"],
                       "files": [next(results) for f in u["files"] if f in readable]} for u in inv["units"]]}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(hits_summary(data, out))
    return 2 if failed else 0


def hits_summary(data, path):
    """Counts per unit, busiest first, and the duplication groups the caller fixes across units."""
    rows, dup = [], {}
    for u in data["units"]:
        hits = [h for r in u["files"] for h in r["hits"]]
        opened = [h for r in u["files"] for h in open_hits(r)]
        rows.append((len(hits), u["unit"], u["kind"], len(u["files"]), len(opened)))
        for r in u["files"]:
            for h in r["hits"]:
                if h["category"] == "duplication":
                    dup.setdefault((h["rule"], h["match"]), set()).add(r["file"])
    lines = ["%s: %d units, %d files, %d hits, %d open, scanned at %s" % (
        path, len(rows), sum(r[3] for r in rows), sum(r[0] for r in rows), sum(r[4] for r in rows),
        data.get("commit") or "no commit"), "| unit | kind | files | hits | open |", "|---|---|---|---|---|"]
    lines += ["| %s | %s | %d | %d | %d |" % (unit, kind, n, hits, o)
              for hits, unit, kind, n, o in sorted(rows, key=lambda r: (-r[0], r[1]))]
    dirty = data.get("dirty") or []
    if dirty:
        lines.append("uncommitted changes in %d scanned file%s, not pinned to %s: %s%s" % (
            len(dirty), "" if len(dirty) == 1 else "s", data.get("commit"), ", ".join(dirty[:10]),
            ", and %d more" % (len(dirty) - 10) if len(dirty) > 10 else ""))
    read_as = {}
    for u in data["units"]:
        for r in u["files"]:
            if r.get("read_as"):
                read_as.setdefault(r["read_as"], []).append(r["file"])
    lines += ["not UTF-8, read as %s: %s" % (enc, ", ".join(files)) for enc, files in sorted(read_as.items())]
    if dup:
        lines.append("duplication across units (%d groups):" % len(dup))
        lines += ["  %s  %d files  %s" % (rule, len(files), match[:80]) for (rule, match), files in sorted(dup.items())]
    return "\n".join(lines)


def find_unit(units, name):
    """The unit a worker names: exactly, without a route's leading slash (`pricing` for `/pricing`), or
    through Git Bash's rewrite of an argument starting with `/` into a Windows path (`C:/Program Files/Git/pricing`)."""
    exact = [u for u in units if u["unit"] == name]
    if exact:
        return exact[0]
    bare = [u for u in units if u["kind"] == "route" and u["unit"].lstrip("/") == name.strip("/")]
    if len(bare) == 1:
        return bare[0]
    if re.match(r"[A-Za-z]:/", name.replace("\\", "/")):
        rewritten = name.replace("\\", "/")
        routes = [u for u in units if u["kind"] == "route" and rewritten.endswith(u["unit"])]
        if routes:
            return max(routes, key=lambda u: len(u["unit"]))
    return None


def cmd_hits(argv):
    p = argparse.ArgumentParser(prog="designscan.py hits", description="read a hits file written with --out")
    p.add_argument("file")
    p.add_argument("unit", nargs="?", help="print this unit's results as JSON, duplication hits left out")
    a = p.parse_args(argv)
    with open(a.file, encoding="utf-8") as f:
        data = json.load(f)
    if a.unit is None:
        print(hits_summary(data, a.file))
        return 0
    unit = find_unit(data["units"], a.unit)
    if unit is None:
        print("no unit %r in %s (units: %s)" % (a.unit, a.file, ", ".join(u["unit"] for u in data["units"])),
              file=sys.stderr)
        return 2
    results = [dict(r, hits=[h for h in r["hits"] if h["category"] != "duplication"]) for r in unit["files"]]
    print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0


# --- reconcile ----------------------------------------------------------------------------
# A re-run audit compares a fresh hits file with the ledger's findings and keep file, so a
# finding whose hit is gone closes, a returning one reopens, and a hit nobody judged is new.

# the status runs to the end of the line: `rejected:wontfix (#12)` holds spaces
FINDING = re.compile(r"^### (DS-\d+) · ([^·\n]+?) · status: (\S[^\n]*?)[ \t]*$", re.M)


def ledger_path(path):
    return posixpath.normpath(path.strip().replace("\\", "/"))


def parse_findings(text):
    """Finding blocks of findings.md (schema in SKILL.md, Ledger), in file order."""
    heads = list(FINDING.finditer(text))
    found = []
    for i, m in enumerate(heads):
        body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        field = {k.lower(): v.strip() for k, v in re.findall(r"^(Surface|Hit|Where|Scanned):[ \t]*(.*)$", body, re.M)}
        rule, _, match = field.get("hit", "").partition(" · ")
        match = match.strip()
        if len(match) >= 2 and match[0] == match[-1] == "`":
            match = match[1:-1]
        where = []
        for part in field.get("where", "").split(","):
            path, _, line = part.strip().rpartition(":")
            where.append((ledger_path(path), int(line)) if path and line.isdigit() else (ledger_path(part), 0))
        found.append({"id": m.group(1), "category": m.group(2).strip(), "was": m.group(3), "rule": rule.strip(),
                      "match": match, "surface": field.get("surface", ""), "scanned": field.get("scanned", ""),
                      "where": [w for w in where if w[0] not in ("", ".")]})
    return found


def same_hit(hit, finding):
    return (hit["rule"], hit["match"]) == (finding["rule"], finding["match"])


def keep_reason(hit, keep):
    """Why a hit is kept: a keep line for it, or the keep file the scan itself read."""
    return keep.get((hit["rule"], hit["match"])) or hit.get("kept")


def next_status(was, state):
    """The status a finding takes from what the fresh scan shows; rejected findings and unchecked ones keep theirs."""
    if was.startswith("rejected") or state == "unchecked":
        return was
    if state == "fixed":
        return "fixed"
    if state == "resolved":
        return "rejected:kept"
    return "open" if was in ("fixed", "stale") else was


def reconcile(findings, data, keep):
    dirty = {ledger_path(p) for p in data.get("dirty") or []}
    fresh = []  # (unit, file, hit), unclaimed until a finding takes it
    for u in data["units"]:
        for r in u["files"]:
            fresh += [(u["unit"], r["file"], h) for h in r["hits"]]
    taken = set()

    def claim(i):
        taken.add(i)
        return fresh[i]

    out = []
    for f in findings:
        entry = {k: f[k] for k in ("id", "was", "rule", "match", "surface", "scanned")}
        entry.update(file=f["where"][0][0] if f["where"] else None, line=None)
        if f["rule"] not in RULES:
            entry["state"] = "unchecked"  # judgment-only and copy finds: no pattern can tell
        elif RULES[f["rule"]][0] == "duplication":
            # one finding per group: open while the repetition is anywhere, whichever files still carry it
            copies = [claim(i) for i, (_, _, h) in enumerate(fresh) if i not in taken and same_hit(h, f)]
            entry["state"] = "open" if copies else "fixed"
            entry["files"] = sorted({ledger_path(path) for _, path, _ in copies})
        else:
            files = {path for path, _ in f["where"]}
            candidates = [i for i, (_, path, h) in enumerate(fresh)
                          if i not in taken and ledger_path(path) in files and same_hit(h, f)]
            if candidates:
                line = f["where"][0][1] if f["where"] else 0
                i = min(candidates, key=lambda i: (abs(fresh[i][2]["line"] - line), i))
                _, path, h = claim(i)
                reason = keep_reason(h, keep)
                entry.update(state="resolved" if reason else "open", line=h["line"])
                if reason:
                    entry["reason"] = reason
            else:
                entry["state"] = "fixed"
        entry["status"] = next_status(f["was"], entry["state"])
        files = {path for path, _ in f["where"]} | set(entry.get("files", ()))
        # a group over several files names the uncommitted ones, so the others keep their permalinks
        entry["dirty_files"] = sorted(p for p in files if p in dirty)
        entry["dirty"] = bool(entry["dirty_files"])
        entry["all_dirty"] = entry["dirty"] and len(entry["dirty_files"]) == len(files)
        out.append(entry)
    new, resolved = [], []
    for i, (unit, path, h) in enumerate(fresh):
        if i in taken:
            continue
        item = {"unit": unit, "file": path, "line": h["line"], "rule": h["rule"], "category": h["category"],
                "tier": h["tier"], "match": h["match"], "dirty": ledger_path(path) in dirty}
        reason = keep_reason(h, keep)
        if reason:
            resolved.append(dict(item, reason=reason))
        else:
            new.append(item)
    return {"commit": data.get("commit"), "dirty": sorted(data.get("dirty") or []), "findings": out, "new": new,
            "resolved": resolved}


def write_findings(text, result):
    """findings.md with each block's status, its Where line and its Scanned commit taken from the reconcile;
    a finding read in a file with uncommitted changes gets `<sha>-dirty`, never a commit that does not hold it."""
    by_id = {f["id"]: f for f in result["findings"]}
    heads = list(FINDING.finditer(text))
    parts, at = [], 0
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        f, body = by_id[m.group(1)], text[m.end():end]
        parts += [text[at:m.start()], m.group(0).replace("status: " + m.group(3), "status: " + f["status"])]
        if f["state"] != "unchecked" and result["commit"]:
            commit = result["commit"] + ("-dirty" if f["dirty"] else "")
            if f["dirty"] and not f["all_dirty"]:
                commit += " (%s)" % ", ".join(f["dirty_files"])
            body = re.sub(r"^(Scanned:[ \t]*).*?[ \t]*$", lambda s: s.group(1) + commit, body, count=1, flags=re.M)
        if f["line"] is not None:
            body = re.sub(r"^(Where:[ \t]*[^,\n]+:)\d+[ \t]*$", lambda s: "%s%d" % (s.group(1), f["line"]), body,
                          count=1, flags=re.M)
        parts.append(body)
        at = end
    return "".join(parts) + text[at:]


def reconcile_summary(result, path):
    changed = [f for f in result["findings"] if f["status"] != f["was"]]
    counts = {}
    for f in result["findings"]:
        counts[f["state"]] = counts.get(f["state"], 0) + 1
    lines = ["%s: %d findings (%s), %d status changes, %d new hits, %d kept hits resolved, scanned at %s" % (
        path, len(result["findings"]), ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none",
        len(changed), len(result["new"]), len(result["resolved"]), result["commit"] or "no commit")]
    lines += ["  %s  %s -> %s  (%s)" % (f["id"], f["was"], f["status"], f["state"]) for f in changed]
    if result["new"]:
        lines.append("new hits, to judge:")
        lines += ["  %s  %s:%d  %s %s  %s%s" % (n["unit"], n["file"], n["line"], n["tier"], n["rule"], n["match"],
                                               "  (uncommitted)" if n["dirty"] else "") for n in result["new"]]
    return "\n".join(lines)


def cmd_reconcile(argv):
    p = argparse.ArgumentParser(prog="designscan.py reconcile",
                                description="compare a fresh hits file with the ledger's findings and keep file")
    p.add_argument("findings", help="the ledger's findings.md")
    p.add_argument("hits", help="a hits file written by --surfaces ... --out after the fixes")
    p.add_argument("--keep", help="the ledger's keep file")
    p.add_argument("--json", action="store_true", help="print every finding and hit as JSON")
    p.add_argument("--write", action="store_true",
                   help="update findings.md in place: statuses, lines and the commit the fresh scan confirmed")
    a = p.parse_args(argv)
    text = read(a.findings)
    findings = parse_findings(text)
    with open(a.hits, encoding="utf-8") as f:
        data = json.load(f)
    result = reconcile(findings, data, load_keep(a.keep))
    if a.write:
        with open(a.findings, "w", encoding="utf-8", newline="\n") as f:
            f.write(write_findings(text, result))
    print(json.dumps(result, ensure_ascii=False, indent=1) if a.json else reconcile_summary(result, a.findings))
    return 1 if result["new"] or any(f["state"] == "open" for f in result["findings"]) else 0


# --- verdicts -----------------------------------------------------------------------------
# Every judged hit becomes a verdict in the user's log; learn.py turns the log into the model
# a file scan applies (ADR 0018). Inventory scans and reconcile keep the calibrated tiers.

LOG_FIELDS = ["time", "rule", "category", "tier", "label", "reason", "source", "file", "match", "context"]
HIT_LINE = re.compile(r"^Hit: (\S+) · (.+?)\s*$", re.M)
WHERE_LINE = re.compile(r"^Where: (\S+?)(?::\d+)?\s*$", re.M)


def judge(before, after, keep):
    """(hit, label, reason) for every hit in before that was resolved; unresolved hits get label None."""
    remaining = {(h["rule"], h["match"]) for h in after["hits"]}
    for h in before["hits"]:
        reason = keep.get((h["rule"], h["match"]))
        if reason == "fp":
            yield h, "fp", "fp"
        elif reason == "handoff":
            yield h, "reflex", "handoff"
        elif reason:
            yield h, "chosen", reason
        elif (h["rule"], h["match"]) not in remaining:
            yield h, "reflex", ""
        else:
            yield h, None, ""


def judged(findings_path, keep):
    """An audit's judgments as verdicts: each scanner finding not rejected is a reflex, each keep line
    `fp`, a reflex (handoff) or chosen. The reason names the project and the finding or keep line, so a
    re-run records nothing twice and another project's judgments stay its own."""
    rows, repo = [], learn.repo_id(findings_path)
    text = read(findings_path)
    heads = list(FINDING.finditer(text))
    for i, m in enumerate(heads):
        block = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        hit, where = HIT_LINE.search(block), WHERE_LINE.search(block)
        if not hit or hit.group(1) not in RULES or m.group(3).startswith("rejected"):
            continue
        rows.append({"rule": hit.group(1), "label": "reflex", "reason": "judged:%s:%s" % (repo, m.group(1)),
                     "file": where.group(1) if where else "", "match": hit.group(2).strip("`")})
    for (rule, match), reason in keep.items():
        if rule in RULES:
            # a handoff is a reflex handed to craft, as judge() records it after a sweep
            rows.append({"rule": rule, "label": "fp" if reason == "fp" else "reflex" if reason == "handoff" else "chosen",
                         "reason": "judged:%s:keep %s" % (repo, reason), "file": "", "match": match})
    for r in rows:
        r.update(category=RULES[r["rule"]][0], tier=tier_of(r["rule"]), source="model", context="")
    return rows


def cmd_verdict(argv):
    p = argparse.ArgumentParser(prog="designscan.py verdict",
                                description="ORIG FILE pairs, all files of one sweep; or --judged FINDINGS")
    p.add_argument("pairs", nargs="*", metavar="ORIG FILE")
    p.add_argument("--judged", metavar="FINDINGS", help="an audit's findings.md: record its judgments once")
    p.add_argument("--keep")
    p.add_argument("--source", default="model", choices=["model", "human"])
    a = p.parse_args(argv)
    keep = load_keep(a.keep)
    rows, unresolved, skipped = [], 0, 0
    if a.judged:
        if a.pairs:
            p.error("give ORIG FILE pairs or --judged FINDINGS, not both")
        if not os.path.isfile(a.judged):
            print("designscan.py verdict: no findings file at %s" % a.judged, file=sys.stderr)
            return 2
        seen = learn.recorded(lambda r: (r["rule"], learn.clean(r["match"]), r["reason"]))
        for r in judged(a.judged, keep):
            if (r["rule"], learn.clean(r["match"]), r["reason"]) in seen:
                skipped += 1
            else:
                rows.append(r)
    else:
        if not a.pairs or len(a.pairs) % 2:
            p.error("give ORIG FILE pairs")
        origs, files = a.pairs[0::2], a.pairs[1::2]
        run = learn.run_id(*[read(x) for x in a.pairs])
        log = learn.read_log()
        if any(r["reason"].endswith("@" + run) for r in log):
            print("recorded 0 verdicts: this sweep (%s) is already in %s" % (run, learn.paths()[0]))
            return 0
        # this project's audit (verdict --judged) already counted these hits: the sweep that fixes them adds nothing
        repo = learn.repo_id(files[0])
        judged_hits = {(r["rule"], learn.clean(r["match"])) for r in log
                       if r["reason"].startswith("judged:%s:" % repo)}
        # scanned as one run each, so duplication is judged across the files as the sweep saw them
        befores = scan_many([(read(o), f) for o, f in zip(origs, files)])
        afters = scan_many([(read(f), f) for f in files])
        for before, after in zip(befores, afters):
            for h, label, reason in judge(before, after, keep):
                if label is None:
                    unresolved += 1
                    continue
                if (h["rule"], learn.clean(h["match"])) in judged_hits:
                    skipped += 1
                    continue
                reason = ("%s @%s" % (reason, run)).strip()
                rows.append({"rule": h["rule"], "category": h["category"], "tier": h["tier"], "label": label,
                             "reason": reason, "source": a.source, "file": before["file"], "match": h["match"],
                             "context": h["context"]})
    learn.record(rows, fields=LOG_FIELDS)
    counts = {}
    for row in rows:
        counts[row["label"]] = counts.get(row["label"], 0) + 1
    detail = ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none"
    tail = "%d already recorded" % skipped if a.judged else "%d unresolved, %d counted by the audit" % (unresolved, skipped)
    print("recorded %d verdicts (%s), %s, in %s" % (len(rows), detail, tail, learn.paths()[0]))
    model = learn.rebuild()
    for line in learn.progress(model, sorted({"%s/%s" % (r["rule"], learn.NO_LANG) for r in rows}),
                               "designscan.py audit"):
        print("  " + line)
    return 0


def main():
    learn.configure("design")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["rules"]:
        print("| rule | category | tier |\n|---|---|---|")
        for name, (cat, _, _) in RULES.items():
            print("| %s | %s | %s |" % (name, cat, tier_of(name)))
        return 0
    if sys.argv[1:2] == ["verdict"]:
        return cmd_verdict(sys.argv[2:])
    if sys.argv[1:2] and sys.argv[1] in learn.COMMANDS:
        return learn.COMMANDS[sys.argv[1]](sys.argv[2:], "designscan.py")
    if sys.argv[1:2] == ["surfaces"]:
        return cmd_surfaces(sys.argv[2:])
    if sys.argv[1:2] == ["hits"]:
        return cmd_hits(sys.argv[2:])
    if sys.argv[1:2] == ["reconcile"]:
        return cmd_reconcile(sys.argv[2:])
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*")
    p.add_argument("--json", action="store_true")
    p.add_argument("--keep")
    p.add_argument("--surfaces", metavar="INVENTORY", help="scan every file of an inventory written by `surfaces`")
    p.add_argument("--out", metavar="HITS", help="with --surfaces: write the hits grouped by unit, print a summary")
    p.add_argument("--no-learn", action="store_true", help="ignore the learned model (tiers, suppressions)")
    a = p.parse_args()
    model = learn.model_for(a.no_learn)
    if a.keep and not os.path.isfile(a.keep):
        p.error("keep file not found: %s" % a.keep)
    keep = load_keep(a.keep)
    if bool(a.surfaces) != bool(a.out) or bool(a.surfaces) == bool(a.files):
        p.error("give FILE... or --surfaces INVENTORY --out HITS")
    if a.surfaces:
        return scan_inventory(a.surfaces, keep, a.out)
    pairs, failed = read_inputs(a.files)
    results = scan_many(pairs, keep, model)
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            if r["skipped"]:
                print("%s: skipped, %s" % (r["file"], r["skipped"]))
            if r.get("read_as"):
                print("%s: not UTF-8, read as %s" % (r["file"], r["read_as"]))
            for h in r["hits"]:
                print("%s:%d  %s %-22s %s%s" % (r["file"], h["line"], h["tier"], h["rule"], h["match"],
                                               "  [kept: %s]" % h["kept"] if h["kept"] else ""))
    return 2 if failed else 1 if any(open_hits(r) for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
