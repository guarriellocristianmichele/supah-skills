"""Verdict learning for the prose, design and code scanners. Stdlib only.

One source, skills/ai-slop-prose/scripts/learn.py; release.py --sync copies it next to
designscan.py and codescan.py, and each scanner calls configure() with its store name.

Every reviewed hit becomes a verdict: `tell` (rewritten), `kept` (a real tell kept for a
reason) or `fp` (not a tell). Verdicts are appended to a log in the user's config folder,
and `rebuild()` turns the log into model.json:

- per rule and language, a Beta-Binomial posterior on precision with discounted counts
  (gamma = 0.99) and an empirical-Bayes prior per tier; a rule is demoted only after
  MIN_VERDICTS verdicts and when P(precision < target) > 0.95, promoted back when the
  95% lower bound clears the higher tier's target (see docs/research/2026-11-false-positive-control.md);
- exact-context suppressions: a (rule, match, context) seen as `fp` at least twice and never
  as a tell;
- a multinomial naive Bayes suppressor per category, trained only once a category has
  NB_MIN labelled hits with at least NB_MIN_CLASS per class. It can only suppress.

Human verdicts (source `human`) override model verdicts for the same context.
"""
import hashlib
import json
import math
import os
import random
import re
import sys
import time

GAMMA = 0.99
MIN_VERDICTS = 30
CONFIDENCE = 0.95
TARGETS = {"S": 0.95, "M": 0.75, "W": 0.50}
FALLBACK_PRIOR = {"S": (9.0, 1.0), "M": (3.0, 1.0), "W": (1.0, 1.0)}
PRIOR_CAP = 10.0
ORDER = ["S", "M", "W", "off"]
NB_MIN, NB_MIN_CLASS, NB_SUPPRESS = 200, 30, 0.90
CONTEXT_FP_MIN = 2
FIELDS = ["time", "lang", "rule", "category", "tier", "label", "reason", "source", "match", "context"]
NO_LANG = "-"  # scanners whose rules do not depend on a language
STORE = {"name": "prose"}


def configure(name):
    """Select the scanner (prose, design, code) whose verdicts and model this module reads and writes."""
    STORE["name"] = name


def store_dir():
    env = "SUPAH_%s_HOME" % STORE["name"].upper()
    if os.environ.get(env):
        return os.environ[env]
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        base = os.environ["APPDATA"]
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "supah-skills", STORE["name"])


def paths():
    d = store_dir()
    return os.path.join(d, "verdicts.tsv"), os.path.join(d, "model.json")


