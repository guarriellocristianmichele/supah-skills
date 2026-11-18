"""A git planted in the scanned repository never runs. On Windows, CreateProcess and shutil.which (3.10)
look in the current folder before PATH, so every script that runs git resolves it on PATH's absolute
entries only. Run: python -m unittest discover -s tests"""
import glob
import importlib.util
import os
import re
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = {name: os.path.join(ROOT, "skills", skill, "scripts", name + ".py")
           for skill, name in (("mutation-check", "mutate"), ("doc-truth", "doctruth"),
                               ("ai-slop-design", "designscan"))}
EXE = "git.exe" if os.name == "nt" else "git"


def load(name):
    spec = importlib.util.spec_from_file_location("planting_" + name, SCRIPTS[name])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_git(folder):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, EXE)
    with open(path, "w") as f:
        f.write("#!/bin/sh\n")
    os.chmod(path, 0o755)
    return path


class FindExe(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.planted = os.path.join(self.dir, "repo")
        fake_git(self.planted)
        fake_git(os.path.join(self.planted, "bin"))
        self.good = fake_git(os.path.join(self.dir, "tools"))
        old = os.getcwd()
        os.chdir(self.planted)
        self.addCleanup(os.chdir, old)

    def path(self, *extra):
        # the current folder, an empty entry, a relative entry and the current folder by its full path
        return os.pathsep.join([".", "", "bin", self.planted, *extra])

    def test_git_comes_from_an_absolute_path_entry_never_the_current_folder(self):
        for name in SCRIPTS:
            with self.subTest(script=name):
                find_exe = load(name).find_exe
                with mock.patch.dict(os.environ, {"PATH": self.path(os.path.dirname(self.good)),
                                                  "PATHEXT": ".COM;.EXE"}):
                    self.assertEqual(os.path.normcase(find_exe("git")), os.path.normcase(self.good))
                with mock.patch.dict(os.environ, {"PATH": self.path(), "PATHEXT": ".COM;.EXE"}):
                    with self.assertRaises(FileNotFoundError):
                        find_exe("git")


class EveryCall(unittest.TestCase):
    def test_no_script_runs_git_or_taskkill_by_bare_name(self):
        for path in glob.glob(os.path.join(ROOT, "skills", "*", "scripts", "*.py")):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            with self.subTest(script=os.path.relpath(path, ROOT)):
                self.assertEqual(re.findall(r"""\[\s*["'](?:git|taskkill)["']""", text), [])
        with open(SCRIPTS["mutate"], encoding="utf-8") as f:
            self.assertRegex(f.read(), r"""["']System32["'],\s*["']taskkill\.exe["']""")


if __name__ == "__main__":
    unittest.main()
