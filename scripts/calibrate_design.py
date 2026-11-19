#!/usr/bin/env python3
"""Calibrate the design scanner (skills/ai-slop-design/scripts/designscan.py) on web pages. Stdlib only.

  python scripts/calibrate_design.py fetch [--human N] [--jobs J]
      AI-era pages: the sites labelled by design-slop-cop (MIT), each as the Wayback Machine snapshot
      closest to its label date. Human pages: a seeded sample of Tranco-listed domains as archived in
      mid-2021, before generated sites were common. HTML plus up to six linked stylesheets per page,
      into the ignored .calibration/design/.
  python scripts/calibrate_design.py run
      Scan every usable page; pages whose archived HTML is nearly empty (client-rendered apps) are
      counted and left out.
  python scripts/calibrate_design.py sample RULE [--n 8] [--seed S]
      Print hits of RULE drawn across both sides, with context, for the judging pass (ADR 0011).
  python scripts/calibrate_design.py report
      Tiers -> designscan-calibration.json and docs/research/2026-11-design-calibration-results.md.

Method (ADR 0011, after ADR 0010): a reflex is a default rather than an authorship signal, so a rule's
tier comes from judged precision, the share of sampled hits that are real. `reflex` and `chosen`
verdicts count as real (the rule found the pattern it names); only `fp` counts against. Rates on human
and AI-era pages, and slop-cop's page labels, are reported as context: a page label says a pattern is
somewhere on the page, never that a given hit is real.
"""
import argparse
import concurrent.futures
import io
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calibrate  # noqa: E402  (wilson)

WORK = os.path.join(ROOT, ".calibration", "design")
SCANS = os.path.join(WORK, "scans.jsonl")
SCANNER = os.path.join(ROOT, "skills", "ai-slop-design", "scripts")
OUT_JSON = os.path.join(SCANNER, "designscan-calibration.json")
OUT_NOTE = os.path.join(ROOT, "docs", "research", "2026-11-design-calibration-results.md")
sys.path.insert(0, SCANNER)

LABELS_URL = "https://raw.githubusercontent.com/AdrianKrebs/design-slop-cop/main/dataset/labels.jsonl"
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"
HUMAN_TIMESTAMP = "20210601"
HUMAN_RANKS = (1000, 100000)
UA = {"User-Agent": "supah-skills-calibration/1.0"}
MAX_CSS, MAX_BYTES = 6, 3 * 1024 * 1024
# a snapshot counts only inside its side's years: human pages before generated sites, AI-era pages near the labels
YEARS = {"human": (1996, 2021), "ai": (2025, 2100)}


def in_window(side, ts):
    lo, hi = YEARS[side]
    return lo <= int(ts[:4]) <= hi

# slop-cop label -> the designscan rules that look for the same thing (partial: slop-cop renders pages)
LABEL_RULES = {
    "gradients": {"purple-gradient"},
    "purple_accent": {"purple-gradient", "stock-swatch"},
    "slop_fonts": {"reflex-font"},
    "glassmorphism": {"glass-card"},
    "accent_stripe": {"accent-stripe"},
    "colored_glows": {"coloured-glow"},
    "icon_card_grid": {"icon-card-grid"},
    "numbered_steps": {"numbered-markers"},
    "stat_banner_row": {"stat-banner"},
    "shadcn_signature": {"shadcn-card"},
    "hero_eyebrow_pill": {"eyebrow"},
    "all_caps_headings": {"eyebrow", "tracked-caps"},
    "sidebar_emoji": {"emoji-icon"},
}


def get(url, tries=4, limit=MAX_BYTES):
    err = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read(limit)
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410):
                return None
            err = e
        except Exception as e:  # archive.org drops connections under load
            err = e
        time.sleep(4 * (attempt + 1))
    print("  failed %s: %s" % (url, err), file=sys.stderr)
    return None


def snapshot(url, timestamp):
    """(timestamp, original url) of the Wayback snapshot closest to timestamp, or None."""
    data = get("https://archive.org/wayback/available?" + urllib.parse.urlencode({"url": url, "timestamp": timestamp}))
    try:
        closest = json.loads(data or b"{}").get("archived_snapshots", {}).get("closest") or {}
    except ValueError:
        return None
    if closest.get("available") and str(closest.get("status", "200")).startswith("2"):
        m = re.match(r"https?://web\.archive\.org/web/(\d+)/(.*)", closest["url"])
        if m:
            return m.group(1), m.group(2)
    return None


