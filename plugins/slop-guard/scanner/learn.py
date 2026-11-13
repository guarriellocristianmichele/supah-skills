"""Verdict learning for scan.py. Stdlib only.

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


def store_dir():
    if os.environ.get("SUPAH_PROSE_HOME"):
        return os.environ["SUPAH_PROSE_HOME"]
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        base = os.environ["APPDATA"]
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "supah-skills", "prose")


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

def record(rows):
    log, _ = paths()
    os.makedirs(os.path.dirname(log), exist_ok=True)
    new = not os.path.exists(log)
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("\t".join(FIELDS) + "\n")
        for row in rows:
            row = dict(row, time=row.get("time") or time.strftime("%Y-%m-%dT%H:%M:%S"))
            f.write("\t".join(clean(str(row.get(k, ""))) if k in ("match", "context")
                              else str(row.get(k, "")).replace("\t", " ") for k in FIELDS) + "\n")


def read_log():
    log, _ = paths()
    if not os.path.exists(log):
        return []
    with open(log, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return [dict(zip(FIELDS, l.split("\t"))) for l in lines[1:] if l.strip()]


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
                                   "category": r["category"], "tp": 0.0, "fp": 0.0, "n": 0})
        good = r["label"] != "fp"
        s["tp"] = GAMMA * s["tp"] + good
        s["fp"] = GAMMA * s["fp"] + (not good)
        s["n"] += 1
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
