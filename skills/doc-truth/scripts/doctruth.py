#!/usr/bin/env python3
"""Check what Markdown docs claim about a repository against the repository. Stdlib only; runs nothing.

  doctruth.py [--root DIR] [--json] [--keep FILE] FILE...
      List every claim that does not hold, with file, line, kind and tier.
      Exit 0 when nothing is left to resolve (no open S or M finding), else 1.

Claims checked:
  relative links and their #anchors             link-missing (S), anchor-missing (M)
  repo paths in code spans                      path-missing (W: docs often name paths in the user's project)
  shell blocks: local scripts                   script-missing (S)
                npm/pnpm/yarn/bun run X         package-script-missing (S)
                make X                          make-target-missing (S)
                --flags passed to a local script  flag-unknown (M: the flag is not in the script's source)
                commands not on this PATH       not-installed (W)
  ENV_VARS in code spans or `export X=`        env-unread (M: no source file reads the name)

Keep file: TSV lines `kind<TAB>claim<TAB>reason` for deliberate exceptions (a path the program creates,
a link to a file generated at build time). The scanner finds candidates; whether the doc or the code is
wrong is decided by reading both (ADR 0003).
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

TIERS = {"link-missing": "S", "script-missing": "S", "package-script-missing": "S", "make-target-missing": "S",
         "anchor-missing": "M", "path-missing": "W", "flag-unknown": "M", "env-unread": "M", "not-installed": "W"}
SHELL_LANGS = {"sh", "bash", "shell", "console", "zsh", "terminal", ""}
SOURCE_EXT = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".php", ".java", ".kt",
              ".cs", ".sh", ".ps1", ".toml", ".yml", ".yaml", ".json", ".env.example", ".cfg", ".ini")
PATHLIKE = re.compile(r"^(\./|\.\./)?[\w.-]+(/[\w.@-]+)+/?$|^[\w-]+\.(md|py|json|ya?ml|toml|sh|js|ts|txt|tsv|cfg|ini)$")
ENV = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$")
PLACEHOLDER = re.compile(r"[<>*{}$]|\b(NNNN|DIR|PATH|FILE|NAME|SLUG|X+|Y+)\b")  # docs/adr/NNNN-slug.md, DIR/state.json
WRAPPERS = {"sudo", "env", "time", "npx", "pnpx", "bunx", "uvx", "exec"}
INTERPRETERS = {"python", "python3", "py", "node", "bash", "sh", "pwsh", "powershell", "ruby", "deno", "bun", "tsx", "ts-node"}
WELL_KNOWN_ENV = {"PATH", "HOME", "USERPROFILE", "PWD", "SHELL", "TERM", "LANG", "TMPDIR", "TEMP", "NODE_ENV",
                  "CI", "GITHUB_TOKEN", "EDITOR"}


def slug(heading):
    """GitHub's anchor for a heading."""
    text = re.sub(r"[`*_~\[\]()]|<[^>]+>", "", heading.strip().lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path, cache={}):
    if path not in cache:
        found, fence = set(), False
        try:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            lines = []
        counts = {}
        for line in lines:
            if line.lstrip().startswith(("```", "~~~")):
                fence = not fence
            m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
            if m and not fence:
                s = slug(m.group(1))
                n = counts.get(s, 0)
                counts[s] = n + 1
                found.add(s if n == 0 else "%s-%d" % (s, n))
        found.update(re.findall(r'<a\s+(?:name|id)="([^"]+)"', "\n".join(lines)))
        cache[path] = found
    return cache[path]


def tracked_sources(root, every=False):
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
        files = out.splitlines()
    except (OSError, subprocess.CalledProcessError):
        files = []
        for folder, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")]
            files += [os.path.relpath(os.path.join(folder, n), root) for n in names]
    if every:
        return files
    return [f for f in files if f.endswith(SOURCE_EXT) or os.path.basename(f) in ("Dockerfile", "Makefile")]


