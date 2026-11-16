#!/usr/bin/env python3
"""Mutation testing with the project's own test command. Stdlib only.

  mutate.py list FILE [--lines A-B] [--function NAME]
      Print every mutant of FILE: id, line, what changes.
  mutate.py run FILE --test "CMD" [--lines A-B] [--function NAME] [--max N] [--timeout S] [--json]
      Run CMD once on the original (it must pass), then once per mutant, and report each mutant
      as killed (CMD failed), survived (CMD passed) or timeout. Exit 0 when no mutant survived.

Python files are mutated through ast (the mutant is the unparsed tree, so formatting and comments
differ but behaviour only changes where the mutant says). JavaScript and TypeScript are mutated by
replacing one operator or literal in code, never inside strings or comments.

FILE is changed in place while CMD runs and restored after every mutant, on errors and on Ctrl+C.
`run` refuses a file with uncommitted changes, so `git checkout -- FILE` is always a way back.
"""
import argparse
import ast
import copy
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
JS_SWAP = [("===", "!=="), ("!==", "==="), ("<=", "<"), (">=", ">"), ("&&", "||"), ("||", "&&"),
           ("<", "<="), (">", ">="), ("true", "false"), ("false", "true")]


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
    if function and path.endswith(PY):
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
                lo, hi = max(lo, node.lineno), min(hi, node.end_lineno)
                break
        else:
            raise SystemExit("no function %s in %s" % (function, path))
    return lambda line: lo <= line <= hi


def mutants(path, lines=None, function=None):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    keep = selector(lines, function, source, path)
    if path.endswith(PY):
        found = list(py_mutants(source, keep))
    elif path.endswith(JS):
        found = list(js_mutants(source, keep))
    else:
        raise SystemExit("%s: not Python, JavaScript or TypeScript" % path)
    for i, m in enumerate(found, 1):
        m["id"] = "M%d" % i
    return source, found


def dirty(path):
    out = subprocess.run(["git", "status", "--porcelain", "--", path], capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.abspath(path)) or ".")
    return out.returncode != 0 or bool(out.stdout.strip())


def run_tests(cmd, timeout):
    # a fresh bytecode cache per run: Python trusts a .pyc whose source has the same size and the same
    # mtime second, so a same-length mutant written within a second would run the previous mutant's code
    cache = tempfile.mkdtemp(prefix="mutate-pyc-")
    env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
    start = time.time()
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=env)
        return ("passed" if out.returncode == 0 else "failed"), time.time() - start, out
    except subprocess.TimeoutExpired:
        return "timeout", time.time() - start, None
    finally:
        shutil.rmtree(cache, ignore_errors=True)


def cmd_run(a):
    if dirty(a.file):
        raise SystemExit("%s has uncommitted changes (or is not in git): commit or stash it first" % a.file)
    original, found = mutants(a.file, a.lines, a.function)
    found = found[:a.max] if a.max else found
    status, took, out = run_tests(a.test, a.timeout or None)
    if status != "passed":
        tail = (out.stdout + out.stderr)[-1500:] if out else "timed out"
        raise SystemExit("the tests do not pass on the original file; fix that first.\n" + tail)
    limit = a.timeout or max(10.0, 3 * took + 5)

    def restore(*_):
        with open(a.file, "w", encoding="utf-8", newline="") as f:
            f.write(original)

    signal.signal(signal.SIGINT, lambda *_: (restore(), sys.exit(130)))
    results = []
    try:
        for m in found:
            with open(a.file, "w", encoding="utf-8", newline="") as f:
                f.write(m["source"])
            verdict, _, _ = run_tests(a.test, limit)
            restore()
            results.append({"id": m["id"], "line": m["line"], "change": m["change"],
                            "status": {"failed": "killed", "passed": "survived", "timeout": "timeout"}[verdict]})
            if not a.json:
                print("%-5s line %-5d %-28s %s" % (m["id"], m["line"], m["change"], results[-1]["status"]), flush=True)
    finally:
        restore()
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
        _, found = mutants(a.file, a.lines, a.function)
        if a.json:
            print(json.dumps([{k: m[k] for k in ("id", "line", "change")} for m in found], indent=1))
        else:
            for m in found:
                print("%-5s line %-5d %s" % (m["id"], m["line"], m["change"]))
        return 0
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
