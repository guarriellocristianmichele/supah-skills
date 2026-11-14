#!/usr/bin/env python3
"""Deterministic scanner for mechanical AI slop in Python and JavaScript/TypeScript. Stdlib only.

  codescan.py [--json] [--keep FILE] FILE...
      List every catalogued pattern with line, rule, category and tier.
      Exit 0 when nothing is left to resolve (no open S or M hit), else 1.
  codescan.py rules
      Print every rule with category, tier and languages.

Python is read with ast and tokenize, so comments, strings and structure are exact; a file
whose syntax this interpreter cannot parse is reported as skipped. JavaScript and TypeScript
are read line by line with regular expressions, so their rules are narrower.

Tiers: S = one hit is enough; M = fix unless there is a keep reason; W = review only.
Keep file: TSV lines `rule<TAB>matched text<TAB>reason`; matching hits count as resolved.
The scanner finds candidates; whether a hit is slop is decided by reading it (ADR 0003).
"""
import argparse
import ast
import io
import json
import os
import re
import sys
import tokenize
import warnings

CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codescan-calibration.json")
PY = (".py",)
JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")

# rule -> (category, designed tier, languages)
RULES = {
    "placeholder": ("residue", "S", "py js"),
    "changelog-comment": ("comment-noise", "M", "py js"),
    "step-comment": ("comment-noise", "M", "py js"),
    "restating-comment": ("comment-noise", "M", "py js"),
    "restating-docstring": ("comment-noise", "M", "py"),
    "emoji-output": ("residue", "M", "py js"),
    "catch-rethrow": ("defensive-check", "M", "py js"),
    "swallowed-exception": ("defensive-check", "M", "py js"),
    "annotated-isinstance": ("defensive-check", "M", "py"),
    "forwarding-wrapper": ("wrapper", "M", "py js"),
    "bool-return": ("verbose-logic", "W", "py"),
}

VERBS = ("open|load|return|call|create|get|set|initiali[sz]e|init|check|loop|iterate|increment|import|define|"
         "print|save|read|write|parse|add|update|append|convert|calculate|compute|send|fetch|close|raise|throw|"
         "log|validate|instantiate|declare|assign|export")
RESTATING = re.compile(r"^\s*(%s)s?\b(\s+\w+){0,4}\s*\.?\s*$" % VERBS, re.I)
# an edit narrated to a reviewer, not a fact about the code: "Fixed header" and "Modified BSD License" stay out
CHANGELOG = re.compile(r"^\s*((Updated|Changed|Modified|Refactored|Moved|Switched) (to|from|so|for)\b|"
                       r"Now (uses|handles|returns|supports|calls)\b|(Fixed|Fix) (the|a) (bug|issue|problem)\b|"
                       r"Replaced \S+( \S+)? with\b|Added (to|for) (handle|handling|support|fix)\b)")
STEP = re.compile(r"^\s*(Step\s+\d+|\d+\.)\s*[:.)-]?\s+[A-Za-z]")
PLACEHOLDER = re.compile(r"(\bTODO:?\s*implement\b|(\.\.\.|…)\s*(rest|existing|remaining|other)\b|"
                         r"\byour (code|implementation|logic) (goes )?here|\bimplementation (goes )?here|"
                         r"\badd (your )?(logic|code) here)", re.I)
EMOJI = re.compile("[✅❌⚠✨⭐\U0001F300-\U0001FAFF]")
OUTPUT_CALL = re.compile(r"\b(print|console\.(log|info|warn|error)|logger\.\w+|logging\.\w+|log\.\w+)\s*\(")
WORD = re.compile(r"[A-Za-z][a-z]*|[A-Z]+(?![a-z])")
STOPWORDS = {"the", "a", "an", "of", "to", "this", "that", "it", "and", "for", "from", "with"}


def name_words(name):
    return {w.lower() for part in name.split("_") for w in WORD.findall(part)}


def tier_of(rule, lang):
    tier = RULES[rule][1]
    if os.path.exists(CALIBRATION_FILE) and not os.environ.get("SUPAH_CODE_NO_CALIBRATION"):
        with open(CALIBRATION_FILE, encoding="utf-8") as f:
            tier = json.load(f).get("rules", {}).get("%s/%s" % (rule, lang), {}).get("tier", tier)
    return tier