def blocks(text):
    """(language, first line number, lines) for fenced blocks, and the prose lines outside them."""
    fenced, prose, lang, start, buf = [], [], None, 0, []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*(```|~~~)\s*([\w+-]*)", line)
        if m and lang is None:
            lang, start, buf = m.group(2).lower(), n + 1, []
        elif m and lang is not None:
            fenced.append((lang, start, buf))
            lang = None
        elif lang is not None:
            buf.append(line)
        else:
            prose.append((n, line))
    return fenced, prose


def commands(lines):
    """Logical shell commands of a block with their line offset: continuations joined, prompts stripped."""
    out, cur, at = [], "", 0
    for i, raw in enumerate(lines):
        line = re.sub(r"^\s*(\$|>|PS [^>]*>)\s+", "", raw).rstrip()
        if not cur:
            at = i
        if line.endswith("\\"):
            cur += line[:-1] + " "
            continue
        cur += line
        if cur.strip() and not cur.lstrip().startswith("#"):
            out.append((at, cur.split(" #")[0].strip()))
        cur = ""
    return out


class Repo:
    def __init__(self, root):
        self.root = root
        self.sources = None
        self.package = None
        self.make = None

    def exists(self, rel, base):
        rel = rel.split("#")[0].split("?")[0]
        if not rel:
            return True
        if any(os.path.exists(os.path.normpath(os.path.join(b, rel))) for b in (base, self.root)):
            return True
        if "/" not in rel.strip("/"):  # a bare name: anywhere in the repository will do
            return rel.strip("/") in self.names()
        return False

    def names(self):
        if not hasattr(self, "_names"):
            self._names = set()
            for rel in tracked_sources(self.root, every=True):
                self._names.update(rel.replace(os.sep, "/").split("/"))
        return self._names

    def scripts(self):
        if self.package is None:
            try:
                self.package = json.load(open(os.path.join(self.root, "package.json"), encoding="utf-8")).get("scripts") or {}
            except (OSError, ValueError):
                self.package = {}
        return self.package

    def targets(self):
        if self.make is None:
            try:
                text = open(os.path.join(self.root, "Makefile"), encoding="utf-8", errors="replace").read()
                self.make = set(re.findall(r"^([\w.-]+)\s*:(?!=)", text, re.M))
            except OSError:
                self.make = set()
        return self.make

    def reads(self, name):
        if self.sources is None:
            self.sources = {}
            for rel in tracked_sources(self.root):
                try:
                    self.sources[rel] = open(os.path.join(self.root, rel), encoding="utf-8", errors="replace").read()
                except OSError:
                    pass
        return any(name in text for rel, text in self.sources.items() if not rel.endswith(".md"))


def check_command(cmd, repo, base):
    found = []
    try:
        words = shlex.split(cmd, posix=True)
    except ValueError:
        return found
    for part in " ".join(words).split(" && "):
        toks = part.split()
        while toks and ("=" in toks[0] and not toks[0].startswith("-") or toks[0] in WRAPPERS):
            toks = toks[1:]
        if not toks:
            continue
        exe, args = toks[0], toks[1:]
        script = None
        if exe in INTERPRETERS and args and not args[0].startswith("-"):
            script, args = args[0], args[1:]
        elif exe.startswith(("./", "../")) or "/" in exe and not os.path.isabs(exe):
            script = exe
        if script and re.search(r"[<>*{}$]", script) is None:
            if not repo.exists(script, base):
                found.append(("script-missing", script))
            else:
                path = os.path.join(base if os.path.exists(os.path.join(base, script)) else repo.root, script)
                if os.path.isdir(path):  # `python pkg` runs pkg/__main__.py; any other directory has no flags to read
                    path = os.path.join(path, "__main__.py")
                text = open(path, encoding="utf-8", errors="replace").read() if os.path.isfile(path) else None
                for flag in [a.split("=")[0] for a in args if text is not None and re.match(r"^--[\w-]+", a)]:
                    if flag not in text:
                        found.append(("flag-unknown", "%s %s" % (script, flag)))
        elif exe in ("npm", "pnpm", "yarn", "bun") and args:
            name = args[1] if args[0] == "run" and len(args) > 1 else None if args[0] in (
                "install", "i", "add", "ci", "init", "create", "exec", "dlx", "x", "publish", "test", "start") else args[0]
            if args[0] in ("test", "start") and args[0] not in repo.scripts() and repo.scripts():
                found.append(("package-script-missing", "%s %s" % (exe, args[0])))
            elif name and repo.scripts() is not None and name not in repo.scripts() and os.path.exists(
                    os.path.join(repo.root, "package.json")):
                found.append(("package-script-missing", "%s run %s" % (exe, name)))
        elif exe == "make" and args and not args[0].startswith("-") and os.path.exists(os.path.join(repo.root, "Makefile")):
            if args[0] not in repo.targets():
                found.append(("make-target-missing", "make " + args[0]))
        elif not script and shutil.which(exe) is None and re.match(r"^[\w.-]+$", exe):
            found.append(("not-installed", exe))
    return found


def check_file(path, repo, keep):
    text = open(path, encoding="utf-8", errors="replace").read()
    base = os.path.dirname(os.path.abspath(path))
    findings = []

    def add(kind, line, claim):
        findings.append({"line": line, "kind": kind, "tier": TIERS[kind], "claim": claim,
                         "kept": keep.get((kind, claim))})

    fenced, prose = blocks(text)
    for lang, start, lines in fenced:
        if lang in SHELL_LANGS:
            for offset, cmd in commands(lines):
                for kind, claim in check_command(cmd, repo, base):
                    add(kind, start + offset, claim)
                for name in re.findall(r"\bexport\s+([A-Z][A-Z0-9_]+)=", cmd):
                    if ENV.match(name) and name not in WELL_KNOWN_ENV and not repo.reads(name):
                        add("env-unread", start + offset, name)
    for n, line in prose:
        for target in re.findall(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", line):
            if re.match(r"^[a-z][\w+.-]*:", target) or target.startswith("//"):
                continue
            file_part, _, anchor = target.partition("#")
            dest = os.path.normpath(os.path.join(base, file_part)) if file_part else os.path.abspath(path)
            if file_part and not os.path.exists(dest):
                add("link-missing", n, target)
            elif anchor and dest.endswith(".md") and anchor.lower() not in anchors(dest):
                add("anchor-missing", n, target)
        for span in re.findall(r"`([^`\n]+)`", line):
            span = span.strip().rstrip(".,:;")
            if ENV.match(span) and span not in WELL_KNOWN_ENV:
                if not repo.reads(span):
                    add("env-unread", n, span)
            elif PATHLIKE.match(span) and not PLACEHOLDER.search(span) and span.lower() != "n/a" \
                    and not span.startswith(("http", "-", "~", "/")) and not repo.exists(span, base):
                add("path-missing", n, span)
    seen, unique = set(), []
    for f in findings:
        key = (f["line"], f["kind"], f["claim"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return {"file": path, "findings": unique}


def load_keep(path):
    keep = {}
    if path:
        for line in open(path, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and not line.startswith("#"):
                keep[(parts[0], parts[1])] = parts[2]
    return keep


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+")
    p.add_argument("--root", help="repository root (default: the git top level of the current folder)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--keep")
    a = p.parse_args()
    root = a.root
    if not root:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        root = out.stdout.strip() if out.returncode == 0 else os.getcwd()
    repo, keep = Repo(os.path.abspath(root)), load_keep(a.keep)
    results = [check_file(f, repo, keep) for f in a.files]
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            for f in r["findings"]:
                print("%s:%d  %s %-22s %s%s" % (r["file"], f["line"], f["tier"], f["kind"], f["claim"],
                                               "  [kept: %s]" % f["kept"] if f["kept"] else ""))
    open_ = any(not f["kept"] and f["tier"] in ("S", "M") for r in results for f in r["findings"])
    return 1 if open_ else 0


if __name__ == "__main__":
    sys.exit(main())
