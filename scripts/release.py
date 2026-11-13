#!/usr/bin/env python3
"""Release helper for supah-skills. Stdlib only.

  python scripts/release.py --check     run every repository check (CI runs this)
  python scripts/release.py --sync      copy the prose scanner into plugins/slop-guard/scanner
  python scripts/release.py 0.3.0       set the version everywhere, sync, then run the checks

Checks: every skill folder is listed in plugin.json and has its own marketplace entry;
every plugins/<name> folder has one too; all versions agree; the slop-guard scanner copy
equals skills/ai-slop-prose/scripts; the test suite passes; every README passes the prose
scanner (exceptions in docs/readme-keep.tsv); `claude plugin validate` (errors only) when
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
SCANNER = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts")
SCAN = os.path.join(SCANNER, "scan.py")
# installed plugins cannot reach files outside their folder, so slop-guard carries a copy
SCANNER_COPY = os.path.join(ROOT, "plugins", "slop-guard", "scanner")
KEEP = os.path.join(ROOT, "docs", "readme-keep.tsv")


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
    shutil.rmtree(SCANNER_COPY, ignore_errors=True)
    for rel in scanner_files(SCANNER):
        os.makedirs(os.path.dirname(os.path.join(SCANNER_COPY, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(SCANNER, rel), os.path.join(SCANNER_COPY, rel))
    print(f"scanner copied to {os.path.relpath(SCANNER_COPY, ROOT)}")


def check_scanner_copy():
    files = scanner_files(SCANNER)
    if files != scanner_files(SCANNER_COPY) or any(
            not filecmp.cmp(os.path.join(SCANNER, f), os.path.join(SCANNER_COPY, f), shallow=False) for f in files):
        return ["plugins/slop-guard/scanner differs from skills/ai-slop-prose/scripts: run release.py --sync"]
    return []


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
    return errors + check_scanner_copy()


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
               [os.path.join(ROOT, "README.md")] + sorted(glob.glob(os.path.join(ROOT, "skills", "*", "README.md")))
               + sorted(glob.glob(os.path.join(ROOT, "plugins", "*", "README.md")))]
    ok &= run("readme sweep", [sys.executable, SCAN, "--no-learn", "--keep", KEEP, *readmes])
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
            print(f"\nNext: commit, then `git tag v{args[0]} && git push --follow-tags`.")
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
