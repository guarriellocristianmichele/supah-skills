#!/usr/bin/env python3
"""Measure what Claude Code loads into every session, and list contradiction candidates. Stdlib only.

  ctx.py measure [--sessions N]   per session, from its transcript: the first request's input tokens
                                  (measured by the API) and what they are made of: skill listing,
                                  deferred tool names, MCP server instructions, agent listing and hook
                                  text, each split by plugin or server; the rest is system prompt and
                                  tool schemas, which transcripts do not record
  ctx.py sources                  instruction files Claude Code reads (CLAUDE.md chain with @imports),
                                  the memory index, and the enabled plugins with always-on hooks
  ctx.py check                    deterministic candidates: broken memory links and index entries,
                                  missing paths and ADRs referenced by instructions, overlapping
                                  skills, and every imperative rule line for the model to compare

Common options: --project DIR (default: current directory), --home DIR (default: $CLAUDE_CONFIG_DIR
or ~/.claude), --json. "est" tokens are characters / 4; first-request tokens are measured.
Transcripts are read for listings and hook output only; user prompts are never printed.
"""
import argparse
import glob
import json
import os
import re
import sys

EST = 4  # characters per token, for text that has no measured count
RULE = re.compile(r"\b(must|never|always|important|do not|don't|only|"
                  r"sempre|mai|deve|devono|vietato|obbligatori[oa])\b", re.I)
PATHLIKE = re.compile(r"^[~.\w-][\w./~-]*(/[\w.-]+|\.(md|py|json|ya?ml|toml|sh|txt|tsv|js|ts))$")
TOPICS = [  # capability -> pattern over a skill's name and description
    ("test-driven development", r"tdd|test-driven|red-green"),
    ("debugging", r"debug|diagnos"),
    ("code review", r"code[- ]review|review (the|a) (diff|pull request|pr)"),
    ("simplification", r"simplif"),
    ("planning", r"implementation plans?|writing-plans|plan mode"),
    ("idea stress-testing", r"brainstorm|grill"),
    ("writing skills", r"writing-skills|skill-creator|writing-for-agents|creating or editing skills"),
    ("commit messages", r"commit message"),
    ("browser automation", r"browser|chrome|playwright"),
    ("parallel agents", r"parallel (agents|subagents)|subagent-driven|dispatching"),
]


def est(chars):
    return round(chars / EST)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(path))


def frontmatter(text):
    m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    fields = {}
    if m:
        for line in m.group(1).splitlines():
            k, sep, v = line.partition(":")
            if sep and not line.startswith((" ", "\t")):
                fields[k.strip()] = v.strip().strip("\"'")
    return fields


# ---------- measure ----------

