#!/usr/bin/env python3
"""Calibrate the ai-slop-prose scanner on human and AI corpora. Stdlib only. Dev tool, not shipped.

  python scripts/calibrate.py fetch [--per-source N]   download samples into .calibration/
  python scripts/calibrate.py run                       scan every document
  python scripts/calibrate.py report [--alpha A]        statistics -> calibration.json + results note

Method (docs/research/2026-11-false-positive-control.md):
- per rule and language: share of human and AI documents with an open hit, Wilson 95% bounds,
  likelihood ratio, and an admitted tier (S: human upper bound <= 0.5% and LR >= 20; M: LR >= 5);
  the shipped tier is the designed tier lowered to the admitted one, never raised. Punctuation and
  formatting rules enforce style, not authorship, and are reported but not demoted;
- per language and length bucket: split-conformal thresholds for each density metric at alpha on the
  human calibration split, so P(metric flags a human document) <= alpha under exchangeability;
- a 30% holdout measures the realised false positive rate with a Clopper-Pearson 95% upper bound.

Corpora are downloaded for measurement only; nothing but derived statistics is written to the repo.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, ".calibration")
DOCS = os.path.join(WORK, "docs.jsonl")
SCANS = os.path.join(WORK, "scans.jsonl")
SCRIPTS = os.path.join(ROOT, "skills", "ai-slop-prose", "scripts")
OUT_JSON = os.path.join(SCRIPTS, "calibration.json")
OUT_NOTE = os.path.join(ROOT, "docs", "research", "2026-11-calibration-results.md")
sys.path.insert(0, SCRIPTS)

HF_ROWS = "https://datasets-server.huggingface.co"
HC3 = "https://huggingface.co/datasets/Hello-SimpleAI/HC3/resolve/main/all.jsonl"
STYLE_CATEGORIES = {"punctuation", "formatting"}
BUCKETS = [(0, 150, "<150"), (150, 400, "150-400"), (400, 1000, "400-1000"), (1000, 10 ** 9, ">1000")]
MIN_WORDS, MAX_WORDS = 60, 3000

# id, lang, origin, genre, fetcher, spec
SOURCES = [
    ("arxiv-2021", "en", "human", "academic", "rows",
     {"dataset": "gfissore/arxiv-abstracts-2021", "config": "default", "split": "train", "field": "abstract"}),
    ("cnn-dailymail", "en", "human", "news", "rows",
     {"dataset": "abisee/cnn_dailymail", "config": "3.0.0", "split": "train", "field": "article"}),
    ("reddit-tldr17", "en", "human", "informal", "rows",
     {"dataset": "webis/tldr-17", "config": "default", "split": "train", "field": "content"}),
    ("ellipse-l2", "en", "human", "essay-non-native", "csv",
     {"url": "https://raw.githubusercontent.com/scrosseye/ELLIPSE-Corpus/main/ELLIPSE_Final_github_train.csv",
      "field": "full_text"}),
    ("hc3-human", "en", "human", "qa", "hc3", {"field": "human_answers"}),
    ("hc3-chatgpt", "en", "ai", "qa", "hc3", {"field": "chatgpt_answers"}),
    ("beemo", "en", "ai", "mixed", "rows",
     {"dataset": "toloka/beemo", "config": "default", "split": "train", "field": "model_output"}),
    ("hap-e", "en", "ai", "mixed", "rows",
     {"dataset": "browndw/human-ai-parallel-corpus", "config": "default", "split": "train", "field": "text",
      "keep_id": lambda r: "@" in r.get("doc_id", "") and "chunk" not in r["doc_id"]}),
    ("ilpost", "it", "human", "news", "csv",
     {"url": "https://huggingface.co/datasets/ARTeLab/ilpost/resolve/main/train.csv", "field": "source"}),
    ("dice", "it", "human", "news-crime", "csv",
     {"url": "https://raw.githubusercontent.com/federicarollo/Italian-Crime-News/main/italian_crime_news.csv",
      "field": "text"}),
    ("europarl-it", "it", "human", "parliament", "gzlines",
     {"url": "https://object.pouta.csc.fi/OPUS-Europarl/v8/mono/it.txt.gz", "lines": 14}),
    ("paisa", "it", "human", "web", "rows",
     {"dataset": "KarlGauss/paisa_corpus", "config": "default", "split": "train", "field": "text_content"}),
    ("coling-it", "it", "ai", "news", "filter",
     {"dataset": "Jinyan1/COLING_2025_MGT_multingual", "config": "default", "split": "train", "field": "text",
      "where": "\"lang\"='it'"}),
]


def http_json(url, tries=6):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # datasets-server answers 502/503 under load
            err = e
            time.sleep(3 * (attempt + 1))
    raise err


def fetch_rows(spec, n, use_filter=False):
    total = None
    probe = {"dataset": spec["dataset"], "config": spec["config"], "split": spec["split"], "offset": 0, "length": 1}
    if use_filter:
        probe["where"] = spec["where"]
    total = http_json(f"{HF_ROWS}/{'filter' if use_filter else 'rows'}?{urllib.parse.urlencode(probe)}")["num_rows_total"]
    pages = max(1, math.ceil(n * 1.6 / 100))
    stride = max(100, total // pages)
    out = []
    for i in range(pages):
        q = dict(probe, offset=min(i * stride, max(0, total - 100)), length=100)
        data = http_json(f"{HF_ROWS}/{'filter' if use_filter else 'rows'}?{urllib.parse.urlencode(q)}")
        for row in data["rows"]:
            r = row["row"]
            if spec.get("keep_id") and not spec["keep_id"](r):
                continue
            out.append((f"{spec['dataset']}#{row['row_idx']}", r[spec["field"]]))
        if len(out) >= n * 1.5:
            break
    return out


def fetch_csv(spec, n):
    csv.field_size_limit(10 ** 8)
    with urllib.request.urlopen(spec["url"], timeout=300) as r:
        data = r.read()
    for encoding in ("utf-8", "cp1252", "latin-1"):  # DICE ships as cp1252; a wrong guess corrupts every accent
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(io.StringIO(text)))
    step = max(1, len(rows) // (n * 2))
    return [(f"{spec['url']}#{i}", rows[i][spec["field"]]) for i in range(0, len(rows), step)][: n * 2]


def fetch_gzlines(spec, n):
    out, buf, idx = [], [], 0
    with urllib.request.urlopen(spec["url"], timeout=300) as r:
        with gzip.GzipFile(fileobj=r) as gz:
            for raw in gz:
                buf.append(raw.decode("utf-8", "replace").strip())
                if len(buf) == spec["lines"]:
                    out.append((f"{spec['url']}#{idx}", " ".join(buf)))
                    buf, idx = [], idx + 1
                    if len(out) >= n * 2:
                        break
    return out


def fetch_hc3(spec, n, cache={}):
    if "rows" not in cache:
        with urllib.request.urlopen(HC3, timeout=300) as r:
            cache["rows"] = [json.loads(l) for l in r.read().decode("utf-8").splitlines() if l.strip()]
    out = []
    for i, row in enumerate(cache["rows"]):
        for j, ans in enumerate(row.get(spec["field"]) or []):
            out.append((f"hc3#{i}.{j}", ans))
    step = max(1, len(out) // (n * 2))
    return out[::step][: n * 2]


def cmd_fetch(args):
    os.makedirs(WORK, exist_ok=True)
    seen = 0
    with open(DOCS, "a" if args.only else "w", encoding="utf-8") as f:
        for sid, lang, origin, genre, kind, spec in SOURCES:
            if args.only and sid not in args.only:
                continue
            try:
                if kind == "rows":
                    items = fetch_rows(spec, args.per_source)
                elif kind == "filter":
                    items = fetch_rows(spec, args.per_source, use_filter=True)
                elif kind == "csv":
                    items = fetch_csv(spec, args.per_source)
                elif kind == "gzlines":
                    items = fetch_gzlines(spec, args.per_source)
                else:
                    items = fetch_hc3(spec, args.per_source)
            except Exception as e:
                print(f"  {sid}: FAILED ({e})")
                continue
            kept = 0
            for doc_id, text in items:
                words = len((text or "").split())
                if MIN_WORDS <= words <= MAX_WORDS and kept < args.per_source:
                    f.write(json.dumps({"id": doc_id, "source": sid, "lang": lang, "origin": origin,
                                        "genre": genre, "text": text}, ensure_ascii=False) + "\n")
                    kept += 1
            seen += kept
            print(f"  {sid}: {kept} documents")
    print(f"{seen} documents in {DOCS}")
    return 0


def cmd_run(args):
    os.environ["SUPAH_PROSE_NO_CALIBRATION"] = "1"  # measure the designed tiers, not a previous calibration
    import scan  # noqa: E402
    n = 0
    with open(DOCS, encoding="utf-8") as src, open(SCANS, "w", encoding="utf-8") as out:
        for line in src:
            d = json.loads(line)
            r = scan.scan_text(d["text"], d["lang"], {}, gates=True, model=None, path=d["id"])
            counts = {}
            for h in r["hits"]:
                if not h["kept"]:
                    key = f"{h['rule']}|{h['category']}|{h['tier']}"
                    counts[key] = counts.get(key, 0) + 1
            record = {k: d[k] for k in ("id", "source", "lang", "origin", "genre")}
            record.update(marked=sorted({h["match"].lower() for h in r["hits"]
                                         if h["rule"] == "marked-word" and not h["kept"]}))
            record.update(words=r["metrics"]["words"], counts=counts, metrics=r["metrics"],
                          split="cal" if int(hashlib.sha1(d["id"].encode()).hexdigest(), 16) % 10 < 7 else "hold")
            out.write(json.dumps(record) + "\n")
            n += 1
    print(f"scanned {n} documents -> {SCANS}")
    return 0


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / (1 + z * z / n)), min(1.0, (centre + spread) / (1 + z * z / n))


def clopper_pearson_upper(k, n, conf=0.95):
    import learn  # exact Beta quantile
    return 1.0 if k >= n else learn.beta_quantile(conf, k + 1, n - k)


S_MAX_HUMAN, M_MAX_HUMAN = 0.005, 0.01   # Wilson 95% upper bound on the human document hit rate
DOC_MAX_HUMAN = 0.01  # the same bound for a whole document carrying required fixes
S_MIN_LR, M_MIN_LR = 20, 5
REPRESENTATIVE_AI = {"en"}  # the only Italian AI corpus is a fine-tuned news generator built to look human


def worse(a, b):
    return a if "SMW".index(a) >= "SMW".index(b) else b


def admit(h, n_h, a, n_a, representative):
    """Tier a rule earns: false-positive bound always, likelihood ratio only with a representative AI corpus."""
    _, h_up = wilson(h, n_h)
    fp_tier = "S" if h_up <= S_MAX_HUMAN else "M" if h_up <= M_MAX_HUMAN else "W"
    hr, ar = h / max(1, n_h), a / max(1, n_a)
    lr = (ar + 0.5 / max(1, n_a)) / (hr + 0.5 / max(1, n_h))
    if not representative:
        return fp_tier, h_up, lr
    lr_tier = "S" if lr >= S_MIN_LR else "M" if lr >= M_MIN_LR else "W"
    return worse(fp_tier, lr_tier), h_up, lr


def bucket(words):
    for lo, hi, name in BUCKETS:
        if lo <= words < hi:
            return name
    return BUCKETS[-1][2]


def conformal(scores, alpha, upper=True):
    """Split-conformal threshold on human scores: flag above it (or below, for lower-tail metrics)."""
    s = sorted(scores)
    n = len(s)
    if n < math.ceil(1 / alpha) - 1:
        return None
    if upper:
        k = math.ceil((n + 1) * (1 - alpha))
        return s[min(k, n) - 1]
    k = math.floor((n + 1) * alpha)
    return s[max(k, 1) - 1]


def cmd_report(args):
    import scan  # noqa: E402
    docs = [json.loads(l) for l in open(SCANS, encoding="utf-8")]
    langs = sorted({d["lang"] for d in docs})
    rules_out, metrics_out, words_out, marked_min, evidence_min, lines = {}, {}, {}, {}, {}, []
    lines.append("# Calibration results\n")
    lines.append(f"Generated by `scripts/calibrate.py` on {time.strftime('%Y-%m-%d')}, alpha = {args.alpha}. "
                 "Method: docs/research/2026-11-false-positive-control.md.\n")
    summary = {}
    for d in docs:
        key = (d["lang"], d["origin"], d["source"], d["genre"])
        summary[key] = summary.get(key, 0) + 1
    lines.append("## Corpus\n\n| lang | origin | source | genre | documents |\n|---|---|---|---|---|")
    for (lang, origin, src, genre), c in sorted(summary.items()):
        lines.append(f"| {lang} | {origin} | {src} | {genre} | {c} |")

    for lang in langs:
        human = [d for d in docs if d["lang"] == lang and d["origin"] == "human"]
        ai = [d for d in docs if d["lang"] == lang and d["origin"] == "ai"]
        h_cal = [d for d in human if d["split"] == "cal"]
        a_cal = [d for d in ai if d["split"] == "cal"]
        representative = lang in REPRESENTATIVE_AI
        rule_keys = sorted({k for d in human + ai for k in d["counts"]})
        lines.append(f"\n## Rules, {lang} (calibration split: {len(h_cal)} human, {len(a_cal)} AI documents; "
                     f"likelihood ratio {'used' if representative else 'not used: AI corpus not representative'})\n")
        lines.append("| rule | designed | human docs hit | 95% upper | AI docs hit | LR | admitted | shipped |\n"
                     "|---|---|---|---|---|---|---|---|")
        for key in rule_keys:
            rule, cat, tier = key.split("|")
            h = sum(1 for d in h_cal if key in d["counts"])
            a = sum(1 for d in a_cal if key in d["counts"])
            admitted, h_up, lr = admit(h, len(h_cal), a, len(a_cal), representative)
            if cat in STYLE_CATEGORIES:
                admitted, shipped = "style", tier
            elif h + a < 5:
                admitted, shipped = "too few", tier
            else:
                shipped = worse(tier, admitted)
            hr, ar = h / max(1, len(h_cal)), a / max(1, len(a_cal))
            rules_out[f"{rule}/{lang}"] = {"designed": tier, "tier": shipped, "human_rate": round(hr, 4),
                                           "human_upper95": round(h_up, 4), "ai_rate": round(ar, 4),
                                           "lr": round(lr, 2), "admitted": admitted}
            lines.append(f"| {rule} | {tier} | {h} ({hr:.1%}) | {h_up:.1%} | {a} ({ar:.1%}) | {lr:.1f} | "
                         f"{admitted} | {shipped} |")

        # the marked lexicon, word by word: words common in human text move to the density list
        words = sorted({w for d in human + ai for w in d.get("marked", [])})
        demoted = []
        lines.append(f"\n## Marked words, {lang}\n")
        lines.append("| word | human docs | 95% upper | AI docs | LR | admitted |\n|---|---|---|---|---|---|")
        for w in words:
            h = sum(1 for d in h_cal if w in d.get("marked", []))
            a = sum(1 for d in a_cal if w in d.get("marked", []))
            admitted, h_up, lr = admit(h, len(h_cal), a, len(a_cal), representative)
            if h > 0 and admitted == "W":
                demoted.append(w)
            lines.append(f"| {w} | {h} | {h_up:.1%} | {a} | {lr:.1f} | {admitted} |")
        words_out[lang] = demoted
        lines.append(f"\nMoved to the density list: {', '.join(demoted) if demoted else 'none'}.")

        # one marked word is something a person writes; several distinct ones in one document are the tell.
        # k = smallest count whose human document rate has a Wilson upper bound <= S_MAX_HUMAN.
        def distinct(d):
            return len(set(d.get("marked", [])) - set(demoted))
        k = 1
        while k < 10 and wilson(sum(1 for d in h_cal if distinct(d) >= k), len(h_cal))[1] > S_MAX_HUMAN:
            k += 1
        marked_min[lang] = k
        hk = sum(1 for d in h_cal if distinct(d) >= k)
        ak = sum(1 for d in a_cal if distinct(d) >= k)
        lines.append(f"Marked words flag a document from {k} distinct word(s) on: {hk}/{len(h_cal)} human, "
                     f"{ak}/{len(a_cal)} AI calibration documents.")

        lines.append(f"\n## Metric thresholds, {lang} (split-conformal at alpha = {args.alpha})\n")
        lines.append("| bucket | metric | from | threshold | default | holdout FPR | 95% upper |\n|---|---|---|---|---|---|---|")
        metrics_out[lang] = {}
        # hierarchy: a length bucket with enough calibration documents gets its own threshold; otherwise
        # the language-wide one ("*"); never looser than the designed default
        for bname in ["*"] + [b[2] for b in BUCKETS]:
            cal = [d for d in human if d["split"] == "cal" and (bname == "*" or bucket(d["words"]) == bname)]
            for metric, (default, op) in scan.THRESHOLDS.items():
                vals = [d["metrics"][metric] for d in cal if d["metrics"].get(metric) is not None]
                tau = conformal(vals, args.alpha, upper=(op == ">"))
                if tau is None:
                    continue
                tau = max(tau, default) if op == ">" else min(tau, default)
                metrics_out[lang].setdefault(bname, {})[metric] = tau
        for bname in [b[2] for b in BUCKETS]:
            hold = [d for d in human if d["split"] == "hold" and bucket(d["words"]) == bname]
            for metric, (default, op) in scan.THRESHOLDS.items():
                effective = metrics_out[lang].get(bname, {}).get(metric, metrics_out[lang].get("*", {}).get(metric))
                if effective is None:
                    continue
                source = "bucket" if metric in metrics_out[lang].get(bname, {}) else "language"
                hv = [d["metrics"][metric] for d in hold if d["metrics"].get(metric) is not None]
                if not hv:
                    continue
                k = sum(1 for v in hv if (v > effective if op == ">" else v < effective))
                up = clopper_pearson_upper(k, len(hv))
                lines.append(f"| {bname} | {metric} | {source} | {op} {effective} | {op} {default} | "
                             f"{k}/{len(hv)} | {up:.2%} |")

        # headline: share of held-out human documents with any open authorship hit after calibration
        hold = [d for d in human if d["split"] == "hold"]
        ai_hold = [d for d in ai if d["split"] == "hold"]

        def evidence(d):
            """(any S hit, number of distinct M rules) after the calibrated tiers."""
            strong, medium = False, set()
            for key in d["counts"]:
                rule, cat, _ = key.split("|")
                if cat in STYLE_CATEGORIES:
                    continue
                if rule == "marked-word":
                    if len(set(d.get("marked", [])) - set(words_out.get(lang, []))) >= marked_min.get(lang, 1):
                        medium.add(rule)
                    continue
                tier = rules_out.get(f"{rule}/{lang}", {}).get("tier")
                if tier == "S":
                    strong = True
                elif tier == "M":
                    medium.add(rule)
            return strong, len(medium)

        # combined evidence: an S hit, or m distinct M rules; m = smallest with human upper bound <= DOC_MAX_HUMAN
        m = 1
        while m < 5 and wilson(sum(1 for d in h_cal if (lambda e: e[0] or e[1] >= m)(evidence(d))),
                               len(h_cal))[1] > DOC_MAX_HUMAN:
            m += 1
        evidence_min[lang] = m

        def flagged(d):
            strong, medium = evidence(d)
            return strong or medium >= m
        lines.append(f"\nA document needs one S hit or {m} distinct M rules before its M hits are required fixes; "
                     "isolated M hits are reported as W.")
        k = sum(flagged(d) for d in hold)
        r_ai = sum(flagged(d) for d in ai_hold)
        lines.append(f"\n**Holdout, {lang}:** {k}/{len(hold)} human documents carry an open S/M authorship hit "
                     f"(95% upper bound {clopper_pearson_upper(k, len(hold)) if hold else float('nan'):.2%}); "
                     f"{r_ai}/{len(ai_hold)} AI documents do "
                     f"({(r_ai / len(ai_hold)) if ai_hold else float('nan'):.1%} recall). "
                     "Style rules (punctuation, formatting) are excluded from both counts.")

    calibration = {"built": time.strftime("%Y-%m-%d"), "alpha": args.alpha, "documents": len(docs),
                   "buckets": [b[2] for b in BUCKETS], "rules": rules_out, "metrics": metrics_out,
                   "demoted_words": words_out, "marked_min": marked_min,
                   "evidence_min": evidence_min}
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(calibration, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with open(OUT_NOTE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT_JSON} and {OUT_NOTE}")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--per-source", type=int, default=400)
    f.add_argument("--only", nargs="*")
    sub.add_parser("run")
    r = sub.add_parser("report")
    r.add_argument("--alpha", type=float, default=0.005)
    a = p.parse_args()
    return {"fetch": cmd_fetch, "run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