def clean(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def context_key(rule, lang, match, context):
    raw = "\x1f".join((rule, lang, clean(match), clean(context)))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def tokens(context):
    return re.findall(r"[^\W\d_]+|[^\w\s]", context.lower())


# --- exact regularised incomplete beta (Numerical Recipes, continued fraction) ---

def _betacf(a, b, x):
    tiny = 1e-30

    def nz(v):
        return v if abs(v) > tiny else tiny

    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 / nz(1.0 - qab * x / qap)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 / nz(1.0 + aa * d)
        c = nz(1.0 + aa / c)
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 / nz(1.0 + aa * d)
        c = nz(1.0 + aa / c)
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-12:
            break
    return h


def beta_cdf(x, a, b):
    """P(X <= x) for X ~ Beta(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def beta_quantile(q, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if beta_cdf(mid, a, b) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --- verdict log ---

def header():
    """The log's own columns: a scanner's log may carry more (design's `file`) or fewer (no `lang`)."""
    log, _ = paths()
    if os.path.exists(log):
        with open(log, encoding="utf-8") as f:
            first = f.readline().rstrip("\n")
        if first:
            return first.split("\t")
    return None


def record(rows, fields=FIELDS):
    """Append verdicts in the log's columns; `fields` names them when the log is new."""
    log, _ = paths()
    os.makedirs(os.path.dirname(log), exist_ok=True)
    columns = header()
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        if columns is None:
            columns = fields
            f.write("\t".join(columns) + "\n")
        for row in rows:
            row = dict(row, time=row.get("time") or time.strftime("%Y-%m-%dT%H:%M:%S"))
            f.write("\t".join(clean(str(row.get(k, ""))) if k in ("match", "context")
                              else str(row.get(k, "")).replace("\t", " ") for k in columns) + "\n")


def read_log():
    log, _ = paths()
    if not os.path.exists(log):
        return []
    with open(log, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines:
        return []
    columns = lines[0].split("\t")
    rows = [dict(zip(columns, l.split("\t"))) for l in lines[1:] if l.strip()]
    for r in rows:
        for k in FIELDS:
            r.setdefault(k, "")
        r["lang"] = r["lang"] or NO_LANG
    return rows


def run_id(*texts):
    """A short id for one recorded run (a sweep's before and after), kept in each row's reason so the
    same run recorded again adds nothing."""
    return hashlib.sha1("\x1e".join(texts).encode("utf-8")).hexdigest()[:12]


def recorded(key):
    """The keys of the rows already in the log, as key(row) computes them."""
    return {key(r) for r in read_log()}


def effective_verdicts(rows):
    """Human verdicts override model verdicts for the same context, whatever their order."""
    human = {}
    for r in rows:
        if r["source"] == "human":
            human[context_key(r["rule"], r["lang"], r["match"], r["context"])] = r["label"]
    out = []
    for r in rows:
        k = context_key(r["rule"], r["lang"], r["match"], r["context"])
        if r["source"] != "human" and k in human:
            continue
        out.append(r)
    return out


# --- model ---

def kind(label):
    """tell, kept or fp, whatever a scanner calls its labels (design: reflex, chosen, fp)."""
    if label == "fp":
        return "fp"
    return "kept" if label in ("kept", "chosen") else "tell"


def _prior(tier, precisions):
    if len(precisions) >= 3:
        m = sum(precisions) / len(precisions)
        v = sum((p - m) ** 2 for p in precisions) / (len(precisions) - 1)
        if 0 < m < 1 and v > 0:
            strength = min(PRIOR_CAP, max(2.0, m * (1 - m) / v - 1))
            return m * strength, (1 - m) * strength
    return FALLBACK_PRIOR.get(tier, (1.0, 1.0))


def _decide(base, a, b, n):
    tier = base
    if n < MIN_VERDICTS:
        return tier
    while tier != "off" and beta_cdf(TARGETS[tier], a, b) > CONFIDENCE:
        tier = ORDER[ORDER.index(tier) + 1]
    return tier


def rebuild():
    rows = effective_verdicts(read_log())
    stats = {}
    for r in rows:
        key = f"{r['rule']}/{r['lang']}"
        s = stats.setdefault(key, {"rule": r["rule"], "lang": r["lang"], "tier": r["tier"],
                                   "category": r["category"], "tp": 0.0, "fp": 0.0, "n": 0, "human": 0,
                                   "counts": {"tell": 0, "kept": 0, "fp": 0}})
        good = r["label"] != "fp"
        s["tp"] = GAMMA * s["tp"] + good
        s["fp"] = GAMMA * s["fp"] + (not good)
        s["n"] += 1
        s["human"] += r["source"] == "human"
        s["counts"][kind(r["label"])] += 1
    by_tier = {}
    for s in stats.values():
        if s["n"] >= 10:
            by_tier.setdefault(s["tier"], []).append(s["tp"] / (s["tp"] + s["fp"]))
    rules = {}
    for key, s in stats.items():
        a0, b0 = _prior(s["tier"], by_tier.get(s["tier"], []))
        a, b = a0 + s["tp"], b0 + s["fp"]
        rules[key] = {
            "base": s["tier"], "tier": _decide(s["tier"], a, b, s["n"]), "n": s["n"],
            "human": s["human"], "counts": s["counts"],
            "leaning": _decide(s["tier"], a, b, MIN_VERDICTS),  # the tier the evidence points to so far
            "alpha": round(a, 4), "beta": round(b, 4), "mean": round(a / (a + b), 4),
            "lower95": round(beta_quantile(1 - CONFIDENCE, a, b), 4),
        }

    contexts = {}
    for r in rows:
        k = context_key(r["rule"], r["lang"], r["match"], r["context"])
        c = contexts.setdefault(k, [0, 0])
        c[0 if r["label"] == "fp" else 1] += 1
    suppress = sorted(k for k, (fp, good) in contexts.items() if fp >= CONTEXT_FP_MIN and good == 0)

    nb = {}
    for r in rows:
        cat = nb.setdefault(f"{r['category']}/{r['lang']}", {"fp": {}, "ok": {}, "docs": {"fp": 0, "ok": 0}})
        cls = "fp" if r["label"] == "fp" else "ok"
        cat["docs"][cls] += 1
        for t in tokens(r["context"]):
            cat[cls][t] = cat[cls].get(t, 0) + 1
    nb = {k: v for k, v in nb.items()
          if sum(v["docs"].values()) >= NB_MIN and min(v["docs"].values()) >= NB_MIN_CLASS}

    model = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "verdicts": len(rows),
             "rules": rules, "suppress": suppress, "nb": nb}
    _, path = paths()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
    return model


def progress(model, keys, audit_command):
    """One line per rule/lang key: how far it is from the minimum, its precision so far and tier.
    A tier change resting on model verdicts alone asks for a human audit first."""
    lines = []
    for key in keys:
        r = model.get("rules", {}).get(key)
        if not r:
            lines.append(f"{key}: 0/{MIN_VERDICTS} verdicts")
            continue
        count = f"{r['n']}/{MIN_VERDICTS}" if r["n"] < MIN_VERDICTS else str(r["n"])
        tier = r["tier"] if r["tier"] == r["base"] else f"{r['tier']} (was {r['base']})"
        line = f"{key}: {count} verdicts, precision so far {r['mean']:.2f}, tier {tier}"
        if not r.get("human") and r.get("leaning", r["base"]) != r["base"]:
            line += f"; it leans to {r['leaning']} on model verdicts alone: run `{audit_command}` to check a sample"
        lines.append(line)
    return lines


def export(model):
    """Per-rule aggregates for the maintainer's recalibration: counts and estimates, never a match or a context."""
    rules = []
    for key, r in sorted(model.get("rules", {}).items()):
        rule, _, lang = key.rpartition("/")
        rules.append({"rule": rule, "lang": lang, "base": r["base"], "tier": r["tier"], "verdicts": r["n"],
                      "tell": r["counts"]["tell"], "kept": r["counts"]["kept"], "fp": r["counts"]["fp"],
                      "human": r["human"], "precision": r["mean"], "lower95": r["lower95"]})
    return {"store": STORE["name"], "built": model.get("built"), "rules": rules}


def load_model():
    _, path = paths()
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def nb_fp_probability(model, category, lang, context):
    cat = (model or {}).get("nb", {}).get(f"{category}/{lang}")
    if not cat:
        return None
    vocab = set(cat["fp"]) | set(cat["ok"])
    total = {c: sum(cat[c].values()) for c in ("fp", "ok")}
    docs = cat["docs"]
    score = {}
    for c in ("fp", "ok"):
        s = math.log(docs[c] / (docs["fp"] + docs["ok"]))
        for t in tokens(context):
            s += math.log((cat[c].get(t, 0) + 1) / (total[c] + len(vocab)))
        score[c] = s
    m = max(score.values())
    return math.exp(score["fp"] - m) / sum(math.exp(v - m) for v in score.values())


def apply(model, hit, lang):
    """Return (tier, kept_reason) for a hit after learning. Never raises a hit's tier above its base."""
    if not model:
        return hit["tier"], None
    if context_key(hit["rule"], lang, hit["match"], hit["context"]) in set(model.get("suppress", [])):
        return hit["tier"], "learned:context"
    p = nb_fp_probability(model, hit["category"], lang, hit["context"])
    if p is not None and p > NB_SUPPRESS:
        return hit["tier"], f"learned:nb {p:.2f}"
    r = model.get("rules", {}).get(f"{hit['rule']}/{lang}")
    if not r or r["tier"] == r["base"]:
        return hit["tier"], None
    # demoted: still show it now and then (Thompson sample, deterministic per hit) so it can recover
    seed = int(hashlib.sha1(f"{hit['rule']}{hit['match']}{hit['line']}".encode()).hexdigest()[:8], 16)
    theta = random.Random(seed).betavariate(r["alpha"], r["beta"])
    if theta > TARGETS[r["base"]]:
        return hit["tier"], None
    if r["tier"] == "off":
        return "W", "learned:rule-off"
    return r["tier"], None


def audit_sample(fraction=0.1, seed=None):
    rows = [r for r in effective_verdicts(read_log()) if r["label"] == "fp" and r["source"] != "human"]
    rng = random.Random(seed)
    k = max(1, math.ceil(len(rows) * fraction)) if rows else 0
    return rng.sample(rows, k)


# --- commands every scanner shares: <scanner> learn | audit | label FILE | export [--out FILE] ---

def cmd_learn(argv, prog):
    """Rebuild the model from the verdict log and print per-rule precision."""
    import argparse
    argparse.ArgumentParser(prog=f"{prog} learn").parse_args(argv)
    model = rebuild()
    print(f"{model['verdicts']} verdicts · {len(model['suppress'])} suppressed contexts · "
          f"{len(model['nb'])} trained context classifiers · {paths()[1]}\n")
    print("| rule/lang | verdicts | precision (mean) | 95% lower bound | tier |\n|---|---|---|---|---|")
    for key, r in sorted(model["rules"].items(), key=lambda kv: kv[1]["lower95"]):
        tier = r["tier"] if r["tier"] == r["base"] else f"{r['base']} -> {r['tier']}"
        print(f"| {key} | {r['n']} | {r['mean']:.2f} | {r['lower95']:.2f} | {tier} |")
    return 0


def cmd_audit(argv, prog):
    """Print a random sample of the model's fp verdicts as TSV for a human to confirm."""
    import argparse
    p = argparse.ArgumentParser(prog=f"{prog} audit")
    p.add_argument("--fraction", type=float, default=0.1)
    a = p.parse_args(argv)
    print(f"# Set label to fp (not what the rule names), kept, or tell, then: {prog} label <this file>")
    print("label\tlang\trule\tcategory\ttier\tmatch\tcontext")
    for r in audit_sample(a.fraction):
        print("\t".join([r["label"], r["lang"], r["rule"], r["category"], r["tier"], r["match"], r["context"]]))
    return 0


def cmd_label(argv, prog):
    """Record human verdicts from an edited audit file; they override model verdicts."""
    import argparse
    p = argparse.ArgumentParser(prog=f"{prog} label")
    p.add_argument("file")
    a = p.parse_args(argv)
    rows = []
    seen = recorded(lambda r: (context_key(r["rule"], r["lang"], r["match"], r["context"]), r["source"], r["label"]))
    with open(a.file, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if line.startswith("#") or parts[0] == "label" or len(parts) < 7:
                continue
            label, lang, rule, cat, tier, match, context = parts[:7]
            key = (context_key(rule, lang, match, context), "human", label)
            if label in ("fp", "kept", "tell") and key not in seen:
                seen.add(key)
                rows.append({"lang": lang, "rule": rule, "category": cat, "tier": tier, "label": label,
                             "reason": "audit", "source": "human", "match": match, "context": context})
    record(rows)
    rebuild()
    print(f"Recorded {len(rows)} human verdicts.")
    return 0


def cmd_export(argv, prog):
    """Write the per-rule aggregates to a file the user can read, then attach to an issue."""
    import argparse
    p = argparse.ArgumentParser(prog=f"{prog} export")
    p.add_argument("--out", default=os.path.join(store_dir(), f"supah-{STORE['name']}-learning.json"))
    a = p.parse_args(argv)
    text = json.dumps(export(rebuild()), ensure_ascii=False, indent=1)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nWrote {a.out}: rule names, tiers and counts only, no text from your files. Read it before "
          f"attaching it to an issue on guarriellocristianmichele/supah-skills.")
    return 0


COMMANDS = {"learn": cmd_learn, "audit": cmd_audit, "label": cmd_label, "export": cmd_export}