def events(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def injected(attachment):
    """Text a hook attachment put into context, or None."""
    kind = attachment.get("type")
    content = attachment.get("content")
    if kind == "hook_additional_context":
        return "".join(content) if isinstance(content, list) else str(content or "")
    if kind == "hook_success" and content:  # plain stdout of SessionStart / UserPromptSubmit hooks
        return content if isinstance(content, str) else "".join(content)
    return None


def listing_entries(content):
    """'- plugin:name: description' entries of a skill listing."""
    entries = []
    for chunk in ("\n" + content).split("\n- ")[1:]:
        name, sep, desc = chunk.partition(": ")
        if not sep:
            name, desc = chunk.strip(), ""
        entries.append({"name": name.strip(), "description": desc.strip(), "chars": len(chunk) + 3})
    return entries


def owner(name):
    if name.startswith("mcp__"):
        return name.split("__")[1]
    return name.split(":")[0] if ":" in name else "(built-in or user)"


def measure_session(path):
    first, prompts, hooks, seen, parts = None, 0, {}, set(), {}

    def add(category, who, chars):
        bucket = parts.setdefault(category, {})
        bucket[who] = bucket.get(who, 0) + chars

    for e in events(path):
        kind = e.get("type")
        if kind == "assistant" and first is None:
            u = (e.get("message") or {}).get("usage") or {}
            first = sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                   "cache_read_input_tokens"))
        elif kind == "user" and not e.get("isMeta") and isinstance((e.get("message") or {}).get("content"), str):
            prompts += 1
        elif kind == "attachment" and isinstance(e.get("attachment"), dict):
            a = e["attachment"]
            t = a.get("type")
            if t not in seen:  # the first listing of each kind is the session's starting context
                if t == "skill_listing":
                    for entry in listing_entries(a.get("content") or ""):
                        add("skill listing", owner(entry["name"]), entry["chars"])
                elif t == "deferred_tools_delta":
                    for line in a.get("addedLines") or []:
                        add("deferred tool names", owner((line.split() or [""])[0]), len(line) + 1)
                elif t == "mcp_instructions_delta":
                    for name, block in zip(a.get("addedNames") or [], a.get("addedBlocks") or []):
                        add("MCP server instructions", name, len(block))
                elif t == "agent_listing_delta":
                    for line in a.get("addedLines") or []:
                        add("agent listing", owner(line[2:].split(": ")[0]), len(line) + 1)
                seen.add(t)
            text = injected(a)
            if text:
                label = "%s: %s" % (a.get("hookEvent") or "?", text.strip().splitlines()[0][:60])
                h = hooks.setdefault(label, {"times": 0, "chars": 0})
                h["times"] += 1
                h["chars"] += len(text)
    breakdown = []
    for category, owners in parts.items():
        top = sorted(owners.items(), key=lambda kv: -kv[1])
        breakdown.append({"category": category, "est_tokens": est(sum(owners.values())),
                          "by_owner": [{"owner": o, "est_tokens": est(c)} for o, c in top]})
    breakdown.sort(key=lambda b: -b["est_tokens"])
    hook_rows = [{"source": k, "times": v["times"], "est_tokens": est(v["chars"])}
                 for k, v in sorted(hooks.items(), key=lambda kv: -kv[1]["chars"])]
    at_start = sum(b["est_tokens"] for b in breakdown) + sum(
        h["est_tokens"] for h in hook_rows if h["source"].startswith("SessionStart"))
    return {"session": os.path.basename(path)[:8], "first_request_tokens": first, "prompts": prompts,
            "breakdown": breakdown, "hooks": hook_rows,
            "unattributed_tokens": first - at_start if first else None}


def transcripts(home, project):
    return sorted(glob.glob(os.path.join(home, "projects", slug(project), "*.jsonl")),
                  key=os.path.getmtime, reverse=True)


def measure(home, project, n):
    return [measure_session(f) for f in transcripts(home, project)[:n]]


def latest_listing(home, project):
    for path in transcripts(home, project):
        for e in events(path):
            a = e.get("attachment") if e.get("type") == "attachment" else None
            if isinstance(a, dict) and a.get("type") == "skill_listing":
                return listing_entries(a.get("content") or "")
    return []


# ---------- sources ----------

def imports(path, seen, depth=0):
    """CLAUDE.md plus the files it pulls in with @path, outside code fences."""
    path = os.path.abspath(path)
    if path in seen or depth > 5 or not os.path.isfile(path):
        return []
    seen.add(path)
    text = read(path)
    found = [(path, len(text))]
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    for ref in re.findall(r"(?<![\w`])@([~./\w-][^\s`)]*)", body):
        target = os.path.expanduser(ref) if ref.startswith("~") else os.path.join(os.path.dirname(path), ref)
        found += imports(target, seen, depth + 1)
    return found


def instruction_files(home, project):
    seen = set()
    files = imports(os.path.join(home, "CLAUDE.md"), seen)
    folder = os.path.abspath(project)
    while True:
        for name in ("CLAUDE.md", "CLAUDE.local.md", os.path.join(".claude", "CLAUDE.md")):
            files += imports(os.path.join(folder, name), seen)
        parent = os.path.dirname(folder)
        if parent == folder:
            return files
        folder = parent


