#!/usr/bin/env python3
"""Release helper for supah-skills. Stdlib only.

  python scripts/release.py --check     run every repository check (CI runs this)
  python scripts/release.py 0.3.0       set the version everywhere, then run the checks

Checks: every skill folder is listed in plugin.json and has its own marketplace entry;
all versions agree; the test suite passes; every README passes the prose scanner
(exceptions in docs/readme-keep.tsv); `claude plugin validate` (errors only) when the
claude CLI is installed.
"""
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
KEEP = os.path.join(ROOT, "docs", "readme-keep.tsv")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def set_version(version):
    plugin, market = load(PLUGIN), load(MARKET)
    plugin["version"] = version
    for entry in market["plugins"]:
        if "version" in entry:
            entry["version"] = version
    save(PLUGIN, plugin)
    save(MARKET, market)
    print(f"version set to {version} in plugin.json and every versioned marketplace entry")


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
    return errors


def run(label, cmd):
    print(f"\n== {label}: {' '.join(cmd)}")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    tail = (result.stdout + result.stderr).strip().splitlines()[-6:]
    print("\n".join(tail))
    return result.returncode == 0


def checks():
    ok = True
    errors = check_manifests()
    print("== manifests: " + ("ok" if not errors else "\n  " + "\n  ".join(errors)))
    ok &= not errors
    ok &= run("tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    readmes = [os.path.relpath(p, ROOT) for p in
               [os.path.join(ROOT, "README.md")] + sorted(glob.glob(os.path.join(ROOT, "skills", "*", "README.md")))]
    ok &= run("readme sweep", [sys.executable, SCAN, "--keep", KEEP, *readmes])
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
    if len(args) == 1 and re.fullmatch(r"\d+\.\d+\.\d+", args[0]):
        set_version(args[0])
        code = checks()
        if code == 0:
            print(f"\nNext: commit, then `git tag v{args[0]} && git push --follow-tags`.")
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