def comment_hits(text, line, next_code):
    """Rules that judge one comment's text; next_code is the source line it sits above."""
    found = []
    if PLACEHOLDER.search(text):
        found.append(("placeholder", text))
    elif CHANGELOG.match(text):
        found.append(("changelog-comment", text))
    elif STEP.match(text):
        found.append(("step-comment", text))
    else:
        m = RESTATING.match(text)
        if m and next_code and m.group(1).lower()[:4] in next_code.lower():
            found.append(("restating-comment", text))
    return [(rule, line, match) for rule, match in found]


# ---------- Python ----------

def py_comments(source):
    lines = source.splitlines()
    out = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return out
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        row = tok.start[0]
        own_line = lines[row - 1][:tok.start[1]].strip() == ""
        text = tok.string.lstrip("#").strip()
        nxt = ""
        if own_line:
            for later in lines[row:]:
                if later.strip() and not later.strip().startswith("#"):
                    nxt = later.strip()
                    break
        if own_line or PLACEHOLDER.search(text):
            out += comment_hits(text, row, nxt)
    return out


def is_raise_of(stmt, name):
    return isinstance(stmt, ast.Raise) and stmt.cause is None and (
        stmt.exc is None or (name and isinstance(stmt.exc, ast.Name) and stmt.exc.id == name))


def broad(handler):
    t = handler.type
    return t is None or (isinstance(t, ast.Name) and t.id in ("Exception", "BaseException"))


def returns_const(stmts, value):
    return (len(stmts) == 1 and isinstance(stmts[0], ast.Return) and isinstance(stmts[0].value, ast.Constant)
            and stmts[0].value.value is value)


def forwards(fn):
    """def f(a, b): return g(a, b), with nothing added: no decorator, default, or transformation."""
    if fn.decorator_list or fn.name.startswith("__"):
        return False
    body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                           and isinstance(fn.body[0].value, ast.Constant)
                           and isinstance(fn.body[0].value.value, str)) else fn.body
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    call = body[0].value
    if isinstance(call, ast.Await):
        call = call.value
    if not isinstance(call, ast.Call) or call.keywords:
        return False
    a = fn.args
    if a.defaults or a.kw_defaults or a.vararg or a.kwarg or a.kwonlyargs:
        return False
    params = [p.arg for p in a.posonlyargs + a.args]
    if params and params[0] in ("self", "cls"):
        return False
    target = call.func
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id in ("self", "cls"):
        return False
    args = [x.id if isinstance(x, ast.Name) else None for x in call.args]
    return bool(params) and args == params


def py_hits(source):
    with warnings.catch_warnings():  # invalid escapes in the scanned code are not our report
        warnings.simplefilter("ignore")
        tree = ast.parse(source)
    lines = source.splitlines()
    hits = py_comments(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            for i, handler in enumerate(node.handlers):
                last = i == len(node.handlers) - 1  # an earlier bare raise lets some errors past a later handler
                if last and len(handler.body) == 1 and is_raise_of(handler.body[0], handler.name):
                    hits.append(("catch-rethrow", handler.lineno, lines[handler.lineno - 1].strip()))
                elif broad(handler) and len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass) \
                        and "#" not in lines[handler.body[0].lineno - 1]:
                    hits.append(("swallowed-exception", handler.lineno, lines[handler.lineno - 1].strip()))
        elif isinstance(node, ast.If):
            if (returns_const(node.body, True) and returns_const(node.orelse, False)) or \
                    (returns_const(node.body, False) and returns_const(node.orelse, True)):
                hits.append(("bool-return", node.lineno, lines[node.lineno - 1].strip()))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if forwards(node):
                hits.append(("forwarding-wrapper", node.lineno, "def %s" % node.name))
            doc = ast.get_docstring(node)
            if doc and "\n" not in doc.strip() and len(doc.split()) >= 2 and "(" not in doc:
                words = {w.lower() for w in WORD.findall(doc)} - STOPWORDS
                if words and words <= name_words(node.name) | {"returns", "gets", "sets"}:
                    hits.append(("restating-docstring", node.body[0].lineno, doc.strip()))
            annotated = {p.arg: p.annotation.id for p in node.args.args
                         if isinstance(p.annotation, ast.Name)}
            for sub in ast.walk(node):
                if isinstance(sub, ast.If) and any(isinstance(s, ast.Raise) for s in sub.body):
                    for call in ast.walk(sub.test):
                        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                                and call.func.id == "isinstance" and len(call.args) == 2
                                and isinstance(call.args[0], ast.Name) and isinstance(call.args[1], ast.Name)
                                and annotated.get(call.args[0].id) == call.args[1].id):
                            hits.append(("annotated-isinstance", sub.lineno, lines[sub.lineno - 1].strip()))
        elif isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            src = lines[node.lineno - 1]
            if OUTPUT_CALL.search(src) and any(isinstance(a, (ast.Constant, ast.JoinedStr)) and EMOJI.search(
                    ast.get_source_segment(source, a) or "") for a in node.args):
                hits.append(("emoji-output", node.lineno, src.strip()))
    return hits