def memory_dir(home, project):
    return os.path.join(home, "projects", slug(project), "memory")


def enabled_plugins(home, project):
    enabled = {}
    for path in (os.path.join(home, "settings.json"), os.path.join(project, ".claude", "settings.json"),
                 os.path.join(project, ".claude", "settings.local.json")):
        enabled.update(load_json(path).get("enabledPlugins") or {})
    installed = load_json(os.path.join(home, "plugins", "installed_plugins.json")).get("plugins") or {}
    return {key: installed[key][-1].get("installPath") or "" for key, on in enabled.items()
            if on and installed.get(key)}


def plugin_hook_events(root):
    declared = dict(load_json(os.path.join(root, "hooks", "hooks.json")).get("hooks") or {})
    inline = load_json(os.path.join(root, ".claude-plugin", "plugin.json")).get("hooks")
    if isinstance(inline, dict):
        declared.update(inline.get("hooks", inline))
    elif isinstance(inline, str):
        declared.update(load_json(os.path.join(root, inline)).get("hooks") or {})
    return sorted(e for e in declared if e in ("SessionStart", "UserPromptSubmit"))


def sources(home, project):
    rows = [{"source": p, "kind": "instructions", "est_tokens": est(c)} for p, c in instruction_files(home, project)]
    index = os.path.join(memory_dir(home, project), "MEMORY.md")
    if os.path.isfile(index):
        rows.append({"source": index, "kind": "memory index", "est_tokens": est(len(read(index)))})
    hooks = {}
    for key, root in enabled_plugins(home, project).items():
        found = plugin_hook_events(root)
        if found:
            hooks[key] = found
    return {"sources": sorted(rows, key=lambda r: -r["est_tokens"]), "always_on_hooks": hooks}


# ---------- check ----------

def memory_findings(home, project):
    folder = memory_dir(home, project)
    if not os.path.isdir(folder):
        return []
    found = []
    files = sorted(p for p in glob.glob(os.path.join(folder, "*.md")) if os.path.basename(p) != "MEMORY.md")
    names = {frontmatter(read(p)).get("name") or os.path.basename(p)[:-3] for p in files}
    linked = set(re.findall(r"\]\(([^)]+\.md)\)", read(os.path.join(folder, "MEMORY.md"))))
    for target in sorted(linked):
        if not os.path.isfile(os.path.join(folder, target)):
            found.append({"kind": "index-missing-file", "where": "MEMORY.md", "what": target})
    for p in files:
        if os.path.basename(p) not in linked:
            found.append({"kind": "memory-not-indexed", "where": os.path.basename(p), "what": ""})
        for ref in re.findall(r"\[\[([^\]]+)\]\]", read(p)):
            if ref not in names:
                found.append({"kind": "dangling-memory-link", "where": os.path.basename(p), "what": ref})
    return found


def project_names(project):
    names = set()
    for _, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".calibration")]
        names.update(files)
        names.update(dirs)
    return names


def reference_findings(project, texts):
    found, names = [], None
    adr_dir = os.path.join(project, "docs", "adr")
    for where, text in texts:
        for ref in sorted(set(re.findall(r"`([^`\s]+)`", text))):
            ref = ref.rstrip(".,:;")
            if not PATHLIKE.match(ref) or re.search(r"[<>*{}$|]", ref) or ref.startswith(("http", "-")):
                continue
            if "/" in ref.strip("/"):
                ok = os.path.exists(os.path.expanduser(ref) if ref.startswith("~") else os.path.join(project, ref))
            else:  # a bare name: anywhere in the project will do
                names = project_names(project) if names is None else names
                ok = ref.strip("/") in names
            if not ok:
                found.append({"kind": "missing-path", "where": where, "what": ref})
        if os.path.isdir(adr_dir):
            for num in sorted(set(re.findall(r"\bADR[ -]?(\d{1,4})\b", text))):
                if not glob.glob(os.path.join(adr_dir, "%04d-*.md" % int(num))):
                    found.append({"kind": "missing-adr", "where": where, "what": "ADR " + num})
    return found


