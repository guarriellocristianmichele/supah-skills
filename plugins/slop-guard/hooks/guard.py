#!/usr/bin/env python3
"""slop-guard hooks for Claude Code. Stdlib only.

  guard.py session   print rules.md; SessionStart adds stdout to Claude's context
  guard.py post      PostToolUse on Write/Edit/MultiEdit: scan only the prose just written;
                     unresolved S/M tells go to stderr in one line with exit 2 (Claude reads it),
                     anything else exits 0 with no output

The scanner in ../scanner is a copy of skills/ai-slop-prose/scripts kept equal by
scripts/release.py, because an installed plugin cannot reach files outside its folder.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(os.path.dirname(HERE), "scanner")
PROSE = (".md", ".mdx", ".markdown", ".txt", ".rst")
AGENT_DOCS = {"skill.md", "agents.md", "claude.md", "gemini.md", "memory.md"}
SHOWN = 6


def session():
    with open(os.path.join(HERE, "rules.md"), encoding="utf-8") as f:
        sys.stdout.write(f.read())
    return 0


def written(tool_input):
    if "content" in tool_input:
        return tool_input["content"]
    if "edits" in tool_input:
        return "\n".join(e.get("new_string", "") for e in tool_input["edits"])
    return tool_input.get("new_string", "")


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


def post():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    text = written(tool_input)
    if not path.lower().endswith(PROSE) or not text.strip() or for_agents(path):
        return 0
    sys.path.insert(0, SCANNER)
    import learn
    import scan
    result = scan.scan_text(text, "auto", {}, model=learn.load_model(), path=path)
    counts = {}
    for h in result["hits"]:
        if not h["kept"] and h["tier"] in ("S", "M"):
            key = '%s "%s"' % (h["rule"], h["match"].strip())
            counts[key] = counts.get(key, 0) + 1
    items = [k if n == 1 else "%s x%d" % (k, n) for k, n in counts.items()]
    if len(items) > SHOWN:
        items = items[:SHOWN] + ["+%d more" % (len(items) - SHOWN)]
    items += result["flags"]
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
