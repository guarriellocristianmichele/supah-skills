#!/usr/bin/env python3
"""Calibrate the code scanner (skills/ai-slop-audit/scripts/codescan.py) on human and AI code. Stdlib only.

  python scripts/calibrate_code.py fetch                  CodeMirage human and 2025-model files into .calibration/code/
  python scripts/calibrate_code.py frontier [--per-lang N] [--models opus,sonnet,haiku] [--jobs J]
                                                          regenerate human seed files with today's Claude models
  python scripts/calibrate_code.py run                    scan every document
  python scripts/calibrate_code.py report                 tiers -> codescan-calibration.json + results note

Method: the prose calibration's (ADR 0007, docs/research/2026-11-false-positive-control.md), with a file as
the document. Human side: CodeMirage human files (GitHub code cleaned in May 2022). AI side used for
likelihood ratios: the frontier stratum, written by `claude -p` from a summary of a human seed file (the
CodeMirage protocol: describe the file, then reimplement it at the same length), in an empty folder with
hooks and user settings off. The CodeMirage 2025-model files are reported beside it.

CodeMirage is CC BY-NC-ND 4.0: fetched and generated files stay in the ignored .calibration/ folder and
only counts reach the repository (docs/research/2026-11-ai-code-corpora.md).
"""
import argparse
import concurrent.futures
import csv
import difflib
import io
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calibrate  # noqa: E402  (wilson, admit, http_json)

WORK = os.path.join(ROOT, ".calibration", "code")
DOCS = os.path.join(WORK, "docs.jsonl")
SCANS = os.path.join(WORK, "scans.jsonl")
FRONTIER = os.path.join(WORK, "frontier")
SUMMARIES = os.path.join(WORK, "summaries")
SCANNER = os.path.join(ROOT, "skills", "ai-slop-audit", "scripts")
OUT_JSON = os.path.join(SCANNER, "codescan-calibration.json")
OUT_NOTE = os.path.join(ROOT, "docs", "research", "2026-11-code-calibration-results.md")
sys.path.insert(0, SCANNER)

DATASET = "HanxiGuo/CodeMirage"
LANGS = {"py": ("Python", ".py"), "js": ("JavaScript", ".js")}
EXT = {"py": "python", "js": "javascript"}
MAX_SIMILARITY = 0.5  # share of matching non-blank lines between seed and generation
CLAUDE_FLAGS = ["--no-session-persistence", "--setting-sources", "project",
                "--settings", '{"disableAllHooks": true}', "--tools="]


def stream_csv(split):
    """Rows of CodeMirage's CSV for a split, read as the download arrives (datasets-server /filter
    answers 500 on this dataset more often than not)."""
    url = "https://huggingface.co/datasets/%s/resolve/main/%s.csv" % (DATASET, split)
    csv.field_size_limit(2 ** 31 - 1)
    with urllib.request.urlopen(url, timeout=300) as r:
        yield from csv.DictReader(io.TextIOWrapper(r, encoding="utf-8", newline=""))


def cmd_fetch(args):
    os.makedirs(WORK, exist_ok=True)
    names = {name: lang for lang, (name, _) in LANGS.items()}
    rng = random.Random(7)
    with open(DOCS, "w", encoding="utf-8") as out:
        for split in ("test", "train"):
            reservoirs, seen = {}, {}
            for i, row in enumerate(stream_csv(split)):
                lang = names.get(row.get("language"))
                if not lang:
                    continue
                doc = {"id": "%s/%s#%d" % (DATASET, split, i), "lang": lang, "split": split, "code": row["code"]}
                if row["source"] == "Human":
                    out.write(json.dumps(dict(doc, side="human", source="codemirage-human"), ensure_ascii=False) + "\n")
                elif row.get("variant") == "Normal":  # reservoir sample per model and language
                    key = (lang, row["source"])
                    seen[key] = seen.get(key, 0) + 1
                    pool = reservoirs.setdefault(key, [])
                    item = dict(doc, side="ai", source="codemirage-" + row["source"])
                    if len(pool) < args.ai_per_model:
                        pool.append(item)
                    elif rng.random() < args.ai_per_model / seen[key]:
                        pool[rng.randrange(args.ai_per_model)] = item
            for pool in reservoirs.values():
                for item in pool:
                    out.write(json.dumps(item, ensure_ascii=False) + "\n")
            out.flush()
            print("%s: done" % split, flush=True)
    print("wrote %s" % DOCS)