# ---------- JavaScript / TypeScript ----------

JS_CATCH_RETHROW = re.compile(r"catch\s*\(\s*(\w+)\s*\)\s*\{\s*throw\s+\1\s*;?\s*\}")
JS_EMPTY_CATCH = re.compile(r"catch\s*(\(\s*\w*\s*\))?\s*\{\s*\}")
JS_FORWARD = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\{\s*"
                        r"return\s+(?:await\s+)?([\w.]+)\s*\(([^)]*)\)\s*;?\s*\}")


def js_params(text):
    names = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part or part.startswith(("...", "{", "[")):
            return None
        names.append(part.split(":")[0].strip().rstrip("?"))
    return names


def js_hits(source):
    lines = source.splitlines()
    hits = []
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if s.startswith("//"):
            nxt = next((l.strip() for l in lines[i:] if l.strip() and not l.strip().startswith("//")), "")
            hits += comment_hits(s[2:].strip(), i, nxt)
        elif "//" in s and PLACEHOLDER.search(s.split("//", 1)[1]):
            hits.append(("placeholder", i, s))
        if OUTPUT_CALL.search(s) and EMOJI.search(s):
            hits.append(("emoji-output", i, s))
    flat = source
    for pattern, rule in ((JS_CATCH_RETHROW, "catch-rethrow"), (JS_EMPTY_CATCH, "swallowed-exception")):
        for m in pattern.finditer(flat):
            hits.append((rule, flat.count("\n", 0, m.start()) + 1, re.sub(r"\s+", " ", m.group(0))))
    for m in JS_FORWARD.finditer(flat):
        params, args = js_params(m.group(2)), js_params(m.group(4))
        if params and params == args:
            hits.append(("forwarding-wrapper", flat.count("\n", 0, m.start()) + 1, "function %s" % m.group(1)))
    return hits


# ---------- driver ----------

def language(path):
    ext = os.path.splitext(path)[1].lower()
    return "py" if ext in PY else "js" if ext in JS else None


def scan_text(source, path, keep=None):
    lang = language(path)
    result = {"file": path, "lang": lang, "skipped": None, "hits": []}
    if lang is None:
        result["skipped"] = "not Python, JavaScript or TypeScript"
        return result
    try:
        raw = py_hits(source) if lang == "py" else js_hits(source)
    except SyntaxError as e:
        result["skipped"] = "syntax this Python %d.%d cannot parse (line %s)" % (
            sys.version_info[0], sys.version_info[1], e.lineno)
        return result
    keep = keep or {}
    seen = set()
    for rule, line, match in sorted(raw, key=lambda h: (h[1], h[0])):
        if (rule, line) in seen:
            continue
        seen.add((rule, line))
        category = RULES[rule][0]
        result["hits"].append({"line": line, "rule": rule, "category": category, "tier": tier_of(rule, lang),
                               "match": match[:120], "kept": keep.get((rule, match[:120]))})
    return result


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


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["rules"]:
        print("| rule | category | tier | languages |\n|---|---|---|---|")
        for rule, (cat, tier, langs) in RULES.items():
            print("| %s | %s | %s | %s |" % (rule, cat, "/".join(tier_of(rule, l) for l in langs.split()), langs))
        return 0
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+")
    p.add_argument("--json", action="store_true")
    p.add_argument("--keep")
    a = p.parse_args()
    keep = load_keep(a.keep)
    results = []
    for path in a.files:
        with open(path, encoding="utf-8", errors="replace") as f:
            results.append(scan_text(f.read(), path, keep))
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            if r["skipped"]:
                print("%s: skipped, %s" % (r["file"], r["skipped"]))
            for h in r["hits"]:
                print("%s:%d  %s %-20s %s%s" % (r["file"], h["line"], h["tier"], h["rule"], h["match"],
                                               "  [kept: %s]" % h["kept"] if h["kept"] else ""))
    return 1 if any(open_hits(r) for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
