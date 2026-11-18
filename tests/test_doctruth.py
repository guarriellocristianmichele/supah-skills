"""Tests for skills/doc-truth/scripts/doctruth.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCTRUTH = os.path.join(ROOT, "skills", "doc-truth", "scripts", "doctruth.py")

README = """# Demo

## Getting started

See [the guide](docs/guide.md), [setup](docs/guide.md#setup), [gone](docs/missing.md)
and [a bad anchor](docs/guide.md#nowhere), or [this section](#getting-started).

```sh
python scripts/build.py --out dist
python scripts/build.py --verbose
python scripts/deploy.py
python scripts
python tools --out x --quiet
npm run build
npm run lint
make test
make release
export APP_TOKEN=abc
export LEGACY_MODE=1
cd docs && set -e
source .venv/bin/activate
```

Set `APP_TOKEN` or `OLD_SECRET`. The config lives in `config/app.toml`, the cache in `cache/state.json`.
Read the [site](https://example.com) and `docs/adr/NNNN-slug.md`.
"""


def put(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Check(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        put(cls.root, "README.md", README)
        put(cls.root, "docs/guide.md", "# Guide\n\n## Setup\n")
        put(cls.root, "scripts/build.py", 'import argparse, os\np = argparse.ArgumentParser()\n'
                                          'p.add_argument("--out")\nTOKEN = os.environ["APP_TOKEN"]\n')
        put(cls.root, "tools/__main__.py", 'import argparse\nargparse.ArgumentParser().add_argument("--out")\n')
        put(cls.root, "package.json", json.dumps({"scripts": {"build": "tsc"}}))
        put(cls.root, "Makefile", "test:\n\tpytest\n")
        put(cls.root, "config/app.toml", "x = 1\n")
        out = subprocess.run([sys.executable, DOCTRUTH, "--root", cls.root, "--json",
                              os.path.join(cls.root, "README.md")], capture_output=True, text=True, encoding="utf-8")
        cls.code = out.returncode
        cls.found = {(f["kind"], f["claim"]) for f in json.loads(out.stdout)[0]["findings"]}

    def test_exit_code(self):
        self.assertEqual(self.code, 1)

    def test_links_and_anchors(self):
        self.assertIn(("link-missing", "docs/missing.md"), self.found)
        self.assertIn(("anchor-missing", "docs/guide.md#nowhere"), self.found)
        for ok in ("docs/guide.md", "docs/guide.md#setup", "#getting-started", "https://example.com"):
            self.assertNotIn(ok, {c for _, c in self.found})

    def test_commands(self):
        self.assertIn(("flag-unknown", "scripts/build.py --verbose"), self.found)
        self.assertNotIn(("flag-unknown", "scripts/build.py --out"), self.found)
        self.assertIn(("script-missing", "scripts/deploy.py"), self.found)
        self.assertNotIn(("script-missing", "scripts"), self.found)  # a directory, read without crashing
        self.assertIn(("flag-unknown", "tools --quiet"), self.found)  # flags read from tools/__main__.py
        self.assertNotIn(("flag-unknown", "tools --out"), self.found)
        self.assertIn(("package-script-missing", "npm run lint"), self.found)
        self.assertNotIn(("package-script-missing", "npm run build"), self.found)
        self.assertIn(("make-target-missing", "make release"), self.found)
        self.assertNotIn(("make-target-missing", "make test"), self.found)

    def test_env_vars(self):
        self.assertIn(("env-unread", "LEGACY_MODE"), self.found)
        self.assertIn(("env-unread", "OLD_SECRET"), self.found)
        self.assertNotIn(("env-unread", "APP_TOKEN"), self.found)

    def test_shell_builtins_are_not_commands(self):
        for builtin in ("export", "cd", "set", "source"):
            self.assertNotIn(("not-installed", builtin), self.found)

    def test_paths(self):
        self.assertIn(("path-missing", "cache/state.json"), self.found)
        self.assertNotIn(("path-missing", "config/app.toml"), self.found)
        self.assertNotIn(("path-missing", "docs/adr/NNNN-slug.md"), self.found)

    def test_keep_file_resolves(self):
        keep = os.path.join(self.root, "keep.tsv")
        with open(keep, "w", encoding="utf-8") as f:
            for kind, claim in sorted(self.found):
                f.write("%s\t%s\tliteral\n" % (kind, claim))
        out = subprocess.run([sys.executable, DOCTRUTH, "--root", self.root, "--keep", keep,
                              os.path.join(self.root, "README.md")], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)


class RepositoryKeepFile(unittest.TestCase):
    def test_claims_kept_in_the_repository_stay_kept_without_flags(self):
        root = tempfile.mkdtemp()
        put(root, "README.md", "# Demo\n\nSee [the log](logs/run.log).\n")
        put(root, ".doc-truth-keep.tsv", "# kind\tclaim\treason\nlink-missing\tlogs/run.log\tcreated by the program\n")
        out = subprocess.run([sys.executable, DOCTRUTH, "--root", root, "--json", os.path.join(root, "README.md")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stdout)
        [finding] = json.loads(out.stdout)[0]["findings"]
        self.assertEqual(finding["kept"], "created by the program")


class BadInput(unittest.TestCase):
    """A missing path, a directory or a file that is not UTF-8: one line on stderr, the other docs go on, exit 2."""

    def test_each_bad_path_is_one_line_and_the_rest_is_checked(self):
        root = tempfile.mkdtemp()
        put(root, "README.md", "# Demo\n\nSee [gone](docs/missing.md).\n")
        os.makedirs(os.path.join(root, "docs"))
        latin = os.path.join(root, "LATIN.md")
        with open(latin, "wb") as f:
            f.write("# Caffè\n".encode("cp1252"))
        missing, folder, good = os.path.join(root, "GONE.md"), os.path.join(root, "docs"), os.path.join(root, "README.md")
        out = subprocess.run([sys.executable, DOCTRUTH, "--root", root, "--json", missing, folder, latin, good],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("Traceback", out.stderr)
        lines = out.stderr.strip().splitlines()
        self.assertEqual(len(lines), 3, out.stderr)
        for line, path in zip(lines, (missing, folder, latin)):
            self.assertIn(path, line)
        self.assertIn("not UTF-8", lines[2])
        [result] = json.loads(out.stdout)
        self.assertEqual(result["file"], good)
        self.assertEqual([f["kind"] for f in result["findings"]], ["link-missing"])  # the readable doc is still checked


def doc(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class Docs(unittest.TestCase):
    def test_judging_points_at_the_history_command_that_finds_a_deleted_file(self):
        step = doc("skills", "doc-truth", "SKILL.md").split("3. **Judge each finding**", 1)[1].split("\n4. ", 1)[0]
        self.assertIn("git log --diff-filter=D -- <path>", step)

    def test_kept_claims_go_to_the_repository_keep_file(self):
        step = doc("skills", "doc-truth", "SKILL.md").split("3. **Judge each finding**", 1)[1].split("\n4. ", 1)[0]
        self.assertIn("`.doc-truth-keep.tsv` at the repository root", step)
        self.assertNotIn("scratchpad", step)
        english, italian = doc("skills", "doc-truth", "README.md").split("## Italiano", 1)
        self.assertIn(".doc-truth-keep.tsv", english)
        self.assertIn(".doc-truth-keep.tsv", italian)


if __name__ == "__main__":
    unittest.main()
