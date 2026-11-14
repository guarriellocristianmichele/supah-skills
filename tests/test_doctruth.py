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
npm run build
npm run lint
make test
make release
export APP_TOKEN=abc
export LEGACY_MODE=1
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
        self.assertIn(("package-script-missing", "npm run lint"), self.found)
        self.assertNotIn(("package-script-missing", "npm run build"), self.found)
        self.assertIn(("make-target-missing", "make release"), self.found)
        self.assertNotIn(("make-target-missing", "make test"), self.found)

    def test_env_vars(self):
        self.assertIn(("env-unread", "LEGACY_MODE"), self.found)
        self.assertIn(("env-unread", "OLD_SECRET"), self.found)
        self.assertNotIn(("env-unread", "APP_TOKEN"), self.found)

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


if __name__ == "__main__":
    unittest.main()