def raw(ts, url):
    return "https://web.archive.org/web/%sid_/%s" % (ts, url)


def save_page(side, slug, url, timestamp, meta):
    target = os.path.join(WORK, side, re.sub(r"[^\w.-]", "_", slug))
    if os.path.exists(os.path.join(target, "meta.json")):
        return True
    snap = snapshot(url, timestamp)
    if not snap:
        return False
    ts, original = snap
    if not in_window(side, ts):
        return False
    html = get(raw(ts, original))
    if not html:
        return False
    os.makedirs(target, exist_ok=True)
    text = html.decode("utf-8", errors="replace")
    with open(os.path.join(target, "page.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    sheets = []
    for m in re.finditer(r"<link\b[^>]*>", text, re.I):
        tag = m.group(0)
        href = re.search(r"""href\s*=\s*["']?([^"'\s>]+)""", tag, re.I)
        if href and re.search(r"""rel\s*=\s*["']?[^"'>]*stylesheet""", tag, re.I) and len(sheets) < MAX_CSS:
            css = get(raw(ts, urllib.parse.urljoin(original, href.group(1))))
            if css:
                name = "css-%d.css" % len(sheets)
                with open(os.path.join(target, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write(css.decode("utf-8", errors="replace"))
                sheets.append(name)
    meta.update({"url": url, "snapshot": ts, "css": sheets})
    with open(os.path.join(target, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    return True


def labelled_sites():
    latest = {}
    for line in (get(LABELS_URL) or b"").decode("utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            latest[d["slug"]] = d  # append-only: the latest record per slug wins
    return list(latest.values())


def human_domains(n, seed=7):
    data = get(TRANCO_URL, limit=64 * 1024 * 1024)
    if not data:
        sys.exit("could not download the Tranco list from %s" % TRANCO_URL)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        rows = z.read(z.namelist()[0]).decode("utf-8").splitlines()
    lo, hi = HUMAN_RANKS
    pool = [r.split(",")[1] for r in rows[lo:hi]]
    random.Random(seed).shuffle(pool)
    return pool[:n]


def cmd_fetch(args):
    os.makedirs(WORK, exist_ok=True)
    jobs = []
    for d in labelled_sites():
        stamp = d.get("timestamp", "2026-04-25")[:10].replace("-", "")
        jobs.append(("ai", d["slug"], d["url"], stamp, {"labels": d["labels"], "source": "design-slop-cop"}))
    for domain in human_domains(args.human * 3):
        jobs.append(("human", domain, "https://%s/" % domain, HUMAN_TIMESTAMP, {"labels": {}, "source": "tranco-2021"}))
    saved = {"ai": 0, "human": 0}
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        futures = {}
        for job in jobs:
            futures[pool.submit(save_page, *job)] = job
        for fut in concurrent.futures.as_completed(futures):
            side = futures[fut][0]
            if fut.result():
                saved[side] += 1
            if saved["human"] >= args.human:
                for other in futures:
                    if futures[other][0] == "human":
                        other.cancel()
    print("fetch: %d AI-era pages, %d human pages in %s" % (saved["ai"], saved["human"], WORK))


def usable(html, sheets):
    """Archived HTML with styling to read: enough class attributes or stylesheet text."""
    return len(html) >= 2000 and (len(re.findall(r"\bclass\s*=", html)) >= 10 or sum(map(len, sheets)) >= 1000)


def cmd_run(args):
    import designscan
    os.environ["SUPAH_DESIGN_NO_CALIBRATION"] = "1"
    out_rows = 0
    with open(SCANS, "w", encoding="utf-8") as out:
        for side in ("ai", "human"):
            base = os.path.join(WORK, side)
            for slug in sorted(os.listdir(base)) if os.path.isdir(base) else []:
                folder = os.path.join(base, slug)
                if not os.path.exists(os.path.join(folder, "meta.json")):
                    continue
                with open(os.path.join(folder, "meta.json"), encoding="utf-8") as f:
                    meta = json.load(f)
                files = [("page.html", designscan.read(os.path.join(folder, "page.html")))]
                files += [(n, designscan.read(os.path.join(folder, n))) for n in meta.get("css", [])]
                ok = usable(files[0][1], [t for _, t in files[1:]]) and in_window(side, meta.get("snapshot", "0"))
                counts, hits = {}, []
                if ok:
                    for name, text in files:
                        for h in designscan.scan_text(text, name)["hits"]:
                            counts[h["rule"]] = counts.get(h["rule"], 0) + 1
                            hits.append({"file": name, "line": h["line"], "rule": h["rule"], "match": h["match"],
                                         "context": h["context"]})
                out.write(json.dumps({"id": "%s/%s" % (side, slug), "side": side, "usable": ok,
                                      "labels": meta.get("labels", {}), "rules": counts, "hits": hits[:400]}) + "\n")
                out_rows += 1
    print("scanned %d pages -> %s" % (out_rows, SCANS))


def load_scans():
    with open(SCANS, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def cmd_sample(args):
    pool = [(d["id"], h) for d in load_scans() if d["usable"] for h in d["hits"] if h["rule"] == args.rule]
    rng = random.Random(args.seed)
    rng.shuffle(pool)
    # one hit per page first, so a single page cannot fill the sample
    seen, picked = set(), []
    for doc, h in pool:
        if doc not in seen:
            seen.add(doc)
            picked.append((doc, h))
    picked += [p for p in pool if p not in picked]
    for doc, h in picked[:args.n]:
        print("%s %s:%d\n  match:   %s\n  context: %s\n" % (doc, h["file"], h["line"], h["match"], h["context"]))
    print("%d hits of %s across %d pages" % (len(pool), args.rule, len(seen)))


# Hits judged by reading them in context, drawn with `sample` (date the batch): (real, judged).
# `reflex` and `chosen` are real; `fp` is not. Add verdicts here and rerun `report`.
#
# 2026-11-15, judged by the model that wrote the scanner (offer a human audit of these samples):
# - purple-gradient: one fp, a rainbow shimmer with a single purple stop.
# - accent-stripe and low-contrast: the first sample found fps (a `--*-border-left-width` custom property;
#   `color` on social icons and on <hr>); the rules were fixed and a fresh sample (seed 2) judged.
# - placeholder-name and placeholder-phone: every hit in the corpus judged, too few for a tier.
# - eyebrow: one fp, a `cva` badge string in a script bundle rather than an element.
# - glued-arrow: the first sample found arrows drawing a flow ("→ observation →"); the rule was fixed
#   and a fresh sample (seed 2) judged.
#
# 2026-11-18, judged by the model that changed the rule (issue #50):
# - low-contrast now reads Tailwind arbitrary values (`text-[#0D9488] bg-[#CCFBF1]`). The run added 2 hits,
#   both judged real (12px teal on mint 3.3:1, 15px white on teal 3.7:1); a fresh default sample (seed 1)
#   judged 7 of 8 real, the fp a styled-components chip whose `color` equals its background (no text).
PRECISION = {
    "purple-gradient": (7, 8), "gradient-text": (8, 8), "accent-stripe": (8, 8), "faux-chrome": (8, 8),
    "emoji-icon": (8, 8), "transition-all": (8, 8), "low-contrast": (17, 18), "dead-link": (8, 8),
    "missing-viewport": (8, 8), "placeholder-name": (4, 4), "placeholder-phone": (1, 1),
    "eyebrow": (7, 8), "middot-meta": (8, 8), "glued-arrow": (8, 8),
}
S_PRECISION, M_PRECISION, MIN_JUDGED_S, MIN_JUDGED_M = 0.9, 0.7, 8, 8


def precision_tier(real, judged, designed):
    if judged < MIN_JUDGED_M:  # ADR 0011: no rule ships at S or M unmeasured
        return "W"
    share = real / judged
    return "S" if share >= S_PRECISION and judged >= MIN_JUDGED_S else "M" if share >= M_PRECISION else "W"


def pct(k, n):
    return "%d/%d (%.1f%%)" % (k, n, 100.0 * k / n) if n else "n/a"


def agreement(pages, rule):
    """For every slop-cop label mapped to rule: (present pages hit, present pages, absent pages hit, absent pages)."""
    out = {}
    for label, rules in LABEL_RULES.items():
        if rule not in rules:
            continue
        present = [d for d in pages if d["labels"].get(label) == "present"]
        absent = [d for d in pages if d["labels"].get(label) == "not_present"]
        hit = lambda d: any(d["rules"].get(r) for r in rules)  # noqa: E731
        out[label] = (sum(map(hit, present)), len(present), sum(map(hit, absent)), len(absent))
    return out


def cmd_report(args):
    import designscan
    scans = load_scans()
    pages = [d for d in scans if d["usable"]]
    ai = [d for d in pages if d["side"] == "ai"]
    human = [d for d in pages if d["side"] == "human"]
    sizes = {"ai_fetched": sum(d["side"] == "ai" for d in scans), "ai_usable": len(ai),
             "human_fetched": sum(d["side"] == "human" for d in scans), "human_usable": len(human)}
    rules_out, rows = {}, []
    for rule, (cat, designed, _) in designscan.RULES.items():
        h = sum(1 for d in human if d["rules"].get(rule))
        a = sum(1 for d in ai if d["rules"].get(rule))
        _, h_up = calibrate.wilson(h, len(human))
        real, judged = PRECISION.get(rule, (0, 0))
        tier = precision_tier(real, judged, designed)
        agree = agreement(ai, rule)
        rules_out[rule] = {"tier": tier, "designed": designed, "precision": [real, judged],
                           "human_rate": round(h / max(1, len(human)), 4), "human_upper": round(h_up, 4),
                           "ai_rate": round(a / max(1, len(ai)), 4),
                           "labels": {k: list(v) for k, v in agree.items()}}
        rows.append((rule, cat, designed, h, len(human), a, len(ai), agree, real, judged, tier))
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"method": "ADR 0011: tier from judged precision; rates and slop-cop label agreement are context",
                   "sizes": sizes, "rules": rules_out}, f, indent=1)
        f.write("\n")
    write_note(rows, sizes)
    print("wrote %s and %s" % (OUT_JSON, OUT_NOTE))


def write_note(rows, sizes):
    lines = [
        "# Design scanner calibration results", "",
        "Generated by `python scripts/calibrate_design.py report`. AI-era pages: the sites labelled by "
        "design-slop-cop (Show HN launches, labels dated April 2026), read from the Wayback Machine snapshot "
        "closest to each label. Human pages: a seeded sample of Tranco-listed domains (ranks %d to %d) as "
        "archived in June 2021. Each page is its archived HTML plus up to %d linked stylesheets; pages whose "
        "HTML is nearly empty, mostly client-rendered apps, are left out." % (HUMAN_RANKS[0], HUMAN_RANKS[1], MAX_CSS),
        "",
        "AI-era: %d fetched, %d usable. Human: %d fetched, %d usable." % (
            sizes["ai_fetched"], sizes["ai_usable"], sizes["human_fetched"], sizes["human_usable"]), "",
        "The shipped tier comes from judged precision (ADR 0011): S needs %d%% of at least %d judged hits, M %d%% "
        "of at least %d; a rule with fewer judged hits ships at W, whatever its designed tier. Page rates say how often a pattern "
        "turns up, not whether a hit is real. Label agreement reads slop-cop's labels for the AI-era pages: "
        "*present* is the share of pages labelled present where the rule fired, *absent* the share of pages "
        "labelled absent where it fired anyway." % (100 * S_PRECISION, MIN_JUDGED_S, 100 * M_PRECISION, MIN_JUDGED_M),
        "",
        "| rule | category | designed | human pages | AI-era pages | label agreement | precision | shipped |",
        "|---|---|---|---|---|---|---|---|"]
    for rule, cat, designed, h, nh, a, na, agree, real, judged, tier in rows:
        labels = "; ".join("%s: present %s, absent %s" % (k, pct(p, np_), pct(q, nq))
                           for k, (p, np_, q, nq) in agree.items()) or "no label"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            rule, cat, designed, pct(h, nh), pct(a, na), labels,
            "%d/%d" % (real, judged) if judged else "none judged", tier))
    with open(OUT_NOTE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--human", type=int, default=200, help="usable human pages to collect")
    f.add_argument("--jobs", type=int, default=4)
    sub.add_parser("run")
    s = sub.add_parser("sample")
    s.add_argument("rule")
    s.add_argument("--n", type=int, default=8)
    s.add_argument("--seed", type=int, default=1)
    sub.add_parser("report")
    a = p.parse_args()
    {"fetch": cmd_fetch, "run": cmd_run, "sample": cmd_sample, "report": cmd_report}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
