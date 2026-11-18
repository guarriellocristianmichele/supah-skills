#!/usr/bin/env python3
"""Release helper for supah-skills. Stdlib only.

  python scripts/release.py --check     run every repository check (CI runs this)
  python scripts/release.py --sync      copy learn.py next to the design and code scanners, and the
                                        prose and code scanners into plugins/slop-guard
  python scripts/release.py 0.3.0       set the version everywhere, sync, then run the checks

Checks: every skill folder is listed in plugin.json and has its own marketplace entry;
every plugins/<name> folder has one too; all versions agree; the slop-guard scanner copies
equal their sources; the test suite passes; every README passes the prose
scanner (exceptions in docs/readme-keep.tsv); READMEs, AGENTS.md and ADRs pass doc-truth; `claude plugin validate` (errors only) when
the claude CLI is installed.
"""
import filecmp
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, ".claude-plugin", "plugin.json")
MARKET = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
SCAN = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts", "scan.py")
# installed plugins cannot reach files outside their folder, so slop-guard carries copies
COPIES = [
    ("skills/ai-slop-prose/scripts", "plugins/slop-guard/scanner"),
    ("skills/ai-slop-audit/scripts", "plugins/slop-guard/codescan"),
]
# one verdict-learning module for the three scanners (ADR 0018); per-skill installs need their own copy
LEARN = "skills/ai-slop-prose/scripts/learn.py"
LEARN_COPIES = ["skills/ai-slop-design/scripts/learn.py", "skills/ai-slop-audit/scripts/learn.py"]
KEEP = os.path.join(ROOT, "docs", "readme-keep.tsv")
LESSONS = "**Lessons.** At the start of a run, read this skill's section of `.supah/LESSONS.md` at the repo root when it exists, and follow its rules. Write a lesson only when the user corrects or undoes what this skill did, or when a run ends failed or partial for a cause the skill could have avoided: one entry under `## <skill>` (on first use create the file and add `.supah/` to `.git/info/exclude`) with the date, the trigger (`correction` or `failure`), the evidence (the user's words, the commit or the output), the step it changes, and the rule in one positive line. Keep at most 15 per skill: a lesson that contradicts an older one replaces it, and past 15 the oldest goes. A lesson about this skill's own instructions, true in any project, changes nothing here: draft an issue for guarriellocristianmichele/supah-skills (title, the SKILL.md step, what happened, no code or text from the project) and ask with options: open it with `gh issue create`, save it in `.supah/issue-drafts/`, or drop it. The report names the lessons added, replaced and drafted."
NEXT_STEP = "**Next step.** End every run with the next step of the workflow, worked out from what this run left (the ledger's statuses, failed or blocked units, a question still open, the user's goal): the exact command and its reason in one line, and when two fit, both, the recommended one first; a skill that keeps a `STATUS.md` writes the same command as its next action. Put `/clear` before it (on another agent, a new session) when this run left its state on disk for that command to read; keep the session when the next step answers this run in conversation. When another skill called this one, hand the result back to it instead. When nothing is left, say the workflow is done."
# ADR 0013: every SKILL.md carries this paragraph word for word
ASK_WITH_OPTIONS = ("**Ask with options.** Settle a doubt by looking first: the repo, its docs, and a web search when "
                    "the answer is a fact about the world. What only the user can decide, ask as one question with 2 "
                    "to 4 ready answers, the recommended one first and each saying what it changes; Claude Code's "
                    "`AskUserQuestion` shows them on screen, other agents number them in the reply.")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def plugin_dirs():
    return sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                  for p in glob.glob(os.path.join(ROOT, "plugins", "*", ".claude-plugin", "plugin.json")))


def manifest(name):
    return os.path.join(ROOT, "plugins", name, ".claude-plugin", "plugin.json")


def set_version(version):
    market = load(MARKET)
    for path in [PLUGIN] + [manifest(name) for name in plugin_dirs()]:
        data = load(path)
        data["version"] = version
        save(path, data)
    for entry in market["plugins"]:
        if "version" in entry:
            entry["version"] = version
    save(MARKET, market)
    print(f"version set to {version} in every plugin.json and every versioned marketplace entry")


def scanner_files(top):
    found = []
    for folder, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        found += [os.path.relpath(os.path.join(folder, f), top) for f in files if not f.endswith(".pyc")]
    return sorted(found)


def sync_scanner():
    for dst in LEARN_COPIES:  # before the folder copies, so slop-guard's codescan carries it too
        shutil.copyfile(os.path.join(ROOT, LEARN), os.path.join(ROOT, dst))
        print(f"copied {LEARN} to {dst}")
    for src, dst in COPIES:
        src, dst = os.path.join(ROOT, src), os.path.join(ROOT, dst)
        shutil.rmtree(dst, ignore_errors=True)
        for rel in scanner_files(src):
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.copyfile(os.path.join(src, rel), os.path.join(dst, rel))
        print(f"copied {os.path.relpath(src, ROOT)} to {os.path.relpath(dst, ROOT)}")