def load_docs():
    with open(DOCS, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def claude(prompt, model, timeout=600):
    # The CLI attaches the file or folder behind any `@path` in a prompt, and seed code is full of `@`
    # (decorators, scoped imports): one such call wrote 300k tokens to the cache. A zero-width space after
    # each `@` keeps the text readable and inert. Prompt caching is off: every call has a fresh prefix,
    # so a cache write costs more than it saves.
    prompt = prompt.replace("@", "@​")
    env = dict(os.environ, DISABLE_PROMPT_CACHING="1")
    with tempfile.TemporaryDirectory() as empty:  # no CLAUDE.md, no project settings
        out = subprocess.run(["claude", "-p", prompt, "--model", model, "--output-format", "json", *CLAUDE_FLAGS],
                             cwd=empty, env=env, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300] or out.stdout[:300])
    data = json.loads(out.stdout)
    usage = data.get("usage") or {}
    with open(os.path.join(WORK, "costs.jsonl"), "a", encoding="utf-8") as log:
        log.write(json.dumps({"model": model, "cost": data.get("total_cost_usd"), "turns": data.get("num_turns"),
                              "output": usage.get("output_tokens"),
                              "thinking": (usage.get("output_tokens_details") or {}).get("thinking_tokens"),
                              "cache_write": usage.get("cache_creation_input_tokens")}) + "\n")
    return data.get("result", ""), data.get("total_cost_usd") or 0.0


def fenced(text, lang):
    blocks = re.findall(r"```[\w+-]*\n(.*?)```", text, re.S)
    return max(blocks, key=len) if blocks else None


def summarise(seed):
    path = os.path.join(SUMMARIES, re.sub(r"\W", "_", seed["id"]) + ".txt")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    prompt = ("In at most 150 words, describe what this %s file does, as a request a developer would give a "
              "colleague: its purpose, the public functions or classes and what they do, and the libraries it "
              "uses. Describe behaviour, not wording or style. Do not name the project, its authors or its "
              "license. Plain text, no code.\n\n```\n%s\n```"
              % (LANGS[seed["lang"]][0], seed["code"][:12000]))
    text, _ = claude(prompt, "haiku")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def generate(seed, model):
    target = os.path.join(FRONTIER, model, re.sub(r"\W", "_", seed["id"]) + LANGS[seed["lang"]][1])
    if os.path.exists(target) or os.path.exists(os.path.join(FRONTIER, "_recalled", model, os.path.basename(target))):
        return 0.0
    summary = summarise(seed)
    lines = seed["code"].count("\n") + 1
    prompt = ("Write the complete %s file described below, about %d lines long. Reply with the code in a "
              "single fenced block.\n\n%s" % (LANGS[seed["lang"]][0], lines, summary))
    text, cost = claude(prompt, model)
    code = fenced(text, seed["lang"])
    if code:
        # a model that recognises the seed recalls it instead of writing new code; such files are human
        # code on the AI side, so they are set aside (CodeMirage caps BLEU at 0.5 for the same reason)
        if copied(seed["code"], code) > MAX_SIMILARITY:
            target = os.path.join(FRONTIER, "_recalled", model, os.path.basename(target))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(code)
    return cost


