"""Tests for skills/mutation-check/scripts/mutate.py. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUTATE = os.path.join(ROOT, "skills", "mutation-check", "scripts", "mutate.py")

CODE = '''def grade(score):
    if score >= 90:
        return "A"
    if score >= 50:
        return "pass"
    return "fail"
'''
REAL = '''import unittest
from calc import grade

class T(unittest.TestCase):
    def test_grade(self):
        self.assertEqual(grade(90), "A")
        self.assertEqual(grade(89), "pass")
        self.assertEqual(grade(50), "pass")
        self.assertEqual(grade(49), "fail")
'''
TAUTOLOGICAL = '''import unittest
from unittest import mock
import calc

class T(unittest.TestCase):
    def test_grade(self):
        with mock.patch.object(calc, "grade", return_value="A"):
            self.assertEqual(calc.grade(99), "A")
'''


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def run(cwd, *args):
    return subprocess.run([sys.executable, MUTATE, *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", timeout=300)


class Project(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        for name, text in (("calc.py", CODE), ("test_real.py", REAL), ("test_fake.py", TAUTOLOGICAL)):
            with open(os.path.join(self.dir, name), "w", encoding="utf-8") as f:
                f.write(text)
        git(self.dir, "init", "-q")
        git(self.dir, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.dir, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def suite(self, test):
        out = run(self.dir, "run", "calc.py", "--json", "--test",
                  '"%s" -m unittest %s' % (sys.executable, test))
        self.assertIn(out.returncode, (0, 1), out.stderr)
        return json.loads(out.stdout), out.returncode

    def test_lists_python_mutants(self):
        out = run(self.dir, "list", "calc.py", "--json")
        changes = {m["change"] for m in json.loads(out.stdout)}
        self.assertTrue({">= -> >", "90 -> 91", "if condition negated", "return value -> None"} <= changes)

    def test_real_tests_kill_every_mutant(self):
        data, code = self.suite("test_real")
        self.assertEqual((code, data["survived"]), (0, []))
        self.assertEqual(data["score"], 1.0)

    def test_tautological_tests_kill_nothing(self):
        data, code = self.suite("test_fake")
        self.assertEqual(code, 1)
        self.assertEqual(data["killed"], 0)
        self.assertEqual(len(data["survived"]), data["mutants"])

    def test_file_is_restored(self):
        self.suite("test_fake")
        with open(os.path.join(self.dir, "calc.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), CODE)

    def test_refuses_uncommitted_file(self):
        with open(os.path.join(self.dir, "calc.py"), "a", encoding="utf-8") as f:
            f.write("# edited\n")
        out = run(self.dir, "run", "calc.py", "--test", "echo ok")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("uncommitted", out.stderr)

    def test_function_scope(self):
        with open(os.path.join(self.dir, "calc.py"), "a", encoding="utf-8") as f:
            f.write("\ndef other(a):\n    return a + 1\n")
        out = run(self.dir, "list", "calc.py", "--function", "other", "--json")
        self.assertTrue(all(m["line"] >= 8 for m in json.loads(out.stdout)))


PRICE = '''def discount(total, is_member):
    if total >= 100:
        rate = 0.1
    else:
        rate = 0.0
    if is_member:
        rate += 0.05
    return round(total * (1 - rate), 2)
'''
PRICE_TEST = '''import unittest
from price import discount

class T(unittest.TestCase):
    def test_discount(self):
        self.assertEqual(discount(200, False), 180)
        self.assertEqual(discount(50, True), 47.5)
'''


class BytecodeCache(unittest.TestCase):
    """Same-size mutants written within one second must not run the previous mutant's cached .pyc."""

    def test_each_mutant_runs_its_own_code(self):
        with tempfile.TemporaryDirectory() as d:
            for name, text in (("price.py", PRICE), ("test_price.py", PRICE_TEST)):
                with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                    f.write(text)
            git(d, "init", "-q")
            git(d, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
            git(d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
            out = run(d, "run", "price.py", "--json", "--test", '"%s" -m unittest test_price' % sys.executable)
            data = json.loads(out.stdout)
            line8 = {r["change"] for r in data["results"] if r["line"] == 8 and r["status"] == "survived"}
            # only rounding to 3 places leaves 180 and 47.5 unchanged; * -> /, - -> + and 1 -> 2 change them
            self.assertEqual(line8, {"2 -> 3"})


class JavaScript(unittest.TestCase):
    def test_mutates_code_not_strings_or_comments(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.js")
            with open(path, "w", encoding="utf-8") as f:
                f.write('// a < b && c\nconst s = "x === y";\nif (a === b && c <= d) { return true; }\n'
                        "const f = (x) => x;\n")
            out = run(d, "list", path, "--json")
        found = json.loads(out.stdout)
        self.assertEqual({m["line"] for m in found}, {3})
        self.assertEqual({m["change"] for m in found}, {"=== -> !==", "&& -> ||", "<= -> <", "true -> false"})


if __name__ == "__main__":
    unittest.main()