def check_scanner_copy():
    errors = [f"{dst} differs from {LEARN}: run release.py --sync" for dst in LEARN_COPIES
              if not os.path.exists(os.path.join(ROOT, dst))
              or not filecmp.cmp(os.path.join(ROOT, LEARN), os.path.join(ROOT, dst), shallow=False)]
    for src_rel, dst_rel in COPIES:
        src, dst = os.path.join(ROOT, src_rel), os.path.join(ROOT, dst_rel)
        files = scanner_files(src)
        if files != scanner_files(dst) or any(
                not filecmp.cmp(os.path.join(src, f), os.path.join(dst, f), shallow=False) for f in files):
            errors.append(f"{dst_rel} differs from {src_rel}: run release.py --sync")
    return errors


def check_manifests():
    errors = []
    plugin, market = load(PLUGIN), load(MARKET)
    skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
    listed = sorted(os.path.basename(p.rstrip("/")) for p in plugin.get("skills", []))
    if skills != listed:
        errors.append(f"plugin.json skills {listed} differ from skill folders {skills}")
    entries = {e["name"]: e for e in market["plugins"]}
    for name in skills:
        entry = entries.get(name)
        if not entry:
            errors.append(f"marketplace.json has no entry for {name}")
        elif entry.get("source") != f"./skills/{name}":
            errors.append(f"marketplace entry {name} has source {entry.get('source')}")
        elif entry.get("version") != plugin["version"]:
            errors.append(f"marketplace entry {name} is at {entry.get('version')}, plugin.json at {plugin['version']}")
    if plugin["name"] not in entries:
        errors.append(f"marketplace.json has no entry for the bundle {plugin['name']}")
    for name in plugin_dirs():
        entry, version = entries.get(name), load(manifest(name)).get("version")
        if not entry:
            errors.append(f"marketplace.json has no entry for plugins/{name}")
        elif entry.get("source") != f"./plugins/{name}":
            errors.append(f"marketplace entry {name} has source {entry.get('source')}")
        elif not entry.get("version") == version == plugin["version"]:
            errors.append(f"plugin {name} is at {version} (entry {entry.get('version')}), plugin.json at {plugin['version']}")
    bundle = entries.get(plugin["name"], {}).get("description", "")
    router = open(os.path.join(ROOT, "skills", "supah-help", "SKILL.md"), encoding="utf-8").read()
    for name in skills:
        if name not in bundle:
            errors.append(f"the {plugin['name']} marketplace description does not name {name}")
        if name != "supah-help" and name not in router:
            errors.append(f"supah-help does not route to {name}")
        with open(os.path.join(ROOT, "skills", name, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
            if ASK_WITH_OPTIONS not in text:
                errors.append(f"skills/{name}/SKILL.md lacks the Ask with options paragraph (ADR 0013)")
            if NEXT_STEP not in text:
                errors.append(f"skills/{name}/SKILL.md lacks the Next step paragraph (ADR 0017)")
            if LESSONS not in text:
                errors.append(f"skills/{name}/SKILL.md lacks the Lessons paragraph (ADR 0019)")
    return errors + check_scanner_copy()


def run(label, cmd):
    print(f"\n== {label}: {' '.join(cmd)}")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    tail = (result.stdout + result.stderr).strip().splitlines()[-6:]
    print("\n".join(tail))
    return result.returncode == 0


def readme_sweep(readmes):
    """The prose scanner over the READMEs: exceptions come from docs/readme-keep.tsv only, never from a
    .slop-prose-keep.tsv at the repository root (AGENTS.md)."""
    return [sys.executable, SCAN, "--no-learn", "--no-repo-keep", "--keep", KEEP, *readmes]


def checks():
    ok = True
    errors = check_manifests()
    print("== manifests: " + ("ok" if not errors else "\n  " + "\n  ".join(errors)))
    ok &= not errors
    ok &= run("tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    readmes = [os.path.relpath(p, ROOT) for p in
               [os.path.join(ROOT, "README.md")] + sorted(glob.glob(os.path.join(ROOT, "skills", "*", "README.md")))
               + sorted(glob.glob(os.path.join(ROOT, "plugins", "*", "README.md")))]
    ok &= run("readme sweep", readme_sweep(readmes))
    docs = readmes + ["AGENTS.md", "GLOSSARY.md"] + sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "docs", "adr", "*.md")))
    ok &= run("doc truth", [sys.executable, os.path.join(ROOT, "skills", "doc-truth", "scripts", "doctruth.py"), "--root", ROOT, *docs])
    if shutil.which("claude"):
        ok &= run("plugin validate", ["claude", "plugin", "validate", "."])  # not --strict: the dev-only CLAUDE.md at the root is a known warning
    else:
        print("\n== plugin validate: skipped (claude CLI not installed)")
    print("\nALL CHECKS PASSED" if ok else "\nCHECKS FAILED")
    return 0 if ok else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if args == ["--check"]:
        return checks()
    if args == ["--sync"]:
        sync_scanner()
        return 0
    if len(args) == 1 and re.fullmatch(r"\d+\.\d+\.\d+", args[0]):
        set_version(args[0])
        sync_scanner()
        code = checks()
        if code == 0:
            # Tags here are lightweight, and --follow-tags pushes only annotated ones: push the tag by name.
            print(f"\nNext: commit, then `git tag v{args[0]} && git push origin HEAD v{args[0]}`.")
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