def copied(original, generated):
    a = [l.strip() for l in original.splitlines() if l.strip()]
    b = [l.strip() for l in generated.splitlines() if l.strip()]
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def cmd_frontier(args):
    os.makedirs(SUMMARIES, exist_ok=True)
    docs = load_docs()
    seeds = []
    for lang in LANGS:
        pool = [d for d in docs if d["lang"] == lang and d["side"] == "human" and d["split"] == "test"]
        seeds += pool[:args.per_lang]
    jobs = [(s, m) for m in args.models.split(",") for s in seeds]
    spent, failed, done = 0.0, 0, 0
    # summaries first, one per seed, so parallel generations never write the same file
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for future in concurrent.futures.as_completed([pool.submit(summarise, s) for s in seeds]):
            try:
                future.result()
            except Exception as e:  # a failed seed is retried on the next run
                failed += 1
                print("summary failed:", e, flush=True)
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        futures = {pool.submit(generate, s, m): (s["id"], m) for s, m in jobs}
        for future in concurrent.futures.as_completed(futures):
            try:
                spent += future.result()
            except Exception as e:
                failed += 1
                print("failed %s %s: %s" % (*futures[future], e), flush=True)
            done += 1
            if done % 25 == 0:
                print("%d/%d done, %d failed, $%.2f" % (done, len(jobs), failed, spent), flush=True)
    print("frontier: %d jobs, %d failed, $%.2f; rerun to retry the failures" % (len(jobs), failed, spent))


def cmd_run(args):
    import codescan
    os.environ["SUPAH_CODE_NO_CALIBRATION"] = "1"
    docs = load_docs()
    for model in sorted(m for m in os.listdir(FRONTIER) if not m.startswith("_")) if os.path.isdir(FRONTIER) else []:
        for name in sorted(os.listdir(os.path.join(FRONTIER, model))):
            lang = "py" if name.endswith(".py") else "js"
            with open(os.path.join(FRONTIER, model, name), encoding="utf-8") as f:
                docs.append({"id": "%s/%s" % (model, name), "lang": lang, "side": "ai",
                             "source": "frontier-" + model, "code": f.read()})
    with open(SCANS, "w", encoding="utf-8") as out:
        for d in docs:
            r = codescan.scan_text(d["code"], "x" + LANGS[d["lang"]][1])
            counts = {}
            for h in r["hits"]:
                counts[h["rule"]] = counts.get(h["rule"], 0) + 1
            out.write(json.dumps({"id": d["id"], "lang": d["lang"], "side": d["side"], "source": d["source"],
                                  "parsed": r["skipped"] is None, "lines": d["code"].count("\n") + 1,
                                  "rules": counts}) + "\n")
    print("scanned %d documents -> %s" % (len(docs), SCANS))


# Hits judged by reading them, sampled across human, 2025-model and Sonnet 5.5 files (2026-11-14):
# (real slop, judged). Add verdicts here and rerun `report`.
PRECISION = {
    "catch-rethrow": (8, 8), "placeholder": (8, 8), "swallowed-exception": (8, 8), "restating-comment": (8, 8),
    "annotated-isinstance": (3, 4), "bool-return": (4, 5), "forwarding-wrapper": (5, 8),
    "restating-docstring": (5, 8), "step-comment": (4, 8),
}
S_PRECISION, M_PRECISION, MIN_JUDGED_S = 0.9, 0.7, 8


def precision_tier(real, judged):
    share = real / judged
    return "S" if share >= S_PRECISION and judged >= MIN_JUDGED_S else "M" if share >= M_PRECISION else "W"


def rate(docs, rule):
    return sum(1 for d in docs if d["rules"].get(rule)), len(docs)


