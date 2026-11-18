"""Tests for skills/mutation-check/scripts/mutate.py. Run: python -m unittest discover -s tests"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
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

    def test_lists_compound_assignment_unary_minus_and_conditional_expression(self):
        with open(os.path.join(self.dir, "more.py"), "w", encoding="utf-8") as f:
            f.write("def f(t, x, c):\n    t += x\n    t -= -x\n    return t if c else x\n")
        out = run(self.dir, "list", "more.py", "--json")
        changes = {(m["line"], m["change"]) for m in json.loads(out.stdout)}
        self.assertTrue({(2, "+= -> -="), (3, "-= -> +="), (3, "unary - removed"),
                         (4, "conditional expression negated")} <= changes, changes)

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
        self.assertEqual(out.returncode, 2)
        self.assertIn("uncommitted", out.stderr)

    def test_a_missing_path_a_directory_or_a_non_utf8_file_is_refused_in_one_line(self):
        os.makedirs(os.path.join(self.dir, "pkg"))
        with open(os.path.join(self.dir, "latin.py"), "wb") as f:
            f.write("# caffè\ndef f(x):\n    return x + 1\n".encode("cp1252"))
        git(self.dir, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.dir, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "latin")
        cases = [("gone.py", "no such file"), (os.path.join("nowhere", "gone.py"), "no such file"),
                 ("pkg", "a directory"), ("latin.py", "not UTF-8")]
        for path, reason in cases:
            for args in (("list", path), ("run", path, "--test", "echo ok")):
                with self.subTest(args=args):
                    out = run(self.dir, *args)
                    self.assertEqual(out.returncode, 2)
                    self.assertNotIn("Traceback", out.stderr)
                    self.assertEqual(len(out.stderr.strip().splitlines()), 1, out.stderr)
                    self.assertIn(path, out.stderr)
                    self.assertIn(reason, out.stderr)
        out = run(self.dir, "restore", os.path.join("nowhere", "gone.py"))
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("Traceback", out.stderr)

    def test_red_baseline_has_its_own_exit_code(self):
        # 1 means "survivors found"; tests that fail before any mutant are a different answer
        out = run(self.dir, "run", "calc.py", "--test", '"%s" -c "raise SystemExit(1)"' % sys.executable)
        self.assertEqual(out.returncode, 3)
        self.assertIn("do not pass on the original file", out.stderr)
        with open(os.path.join(self.dir, "calc.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), CODE)

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


class LineEndings(unittest.TestCase):
    def test_crlf_file_is_restored_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "calc.py")
            crlf = CODE.replace("\n", "\r\n").encode("utf-8")
            with open(path, "wb") as f:
                f.write(crlf)
            git(d, "init", "-q")
            git(d, "config", "core.autocrlf", "false")
            git(d, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
            git(d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
            out = run(d, "run", "calc.py", "--json", "--max", "3", "--test", '"%s" -c "import calc"' % sys.executable)
            self.assertIn(out.returncode, (0, 1), out.stderr)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), crlf)


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

    def test_function_scope_is_refused_rather_than_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.ts")
            with open(path, "w", encoding="utf-8") as f:
                f.write("function f(a) { return a < 1; }\nfunction g(b) { return b > 2; }\n")
            out = run(d, "list", path, "--function", "g", "--json")
        self.assertEqual(out.returncode, 2)
        self.assertIn("--lines", out.stderr)
        self.assertEqual(out.stdout, "")

    def test_compound_assignment(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.js")
            with open(path, "w", encoding="utf-8") as f:
                f.write("let t = 0;\nt += 2;\nt -= 1;\n")
            out = run(d, "list", path, "--json")
        changes = {(m["line"], m["change"]) for m in json.loads(out.stdout)}
        self.assertTrue({(2, "+= -> -="), (3, "-= -> +=")} <= changes, changes)


LOOP = '''def countdown(n):
    while n > 0:
        n = n - 1
    return n
'''
# appends its own pid, so the test can check that no test process outlives the run
LOOP_TEST = '''import os
with open("pids.txt", "a") as f:
    f.write("%d\\n" % os.getpid())
from loop import countdown
assert countdown(3) == 0
'''


def alive(pid):
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def kill(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


class Hanging(unittest.TestCase):
    """A mutant that loops forever: line 3, `n - 1 -> n + 1`, is M1 of `--lines 3`."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        for name, text in (("loop.py", LOOP), ("check.py", LOOP_TEST)):
            with open(os.path.join(self.dir, name), "w", encoding="utf-8") as f:
                f.write(text)
        with open(os.path.join(self.dir, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("pids.txt\n__pycache__/\n")
        git(self.dir, "init", "-q")
        git(self.dir, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git(self.dir, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        self.test = '"%s" check.py' % sys.executable

    def pids(self):
        try:
            with open(os.path.join(self.dir, "pids.txt"), encoding="utf-8") as f:
                return [int(x) for x in f.read().split()]
        except FileNotFoundError:
            return []

    def tearDown(self):
        for pid in self.pids():
            kill(pid)
        shutil.rmtree(self.dir, ignore_errors=True)

    def loop_source(self):
        with open(os.path.join(self.dir, "loop.py"), encoding="utf-8") as f:
            return f.read()

    def test_timeout_kills_the_whole_test_process_tree(self):
        # the shell runs the tests as its child: killing only the shell left them running with the
        # output pipes open, and the run waited for them forever
        try:
            out = subprocess.run([sys.executable, MUTATE, "run", "loop.py", "--lines", "3", "--timeout", "4",
                                  "--json", "--test", self.test], cwd=self.dir, capture_output=True, text=True,
                                 encoding="utf-8", timeout=90)
        except subprocess.TimeoutExpired:
            self.fail("the run hung on a mutant that loops forever")
        self.assertIn(out.returncode, (0, 1), out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual({r["change"]: r["status"] for r in data["results"]},
                         {"- -> +": "timeout", "1 -> 2": "killed"})
        self.assertEqual(self.loop_source(), LOOP)
        self.assertEqual([p for p in self.pids() if alive(p)], [])

    def killed_mid_run(self):
        """Start a run, wait until the hanging mutant is in the file, then kill the script with no
        chance to clean up (a closed console, taskkill /F, SIGKILL)."""
        proc = subprocess.Popen([sys.executable, MUTATE, "run", "loop.py", "--lines", "3", "--timeout", "600",
                                 "--test", self.test], cwd=self.dir, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        deadline = time.time() + 60
        while self.loop_source() == LOOP and time.time() < deadline:
            time.sleep(0.1)
        time.sleep(0.5)
        proc.kill()
        proc.wait()
        self.assertNotEqual(self.loop_source(), LOOP, "precondition: the mutant is left in the file")

    def test_next_run_restores_a_mutant_left_by_a_hard_kill(self):
        self.killed_mid_run()
        out = run(self.dir, "run", "loop.py", "--lines", "4", "--json", "--test", self.test)
        self.assertIn(out.returncode, (0, 1), out.stderr)
        self.assertIn("restored", out.stderr)
        self.assertEqual(self.loop_source(), LOOP)
        self.assertEqual(json.loads(out.stdout)["mutants"], 1)

    def test_restore_command_puts_the_original_back(self):
        self.killed_mid_run()
        out = run(self.dir, "restore", "loop.py")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.loop_source(), LOOP)
        self.assertEqual(run(self.dir, "restore", "loop.py").returncode, 0)  # nothing left: still fine

    def test_restore_leaves_a_file_edited_after_the_crash(self):
        self.killed_mid_run()
        with open(os.path.join(self.dir, "loop.py"), "w", encoding="utf-8") as f:
            f.write("# rewritten by hand\n")
        out = run(self.dir, "restore", "loop.py")
        self.assertEqual(out.returncode, 2)
        self.assertIn("changed since", out.stderr)
        self.assertEqual(self.loop_source(), "# rewritten by hand\n")

    def test_termination_signal_restores_the_file_and_stops_the_tests(self):
        # Windows: Ctrl+Break (a closed console arrives as the same SIGBREAK); elsewhere: SIGTERM
        group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {}
        proc = subprocess.Popen([sys.executable, MUTATE, "run", "loop.py", "--lines", "3", "--timeout", "600",
                                 "--test", self.test], cwd=self.dir, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, **group)
        deadline = time.time() + 60
        while self.loop_source() == LOOP and time.time() < deadline:
            time.sleep(0.1)
        time.sleep(0.5)
        try:
            if os.name == "nt":
                os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            code = proc.wait(timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            proc.kill()
            raise
        self.assertEqual(code, 128 + (signal.SIGBREAK if os.name == "nt" else signal.SIGTERM))
        self.assertEqual(self.loop_source(), LOOP)
        self.assertEqual([p for p in self.pids() if alive(p)], [])


if __name__ == "__main__":
    unittest.main()
