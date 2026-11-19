#!/usr/bin/env python3
"""Mutation testing with the project's own test command. Stdlib only.

  mutate.py list FILE [--lines A-B] [--function NAME]
      Print every mutant of FILE: id, line, what changes.
  mutate.py run FILE --test "CMD" [--lines A-B] [--function NAME] [--max N] [--timeout S] [--json]
      Run CMD once on the original (it must pass), then once per mutant, and report each mutant
      as killed (CMD failed), survived (CMD passed) or timeout (CMD and every process it started
      are killed). Exit 0: no mutant survived; 1: survivors; 2: refused (arguments, uncommitted
      file, FILE missing, a directory or not UTF-8: one line on stderr naming it); 3: CMD fails on
      the original file; 128 + signal number: interrupted, file restored. `list` refuses FILE the same way.
  mutate.py restore [PATH]
      Put back any file in PATH's repository that a killed run left mutated (`run` does this first).

Python files are mutated through ast (the mutant is the unparsed tree, so formatting and comments
differ but behaviour only changes where the mutant says). JavaScript and TypeScript are mutated by
replacing one operator or literal in code, never inside strings or comments; --function is Python only.

FILE is changed in place while CMD runs and restored after every mutant, on errors, on Ctrl+C, Ctrl+Break,
a closed console and SIGTERM. A backup in the repository's git folder covers a hard kill: the next `run`
or `restore` puts the original back. `run` refuses a file with uncommitted changes, so
`git checkout -- FILE` is always a way back.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time

PY = (".py",)
JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
            ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
            ast.In: ast.NotIn, ast.NotIn: ast.In}
BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
            ast.FloorDiv: ast.Mult, ast.Mod: ast.Mult}
SYMBOL = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
          ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in", ast.Add: "+", ast.Sub: "-",
          ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%", ast.And: "and", ast.Or: "or"}
JS_SWAP = [("===", "!=="), ("!==", "==="), ("+=", "-="), ("-=", "+="), ("<=", "<"), (">=", ">"),
           ("&&", "||"), ("||", "&&"), ("<", "<="), (">", ">="), ("true", "false"), ("false", "true")]


# ---------- Python ----------

def py_sites(tree, keep):
    """(path to node, description, mutate(node) -> replacement or None) for every mutable site."""
    sites = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", None)
        if line is None or not keep(line):
            continue
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if type(op) in CMP_SWAP:
                    new = CMP_SWAP[type(op)]
                    sites.append((node, line, "%s -> %s" % (SYMBOL[type(op)], SYMBOL[new]),
                                  lambda n, i=i, new=new: n.ops.__setitem__(i, new())))
        elif isinstance(node, ast.BinOp) and type(node.op) in BIN_SWAP:
            new = BIN_SWAP[type(node.op)]
            sites.append((node, line, "%s -> %s" % (SYMBOL[type(node.op)], SYMBOL[new]),
                          lambda n, new=new: setattr(n, "op", new())))
        elif isinstance(node, ast.AugAssign) and type(node.op) in BIN_SWAP:
            new = BIN_SWAP[type(node.op)]
            sites.append((node, line, "%s= -> %s=" % (SYMBOL[type(node.op)], SYMBOL[new]),
                          lambda n, new=new: setattr(n, "op", new())))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            sites.append((node, line, "unary - removed", lambda n: setattr(n, "op", ast.UAdd())))
        elif isinstance(node, ast.IfExp):
            sites.append((node, line, "conditional expression negated",
                          lambda n: setattr(n, "test", ast.UnaryOp(op=ast.Not(), operand=n.test))))
        elif isinstance(node, ast.BoolOp):
            new = ast.Or if isinstance(node.op, ast.And) else ast.And
            sites.append((node, line, "%s -> %s" % (SYMBOL[type(node.op)], SYMBOL[new]),
                          lambda n, new=new: setattr(n, "op", new())))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            sites.append((node, line, "%s -> %s" % (node.value, not node.value),
                          lambda n: setattr(n, "value", not n.value)))
        elif isinstance(node, ast.Constant) and type(node.value) is int:
            sites.append((node, line, "%d -> %d" % (node.value, node.value + 1),
                          lambda n: setattr(n, "value", n.value + 1)))
        elif isinstance(node, ast.If):
            sites.append((node, line, "if condition negated",
                          lambda n: setattr(n, "test", ast.UnaryOp(op=ast.Not(), operand=n.test))))
        elif isinstance(node, ast.Return) and node.value is not None and not (
                isinstance(node.value, ast.Constant) and node.value.value is None):
            sites.append((node, line, "return value -> None", lambda n: setattr(n, "value", ast.Constant(None))))
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            sites.append((node, line, "call removed", lambda n: setattr(n, "value", ast.Constant(None))))
    return sites


def py_mutants(source, keep):
    tree = ast.parse(source)
    count = len(py_sites(tree, keep))
    for k in range(count):
        clone = copy.deepcopy(tree)  # sites of a fresh tree line up with the original's, in walk order
        node, line, what, apply = py_sites(clone, keep)[k]
        apply(node)
        yield {"line": line, "change": what, "source": ast.unparse(ast.fix_missing_locations(clone)) + "\n"}


# ---------- JavaScript / TypeScript ----------

def js_code_spans(source):
    """(start, end) ranges of source outside strings, template literals and comments."""
    spans, i, start, n = [], 0, 0, len(source)
    while i < n:
        c, two = source[i], source[i:i + 2]
        if two in ("//", "/*") or c in "'\"`":
            spans.append((start, i))
            if two == "//":
                i = source.find("\n", i)
                i = n if i < 0 else i
            elif two == "/*":
                i = source.find("*/", i + 2)
                i = n if i < 0 else i + 2
            else:
                i += 1
                while i < n and source[i] != c:
                    i += 2 if source[i] == "\\" else 1
                i += 1
            start = i
        else:
            i += 1
    spans.append((start, n))
    return [(a, b) for a, b in spans if b > a]


def js_mutants(source, keep):
    taken = set()
    for a, b in js_code_spans(source):
        chunk = source[a:b]
        for old, new in JS_SWAP:
            pattern = r"\b%s\b" % old if old.isalpha() else re.escape(old)
            for m in re.finditer(pattern, chunk):
                pos = a + m.start()
                if any(t <= pos < t + 3 for t in taken):  # "<" inside "<=" or "===" was already mutated
                    continue
                if old in ("<", ">") and (source[pos + 1:pos + 2] in "=>" or source[pos - 1:pos] in "=<>-"):
                    continue  # part of <=, =>, ->, <<, or a generic / JSX bracket next to another symbol
                line = source.count("\n", 0, pos) + 1
                if not keep(line):
                    continue
                taken.add(pos)
                yield {"line": line, "change": "%s -> %s" % (old, new),
                       "source": source[:pos] + new + source[pos + len(old):]}


# ---------- driver ----------

def selector(lines, function, source, path):
    lo, hi = 1, 10 ** 9
    if lines:
        lo, _, hi = lines.partition("-")
        lo, hi = int(lo), int(hi or lo)
    if function and not path.endswith(PY):
        refuse("--function works on Python files only: for JavaScript and TypeScript, give the function's "
               "lines with --lines A-B")
    if function:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
                lo, hi = max(lo, node.lineno), min(hi, node.end_lineno)
                break
        else:
            refuse("no function %s in %s" % (function, path))
    return lambda line: lo <= line <= hi


def mutants(path, lines=None, function=None):
    with open(path, encoding="utf-8", newline="") as f:  # keep CRLF: restore() writes these exact characters back
        source = f.read()
    keep = selector(lines, function, source, path)
    if path.endswith(PY):
        found = list(py_mutants(source, keep))
    elif path.endswith(JS):
        found = list(js_mutants(source, keep))
    else:
        refuse("%s: not Python, JavaScript or TypeScript" % path)
    for i, m in enumerate(found, 1):
        m["id"] = "M%d" % i
    return source, found


def refuse(message, code=2):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:  # keep CRLF: restore writes these exact characters back
        return f.read()


def check_input(path):
    """Refuse, in one line naming it, a FILE that does not exist, is a directory or is not UTF-8."""
    if os.path.isdir(path):
        refuse("%s: a directory, not a file: give one Python, JavaScript or TypeScript file" % path)
    try:
        read(path)
    except FileNotFoundError:
        refuse("%s: no such file" % path)
    except UnicodeDecodeError as e:
        refuse("%s: not UTF-8 (byte 0x%02x at offset %d): mutants are written as UTF-8, so save it as UTF-8 "
               "and commit it first" % (path, e.object[e.start], e.start))
    except OSError as e:
        refuse("%s: cannot be read (%s)" % (path, e.strerror or e))


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def find_exe(name):
    """The full path of name on PATH, searching absolute entries only. On Windows, CreateProcess and
    shutil.which (Python 3.10) look in the current folder first, where a scanned repository could plant
    a git.exe; a relative entry, an empty one or the current folder itself is skipped for the same
    reason. FileNotFoundError when name is on no such entry."""
    here = os.path.normcase(os.path.abspath(os.getcwd()))
    exts = [""]
    if os.name == "nt":
        exts = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep) if e]
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        folder = folder.strip().strip('"')
        if not folder or not os.path.isabs(folder) or os.path.normcase(os.path.abspath(folder)) == here:
            continue
        for ext in exts:
            candidate = os.path.join(folder, name + ext)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    raise FileNotFoundError("%s: not found on PATH" % name)


def dirty(path):
    out = subprocess.run([find_exe("git"), "status", "--porcelain", "--", path], capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.abspath(path)) or ".")
    return out.returncode != 0 or bool(out.stdout.strip())


# ---------- backup: what a killed run left in the file comes back on the next run ----------

def backups_dir(path):
    """<git dir>/mutation-check for the repository holding path (a file or a folder), or None."""
    where = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    out = subprocess.run([find_exe("git"), "rev-parse", "--absolute-git-dir"], capture_output=True, text=True, cwd=where)
    return os.path.join(out.stdout.strip(), "mutation-check") if out.returncode == 0 else None


def save_backup(backup, path, original, mutant):
    """Record the original and the mutant about to be written; written whole, then renamed into place."""
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    with open(backup + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"file": os.path.abspath(path), "original": original, "mutant": mutant}, f)
    os.replace(backup + ".tmp", backup)


def recover(path):
    """Put back every file that an interrupted run in this repository left mutated."""
    folder = backups_dir(path)
    if not folder or not os.path.isdir(folder):
        return
    for name in sorted(os.listdir(folder)):
        backup = os.path.join(folder, name)
        if not name.endswith(".json"):
            os.remove(backup)
            continue
        with open(backup, encoding="utf-8") as f:
            saved = json.load(f)
        try:
            current = read(saved["file"])
        except FileNotFoundError:
            current = None
        if current == saved["mutant"] and current != saved["original"]:
            write(saved["file"], saved["original"])
            print("restored %s: an interrupted run had left a mutant in it" % saved["file"], file=sys.stderr)
        elif current != saved["original"]:
            refuse("%s changed since an interrupted run left a mutant in it, so it was not touched. Its original "
                   "is in %s: compare the two, then delete that backup." % (saved["file"], backup))
        os.remove(backup)


class Interrupted(Exception):
    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


def on_signal(signum, _frame):
    raise Interrupted(signum)


def kill_tree(proc):
    """Kill the test command and every process it started: killing the shell alone leaves the tests running."""
    if os.name == "nt":
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
        subprocess.run([taskkill, "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    proc.wait()


def run_tests(cmd, timeout):
    """("passed" | "failed" | "timeout", seconds, output). The command runs in a process group of its own
    with its output in a file (a pipe held open by a leftover process would block the read); on timeout
    or interrupt the whole group is killed."""
    # a fresh bytecode cache per run: Python trusts a .pyc whose source has the same size and the same
    # mtime second, so a same-length mutant written within a second would run the previous mutant's code
    cache = tempfile.mkdtemp(prefix="mutate-pyc-")
    env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    start = time.time()
    try:
        with open(os.path.join(cache, "output.txt"), "w+b") as log:
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, env=env, **group)
            status = None
            try:
                while status is None:
                    try:  # short waits, so a signal handler runs while the tests do
                        status = "passed" if proc.wait(timeout=0.2) == 0 else "failed"
                    except subprocess.TimeoutExpired:
                        if timeout and time.time() - start > timeout:
                            status = "timeout"
            finally:
                if status in (None, "timeout"):
                    kill_tree(proc)
            log.seek(0)
            output = log.read().decode("utf-8", "replace")
        return status, time.time() - start, output
    finally:
        shutil.rmtree(cache, ignore_errors=True)


def cmd_run(a):
    check_input(a.file)
    recover(a.file)
    if dirty(a.file):
        refuse("%s has uncommitted changes (or is not in git): commit or stash it first" % a.file)
    original, found = mutants(a.file, a.lines, a.function)
    found = found[:a.max] if a.max else found
    for name in ("SIGINT", "SIGTERM", "SIGBREAK", "SIGHUP"):  # SIGBREAK: Ctrl+Break or a closed console on Windows
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), on_signal)
    status, took, out = run_tests(a.test, a.timeout or None)
    if status != "passed":
        tail = out[-1500:] if status == "failed" else "timed out"
        refuse("the tests do not pass on the original file; fix that first.\n" + tail, code=3)
    limit = a.timeout or max(10.0, 3 * took + 5)
    # a run killed with no chance to clean up leaves a mutant in the file: the next run puts this back
    backup = os.path.join(backups_dir(a.file),
                          hashlib.sha1(os.path.abspath(a.file).encode("utf-8")).hexdigest()[:16] + ".json")
    save_backup(backup, a.file, original, original)
    results = []
    try:
        for m in found:
            save_backup(backup, a.file, original, m["source"])
            write(a.file, m["source"])
            verdict, _, _ = run_tests(a.test, limit)
            write(a.file, original)
            results.append({"id": m["id"], "line": m["line"], "change": m["change"],
                            "status": {"failed": "killed", "passed": "survived", "timeout": "timeout"}[verdict]})
            if not a.json:
                print("%-5s line %-5d %-28s %s" % (m["id"], m["line"], m["change"], results[-1]["status"]), flush=True)
    finally:
        write(a.file, original)
        os.remove(backup)
    killed = sum(r["status"] != "survived" for r in results)
    summary = {"file": a.file, "test": a.test, "mutants": len(results), "killed": killed,
               "survived": [r for r in results if r["status"] == "survived"],
               "score": round(killed / len(results), 3) if results else None, "results": results}
    if a.json:
        print(json.dumps(summary, indent=1))
    else:
        print("score %s: %d of %d mutants killed; %d survived" % (
            summary["score"], killed, len(results), len(summary["survived"])))
    return 1 if summary["survived"] else 0


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("restore").add_argument("file", nargs="?", default=".")
    for name in ("list", "run"):
        s = sub.add_parser(name)
        s.add_argument("file")
        s.add_argument("--lines")
        s.add_argument("--function")
        s.add_argument("--json", action="store_true")
        if name == "run":
            s.add_argument("--test", required=True, help="the project's test command, run from the current folder")
            s.add_argument("--max", type=int, default=0)
            s.add_argument("--timeout", type=float, default=0, help="seconds per run (default: 3x the baseline + 5)")
    a = p.parse_args()
    if a.cmd == "list":
        check_input(a.file)
        _, found = mutants(a.file, a.lines, a.function)
        if a.json:
            print(json.dumps([{k: m[k] for k in ("id", "line", "change")} for m in found], indent=1))
        else:
            for m in found:
                print("%-5s line %-5d %s" % (m["id"], m["line"], m["change"]))
        return 0
    if a.cmd == "restore":
        if not os.path.exists(a.file):
            refuse("%s: no such file or folder" % a.file)
        recover(a.file)
        return 0
    try:
        return cmd_run(a)
    except Interrupted as stop:
        print("interrupted: %s is as it was before the run" % a.file, file=sys.stderr)
        return 128 + stop.signum


if __name__ == "__main__":
    sys.exit(main())