def cmd_report(args):
    import codescan
    scans = [json.loads(line) for line in open(SCANS, encoding="utf-8")]
    rules_out, rows = {}, []
    for lang in LANGS:
        mine = [d for d in scans if d["lang"] == lang and d["parsed"]]
        human = [d for d in mine if d["side"] == "human"]
        frontier = [d for d in mine if d["source"].startswith("frontier-")]
        older = [d for d in mine if d["side"] == "ai" and d["source"].startswith("codemirage-")]
        representative = len(frontier) >= calibrate.MIN_REPRESENTATIVE_AI
        for rule, (cat, designed, langs) in codescan.RULES.items():
            if lang not in langs.split():
                continue
            h, nh = rate(human, rule)
            a, na = rate(frontier, rule)
            o, no = rate(older, rule)
            _, h_up, lr = calibrate.admit(h, nh, a, na, representative)
            real, judged = PRECISION.get(rule, (0, 0))
            tier = precision_tier(real, judged) if judged else designed
            rules_out["%s/%s" % (rule, lang)] = {"tier": tier, "precision": [real, judged],
                                                 "human_rate": round(h / max(1, nh), 4),
                                                 "human_upper": round(h_up, 4), "frontier_rate": round(a / max(1, na), 4),
                                                 "codemirage_rate": round(o / max(1, no), 4), "lr": round(lr, 2)}
            rows.append((lang, rule, designed, h, nh, a, na, o, no, lr, real, judged, tier))
        per_model = {}
        for d in frontier + older:
            per_model.setdefault(d["source"], []).append(d)
        rules_out.setdefault("_sizes", {})[lang] = {"human": len(human), "frontier": len(frontier),
                                                   "codemirage_ai": len(older),
                                                   "by_source": {k: len(v) for k, v in sorted(per_model.items())}}
    sizes = rules_out.pop("_sizes")
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"method": "ADR 0010: tier from judged precision; rates and likelihood ratios are context",
                   "sizes": sizes, "rules": rules_out}, f, indent=1)
        f.write("\n")
    write_note(rows, sizes, scans)
    print("wrote %s and %s" % (OUT_JSON, OUT_NOTE))


def pct(k, n):
    return "%d (%.1f%%)" % (k, 100.0 * k / n) if n else "n/a"


def write_note(rows, sizes, scans):
    lines = ["# Code scanner calibration results", "",
             "Generated by `python scripts/calibrate_code.py report`. Human side: CodeMirage human files "
             "(GitHub code cleaned in May 2022). Frontier side: files written by today's Claude models from a "
             "summary of a human seed file. CodeMirage side: the same protocol run in 2025 by ten models "
             "(Claude 3.5 Haiku, GPT-4o-mini, o3-mini, DeepSeek V3 and R1, Gemini 2.0, Llama 3.3, Qwen2.5-Coder). "
             "A hit is slop when the code does not need what it matched, whoever wrote it (ADR 0003), so the "
             "shipped tier comes from judged precision, the share of sampled hits that were real (ADR 0010): "
             "S needs %d%% of at least %d, M %d%%. Rules with no judged hits keep their designed tier. Human and AI "
             "rates, and the likelihood ratio of frontier to human, say how often each pattern turns up, not "
             "whether a hit is real." % (100 * S_PRECISION, MIN_JUDGED_S, 100 * M_PRECISION), ""]
    for lang, s in sizes.items():
        lines.append("%s: %d human files, %d frontier files, %d CodeMirage AI files; by source: %s." % (
            LANGS[lang][0], s["human"], s["frontier"], s["codemirage_ai"],
            ", ".join("%s %d" % kv for kv in s["by_source"].items())))
    unparsed = sum(1 for d in scans if not d["parsed"])
    lines += ["", "Files the scanner could not parse are left out (%d)." % unparsed, "",
              "| lang | rule | designed | human | frontier | CodeMirage AI | LR | precision | shipped |",
              "|---|---|---|---|---|---|---|---|---|"]
    for lang, rule, designed, h, nh, a, na, o, no, lr, real, judged, tier in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %.1f | %s | %s |" % (
            lang, rule, designed, pct(h, nh), pct(a, na), pct(o, no), lr,
            "%d/%d" % (real, judged) if judged else "none judged", tier))
    with open(OUT_NOTE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--ai-per-model", type=int, default=60, help="CodeMirage 2025-model files per model, language and split")
    g = sub.add_parser("frontier")
    g.add_argument("--per-lang", type=int, default=300)
    g.add_argument("--models", default="opus,sonnet,haiku")
    g.add_argument("--jobs", type=int, default=6)
    sub.add_parser("run")
    sub.add_parser("report")
    a = p.parse_args()
    {"fetch": cmd_fetch, "frontier": cmd_frontier, "run": cmd_run, "report": cmd_report}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