def overlaps(entries):
    """Topics covered by skills from more than one owner: candidates for duplicate triggers."""
    groups = []
    for topic, pattern in TOPICS:
        hits = [e["name"] for e in entries if re.search(pattern, e["name"] + " " + e["description"], re.I)]
        if len({owner(n) for n in hits}) > 1:
            groups.append({"kind": "overlapping-skills", "topic": topic, "skills": hits})
    return groups


def rule_lines(texts):
    rows = []
    for where, text in texts:
        for n, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if s and RULE.search(s) and not s.startswith(("```", "|---")):
                rows.append({"where": where, "line": n, "text": s[:200]})
    return rows


def hook_texts(home, project):
    found, seen = [], set()
    for path in transcripts(home, project)[:1]:
        for e in events(path):
            a = e.get("attachment") if e.get("type") == "attachment" else None
            text = injected(a) if isinstance(a, dict) else None
            if text and text[:80] not in seen:
                seen.add(text[:80])
                found.append(("hook %s" % a.get("hookEvent"), text))
    return found


def check(home, project):
    texts = [(p, read(p)) for p, _ in instruction_files(home, project)]
    agents_md = os.path.abspath(os.path.join(project, "AGENTS.md"))
    if os.path.isfile(agents_md) and all(agents_md != p for p, _ in texts):
        texts.append((agents_md, read(agents_md)))
    memory = [(p, read(p)) for p in sorted(glob.glob(os.path.join(memory_dir(home, project), "*.md")))]
    root = os.path.abspath(project)
    rel = [(os.path.relpath(p, root) if p.startswith(root) else os.path.basename(p), t) for p, t in texts + memory]
    return {"memory": memory_findings(home, project),
            "references": reference_findings(project, rel),
            "overlapping_skills": overlaps(latest_listing(home, project)),
            "rules": rule_lines(rel + hook_texts(home, project))}


# ---------- output ----------

def print_text(cmd, data):
    if cmd == "measure":
        for s in data:
            print("session %s: first request %s tokens (measured), %d prompts" % (
                s["session"], s["first_request_tokens"], s["prompts"]))
            for b in s["breakdown"]:
                top = ", ".join("%s %d" % (o["owner"], o["est_tokens"]) for o in b["by_owner"][:5])
                print("  %6d est  %-24s %s" % (b["est_tokens"], b["category"], top))
            for h in s["hooks"]:
                print("  %6d est  hook x%-4d %s" % (h["est_tokens"], h["times"], h["source"]))
            if s["unattributed_tokens"] is not None:
                print("  %6d      system prompt and tool schemas (not in the transcript)" % s["unattributed_tokens"])
    elif cmd == "sources":
        for r in data["sources"]:
            print("%6d est  %-13s %s" % (r["est_tokens"], r["kind"], r["source"]))
        print("always-on hooks: " + (", ".join("%s (%s)" % (k, "+".join(v))
                                              for k, v in data["always_on_hooks"].items()) or "none"))
    else:
        for f in data["memory"] + data["references"]:
            print("%-22s %s %s" % (f["kind"], f["where"], f["what"]))
        for g in data["overlapping_skills"]:
            print("overlapping-skills     %s: %s" % (g["topic"], ", ".join(g["skills"])))
        print("rules: %d lines (--json lists them)" % len(data["rules"]))


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("measure", "sources", "check"))
    p.add_argument("--project", default=os.getcwd())
    p.add_argument("--home", default=os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))
    p.add_argument("--sessions", type=int, default=3)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    project = os.path.abspath(a.project)
    if a.command == "measure":
        data = measure(a.home, project, a.sessions)
    elif a.command == "sources":
        data = sources(a.home, project)
    else:
        data = check(a.home, project)
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        print_text(a.command, data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
