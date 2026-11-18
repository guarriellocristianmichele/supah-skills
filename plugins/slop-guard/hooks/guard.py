#!/usr/bin/env python3
"""slop-guard hooks for Claude Code. Stdlib only.

  guard.py session   print rules.md; SessionStart adds stdout to Claude's context
  guard.py post      PostToolUse on Write/Edit/MultiEdit: scan only what was just written
                     (prose: the new text; Python/JS/TS: the saved file, keeping hits on the new
                     lines); unresolved S/M hits go to stderr in one line with exit 2 (Claude
                     reads it), anything else exits 0 with no output

../scanner and ../codescan are copies of skills/ai-slop-prose/scripts and skills/ai-slop-audit/scripts
kept equal by scripts/release.py, because an installed plugin cannot reach files outside its folder.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
PROSE = (".md", ".mdx", ".markdown", ".txt", ".rst")
CODE = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
AGENT_DOCS = {"skill.md", "agents.md", "claude.md", "gemini.md", "memory.md"}
SHOWN = 6


def session():
    with open(os.path.join(HERE, "rules.md"), encoding="utf-8") as f:
        sys.stdout.write(f.read())
    return 0


def written(tool_input):
    """The text the tool wrote; a field of the wrong type writes nothing."""
    if "content" in tool_input:
        texts = [tool_input["content"]]
    elif "edits" in tool_input:
        edits = tool_input["edits"] if isinstance(tool_input["edits"], list) else []
        texts = [e.get("new_string") for e in edits if isinstance(e, dict)]
    else:
        texts = [tool_input.get("new_string")]
    return [t for t in texts if isinstance(t, str)]


def for_agents(path):
    """Agent-facing documents are out of scope: SKILL.md and friends, anything under .claude/,
    and the reference files that sit next to a SKILL.md (READMEs there are for people)."""
    name = os.path.basename(path).lower()
    parts = path.replace("\\", "/").lower().split("/")
    if name in AGENT_DOCS or ".claude" in parts:
        return True
    if name == "readme.md":
        return False
    folder = os.path.dirname(path)
    for _ in range(3):
        if os.path.exists(os.path.join(folder, "SKILL.md")):
            return True
        folder = os.path.dirname(folder)
    return False


def prose_items(path, texts):
    sys.path.insert(0, os.path.join(PLUGIN, "scanner"))
    import learn
    import scan
    result = scan.scan_text("\n".join(texts), "auto", {}, model=learn.load_model(), path=path)
    hits = ['%s "%s"' % (h["rule"], h["match"].strip()) for h in result["hits"]
            if not h["kept"] and h["tier"] in ("S", "M")]
    return hits, result["flags"]


def new_lines(source, texts):
    """Line numbers of the saved file that hold the text just written."""
    lines = set()
    for text in texts:
        at = source.find(text) if text else -1
        if at >= 0:
            first = source.count("\n", 0, at) + 1
            lines.update(range(first, first + text.count("\n") + 1))
    return lines


def code_items(path, texts):
    sys.path.insert(0, os.path.join(PLUGIN, "codescan"))
    import codescan
    with open(path, encoding="utf-8", errors="replace") as f:
        source = f.read()
    result = codescan.scan_text(source, path)
    fresh = new_lines(source, texts)
    return ['%s "%s"' % (h["rule"], h["match"].strip()) for h in codescan.open_hits(result)
            if h["line"] in fresh], []


def post():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") if isinstance(event, dict) else None
    if not isinstance(tool_input, dict):
        return 0
    path = tool_input.get("file_path")
    texts = [t for t in written(tool_input) if t.strip()]
    if not isinstance(path, str) or not texts or for_agents(path):
        return 0
    lower = path.lower()
    if lower.endswith(PROSE):
        hits, flags = prose_items(path, texts)
    elif lower.endswith(CODE) and os.path.isfile(path):
        hits, flags = code_items(path, texts)
    else:
        return 0
    counts = {}
    for key in hits:
        counts[key] = counts.get(key, 0) + 1
    items = [k if n == 1 else "%s x%d" % (k, n) for k, n in counts.items()]
    if len(items) > SHOWN:
        items = items[:SHOWN] + ["+%d more" % (len(items) - SHOWN)]
    items += flags
    if not items:
        return 0
    sys.stderr.write("slop-guard %s: %s. Rewrite them; leave a quote or a term as it is.\n"
                     % (os.path.basename(path), "; ".join(items)))
    return 2


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "session":
        return session()
    if command == "post":
        return post()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
