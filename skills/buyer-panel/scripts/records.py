"""Record kinds of the panel ledger, their validation, and one round read and cross-checked (RECORDS.md).

Every kind has one entry in KINDS: its fields, whether a file holds one object or one record per line, the
fields that must be unique across lines, and its own checks. Stdlib only.
"""
import dataclasses
import datetime
import json
import os

TEXT, NUMBER, ANY_TEXT = "text", "number", "any text"
OFFER, NOTHING = "offer", "nothing"              # reserved option ids: the idea, and "buy nothing"
PRICE_ANSWERS = ("too_cheap", "cheap", "expensive", "too_expensive")
INTENTS = (1, 2, 3, 4, 5)
INTERVIEWS = ("orchestrate", "inline")   # fresh contexts in batches, or one buyer at a time in this context
# test.json: each metric, and what its share is taken of
METRICS = {"signups": "visits", "preorders": "visits", "commitments": "interviews"}
# real/<label>.json: what each real test counts (people reached, people who acted, what the rate measures)
REAL_TESTS = {
    "smoke-test": ("visits", "conversions", "conversions per visit"),
    "interviews": ("interviews", "commitments", "commitments per interview"),
    "pre-sale": ("asked", "paid", "payments per person asked"),
}


class UsageError(Exception):
    """Bad arguments: printed to stderr, exit 2."""


class RecordErrors(Exception):
    """Records that cannot be used: the command prints them and exits 3."""

    def __init__(self, errors):
        super().__init__(f"{len(errors)} record errors")
        self.errors = errors


def problem(file, line, field, text):
    """One record error, as every command reports it."""
    return {"file": file, "line": line, "field": field, "problem": text}


# ---------------------------------------------------------------- field checks

def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_count(v, least=1):
    return isinstance(v, int) and not isinstance(v, bool) and v >= least


def is_share(v):
    return is_number(v) and 0 <= v <= 1


def is_tag(v):
    """A reason tag: lowercase words joined by hyphens, so counts merge across buyers."""
    return isinstance(v, str) and bool(v) and all(part and part.isalnum() and part == part.lower()
                                                  for part in v.split("-"))


def iso_date(v):
    """A date written YYYY-MM-DD, or None: the length guard keeps 3.11's wider fromisoformat out (ADR 0009)."""
    try:
        return datetime.date.fromisoformat(v) if isinstance(v, str) and len(v) == 10 else None
    except ValueError:
        return None


def date_errors(rec, field):
    if field not in rec or not (isinstance(rec[field], str) and rec[field].strip()):
        return []                                       # missing or empty: the schema says so
    return [] if iso_date(rec[field]) else [(field, "must be a date as YYYY-MM-DD")]


def field_errors(record, schema):
    errors = []
    for field, kind in schema.items():
        if field not in record:
            errors.append((field, "missing"))
        elif kind == TEXT and not (isinstance(record[field], str) and record[field].strip()):
            errors.append((field, "must be non-empty text"))
        elif kind == ANY_TEXT and not isinstance(record[field], str):
            errors.append((field, "must be text"))
        elif kind == NUMBER and not (is_number(record[field]) and record[field] >= 0):
            errors.append((field, "must be a number of 0 or more"))
    return errors


def option_errors(options, field="options"):
    if not (isinstance(options, list) and options and all(isinstance(o, str) and o for o in options)):
        return [(field, "must list option ids")]
    if len(set(options)) != len(options) or OFFER not in options or NOTHING not in options:
        return [(field, f"must be distinct and include {OFFER!r} and {NOTHING!r}")]
    return []


# ---------------------------------------------------------------- each kind's own checks

def answer_errors(rec):
    errors = option_errors(rec.get("options"))
    options = rec.get("options") if not errors else []
    if options and isinstance(rec.get("choice"), str) and rec["choice"] not in options:
        errors.append(("choice", "is not one of the options shown"))
    if rec.get("choice") == OFFER and isinstance(rec.get("give_up"), str) and not rec["give_up"].strip():
        errors.append(("give_up", "a BUY must say what the buyer gives up to pay"))
    price = rec.get("price")
    if not isinstance(price, dict):
        errors.append(("price", "must hold the four Van Westendorp answers"))
    else:
        for name in PRICE_ANSWERS:
            if not (is_number(price.get(name)) and price[name] >= 0):
                errors.append((f"price.{name}", "missing" if name not in price else "must be a number of 0 or more"))
    return errors


def score_errors(rec):
    errors = []
    intent = rec.get("intent")
    if not (isinstance(intent, int) and not isinstance(intent, bool) and intent in INTENTS):
        errors.append(("intent", "must be a whole number from 1 to 5 (the anchor statements)"))
    if "reason" in rec and isinstance(rec["reason"], str) and rec["reason"].strip() and not is_tag(rec["reason"]):
        errors.append(("reason", "must be a tag such as already-paid"))
    return errors


def brief_errors(rec):
    alts = rec.get("alternatives")
    if not (isinstance(alts, list) and alts):
        return [("alternatives", "must list the real alternatives with their prices")]
    errors = []
    for i, alt in enumerate(alts):
        if not isinstance(alt, dict):
            errors.append((f"alternatives[{i}]", "must be an object with name and price"))
            continue
        errors += [(f"alternatives[{i}].{f}", m) for f, m in field_errors(alt, {"name": TEXT, "price": NUMBER})]
        if alt.get("name") in (OFFER, NOTHING):
            errors.append((f"alternatives[{i}].name", f"{alt['name']!r} is a reserved option id"))
    return errors


def plan_errors(rec):
    errors = [] if is_count(rec.get("size")) else [("size", "must be a whole number of buyers")]
    segments = rec.get("segments")
    if not (isinstance(segments, list) and segments and all(isinstance(x, dict) for x in segments)):
        return errors + [("segments", "must list segments with name, share and budget")]
    names = [x.get("name") for x in segments]
    if len(set(names)) != len(names):
        errors.append(("segments", "segment names must be distinct"))
    for i, seg in enumerate(segments):
        errors += [(f"segments[{i}].{f}", m) for f, m in field_errors(seg, {"name": TEXT})]
        if not (is_number(seg.get("share")) and seg["share"] > 0):
            errors.append((f"segments[{i}].share", "must be a number above 0"))
        budget = seg.get("budget")
        if not (isinstance(budget, list) and len(budget) == 2 and all(is_number(b) and b >= 0 for b in budget)
                and budget[0] <= budget[1]):
            errors.append((f"segments[{i}].budget", "must be [low, high] with low <= high"))
    shares = [x["share"] for x in segments if is_number(x.get("share"))]
    if len(shares) == len(segments) and abs(sum(shares) - 1) > 0.01:
        errors.append(("segments.share", f"shares add up to {sum(shares):g}, not 1"))
    return errors


def competitor_errors(rec):
    """round.json `competitor`: {name, price, was}: the competitor this round added (no `was`) or repriced
    (`was` is the price it had in the base round)."""
    c = rec.get("competitor")
    if c is None:
        return []
    if not isinstance(c, dict):
        return [("competitor", "must be {name, price} and, for a reprice, was")]
    errors = [(f"competitor.{f}", m) for f, m in field_errors(c, {"name": TEXT, "price": NUMBER})]
    if c.get("name") in (OFFER, NOTHING):
        errors.append(("competitor.name", f"{c['name']!r} is a reserved option id"))
    elif isinstance(c.get("name"), str) and isinstance(rec.get("options"), list) and c["name"] not in rec["options"]:
        errors.append(("competitor.name", f"{c['name']!r} is not one of the round's options"))
    if "was" in c and not (is_number(c["was"]) and c["was"] >= 0):
        errors.append(("competitor.was", "must be a number of 0 or more"))
    return errors


def round_errors(rec):
    errors = option_errors(rec.get("options"))
    if rec.get("interviews") not in INTERVIEWS:
        errors.append(("interviews", f"must be one of {', '.join(INTERVIEWS)}"))
    if not is_count(rec.get("batch_size")):
        errors.append(("batch_size", "must be a whole number of buyers per context (1 when inline)"))
    elif rec.get("interviews") == "inline" and rec["batch_size"] != 1:
        errors.append(("batch_size", "must be 1 when interviews are inline: one buyer at a time"))
    return errors + competitor_errors(rec)


def threshold_errors(thresholds):
    if not (isinstance(thresholds, dict) and thresholds):
        return [("thresholds", f"must set go and stop for one or more of {', '.join(METRICS)}")]
    errors = []
    for metric, t in thresholds.items():
        where = f"thresholds.{metric}"
        if metric not in METRICS:
            errors.append((where, f"unknown metric; use {', '.join(METRICS)}"))
            continue
        if not isinstance(t, dict):
            errors.append((where, "must be {go, stop}"))
            continue
        bad = [k for k in ("go", "stop") if not is_share(t.get(k))]
        errors += [(f"{where}.{k}", "missing" if k not in t else "must be a share from 0 to 1") for k in bad]
        if not bad and t["stop"] >= t["go"]:
            errors.append((where, f"stop {t['stop']:g} must be below go {t['go']:g}"))
    return errors


def test_errors(rec):
    """test.json: the real test's go and stop thresholds, written before the test runs (TEST.md)."""
    errors = threshold_errors(rec.get("thresholds"))
    thresholds = rec.get("thresholds") if isinstance(rec.get("thresholds"), dict) else {}
    sample = rec.get("sample")
    if not isinstance(sample, dict):
        errors.append(("sample", "must give the visits and interviews the test plans"))
        sample = {}
    for base in sorted({METRICS[m] for m in thresholds if m in METRICS}):
        if not is_count(sample.get(base)):
            errors.append((f"sample.{base}", "missing" if base not in sample else "must be a whole number above 0"))
    errors += date_errors(rec, "written") + date_errors(rec, "ends")
    written, ends = iso_date(rec.get("written")), iso_date(rec.get("ends"))
    if written and ends and ends < written:
        errors.append(("ends", "the test cannot end before its thresholds were written"))
    objections = rec.get("objections")
    if not (isinstance(objections, list) and objections and all(is_tag(o) for o in objections)):
        errors.append(("objections", "must list the reason tags the test probes, such as already-paid"))
    return errors


def real_errors(rec):
    errors = date_errors(rec, "date")
    if rec.get("test") not in REAL_TESTS:
        return errors + [("test", f"must be one of {', '.join(REAL_TESTS)}")]
    reached, acted, _ = REAL_TESTS[rec["test"]]
    if not is_count(rec.get(reached)):
        errors.append((reached, "must be a whole number of 1 or more"))
    if not is_count(rec.get(acted), 0):
        errors.append((acted, "must be a whole number of 0 or more"))
    elif is_count(rec.get(reached)) and rec[acted] > rec[reached]:
        errors.append((acted, f"is more than {reached}"))
    return errors


def grounding_errors(rec):
    errors = date_errors(rec, "date")
    measured = rec.get("real")
    if not (isinstance(measured, dict) and is_count(measured.get("reached")) and is_count(measured.get("acted"), 0)
            and isinstance(measured.get("measure"), str)):
        errors.append(("real", "must hold reached, acted and measure"))
    predicted = rec.get("predicted")
    by_intent = predicted.get("weights", {}).get("by_intent") if isinstance(predicted, dict) else None
    if not (isinstance(by_intent, dict) and sorted(by_intent) == ["1", "2", "3", "4", "5"]):
        errors.append(("predicted", "must hold the weights the ratio was computed with"))
    return errors


# ---------------------------------------------------------------- the registry

@dataclasses.dataclass(frozen=True)
class Kind:
    name: str
    fields: dict
    lines: bool = False          # one record per line (.jsonl) or one object (.json)
    key: tuple = ()              # fields whose values may not repeat across lines
    extra: object = None         # the kind's own checks: record -> [(field, problem)]
    folder: str = None           # files of this kind are any file in a folder of this name


KINDS = {k.name: k for k in (
    Kind("buyers", {"id": TEXT, "name": TEXT, "segment": TEXT, "budget": NUMBER, "currency": TEXT, "habits": TEXT,
                    "current_solution": TEXT, "last_spend": NUMBER, "objection": TEXT}, lines=True, key=("id",)),
    Kind("answers", {"buyer_id": TEXT, "round": TEXT, "reaction": TEXT, "choice": TEXT, "give_up": ANY_TEXT},
         lines=True, key=("buyer_id",), extra=answer_errors, folder="answers"),
    Kind("scores", {"buyer_id": TEXT, "round": TEXT, "reason": TEXT, "quote": TEXT}, lines=True, key=("buyer_id",),
         extra=score_errors),
    Kind("brief", {"idea": TEXT, "audience": TEXT, "price": NUMBER, "currency": TEXT}, extra=brief_errors),
    Kind("plan", {"currency": TEXT}, extra=plan_errors),
    Kind("round", {"label": TEXT, "offer": TEXT, "price": NUMBER, "currency": TEXT, "model": TEXT},
         extra=round_errors),
    Kind("test", {"round": TEXT, "written": TEXT, "ends": TEXT, "offer": TEXT, "price": NUMBER, "currency": TEXT},
         extra=test_errors),
    Kind("real", {"label": TEXT, "test": TEXT, "round": TEXT, "date": TEXT, "source": TEXT, "price": NUMBER,
                  "currency": TEXT}, extra=real_errors, folder="real"),
    # grounding.jsonl: one line per real test compared, written by `ground`, read for the corrected figure
    Kind("grounding", {"label": TEXT, "test": TEXT, "round": TEXT, "date": TEXT, "ratio": NUMBER}, lines=True,
         key=("label",), extra=grounding_errors),
)}


def kind_of(path):
    base, folder = os.path.basename(path), os.path.basename(os.path.dirname(path))
    for kind in KINDS.values():
        if kind.folder and folder == kind.folder and base.endswith(".jsonl" if kind.lines else ".json"):
            return kind
    stem = base.split(".")[0]
    return KINDS.get(stem)


def record_errors(kind, rec):
    return field_errors(rec, kind.fields) + (kind.extra(rec) if kind.extra else [])


# ---------------------------------------------------------------- files

def read_jsonl(path):
    """Yield (line number, record or None, parse error or None)."""
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as e:
                yield n, None, f"not JSON: {e.msg}"
                continue
            yield n, rec, None if isinstance(rec, dict) else "not a JSON object"


def read_json(path):
    """A JSON object from path, or None when it is missing, unreadable or not an object."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def validate_file(path):
    """{file, kind, records, errors, data, lines}; errors carry the file name."""
    kind = kind_of(path)
    if kind is None:
        return {"file": path, "kind": None, "records": 0, "data": None,
                "errors": [problem(path, 0, None, "unknown file name; see RECORDS.md")]}
    if not kind.lines:
        return validate_object(path, kind)
    errors, records, numbers, seen = [], [], [], set()
    for n, rec, parse_problem in read_jsonl(path):
        if parse_problem:
            errors.append(problem(path, n, None, parse_problem))
            continue
        records.append(rec)
        numbers.append(n)
        errors += [problem(path, n, field, msg) for field, msg in record_errors(kind, rec)]
        key = tuple(rec.get(k) for k in kind.key)
        if key in seen:
            errors.append(problem(path, n, kind.key[-1], f"duplicate {' '.join(map(str, key))}"))
        seen.add(key)
    return {"file": path, "kind": kind.name, "records": len(records), "errors": errors, "data": records,
            "lines": numbers}


def validate_object(path, kind):
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except json.JSONDecodeError as e:
        return {"file": path, "kind": kind.name, "records": 0, "data": None,
                "errors": [problem(path, e.lineno, None, f"not JSON: {e.msg}")]}
    if not isinstance(rec, dict):
        return {"file": path, "kind": kind.name, "records": 0, "data": None,
                "errors": [problem(path, 1, None, "not a JSON object")]}
    errors = [problem(path, 0, f, m) for f, m in record_errors(kind, rec)]
    return {"file": path, "kind": kind.name, "records": 1, "errors": errors, "data": rec}


def load(path, kind, what):
    """The data of one file that must be of `kind` and valid, or raise its errors."""
    checked = validate_file(path)
    if checked["kind"] != kind or checked["errors"]:
        raise RecordErrors(checked["errors"] or [problem(path, 0, None, f"not {what}")])
    return checked


def plan_fit_errors(path, buyers, numbers, plan):
    """Line-numbered errors for buyers outside the segment plan (unknown segment, budget out of range)."""
    ranges = {seg["name"]: seg["budget"] for seg in plan["segments"]}
    errors = []
    for n, rec in zip(numbers, buyers):
        seg = rec.get("segment")
        if isinstance(seg, str) and seg not in ranges:
            errors.append(problem(path, n, "segment", f"{seg!r} is not in the plan"))
        elif seg in ranges and is_number(rec.get("budget")):
            low, high = ranges[seg]
            if not low <= rec["budget"] <= high:
                errors.append(problem(path, n, "budget", f"{rec['budget']:g} is outside the plan's {low:g} to {high:g}"))
    return errors


# ---------------------------------------------------------------- one round

def normalise(text):
    return " ".join(text.lower().split())


@dataclasses.dataclass
class Round:
    """One round's records, cross-checked: round.json, the panel's buyers by id, answers and scores by buyer id."""
    dir: str
    meta: dict
    buyers: dict
    answers: dict
    scores: dict

    @property
    def label(self):
        return self.meta["label"]

    def rows(self):
        """One row per buyer answered and scored, in panel order: what every number is computed from."""
        rows = []
        for bid, buyer in self.buyers.items():
            if bid in self.answers and bid in self.scores:
                a, sc = self.answers[bid], self.scores[bid]
                rows.append({"buyer_id": bid, "name": buyer["name"], "segment": buyer["segment"],
                             "budget": buyer["budget"], "currency": buyer["currency"], "choice": a["choice"],
                             "decision": "BUY" if a["choice"] == OFFER else "PASS", "intent": sc["intent"],
                             "reason": sc["reason"], "quote": sc["quote"], "give_up": a["give_up"],
                             "price": a["price"], "options": a["options"]})
        return rows

    def missing(self):
        return {"answers": [b for b in self.buyers if b not in self.answers],
                "scores": [b for b in self.answers if b not in self.scores]}

    def described(self):
        return {k: self.meta[k] for k in ("label", "offer", "price", "currency", "model", "interviews", "batch_size")}


def panel_of(round_dir):
    """The panel folder a round folder sits in: P/rounds/<label>/ -> P."""
    return os.path.normpath(os.path.join(round_dir, os.pardir, os.pardir))


def load_round(round_dir, buyers_path=None):
    """Read and cross-check a round, or raise every record error found."""
    buyers_path = os.path.normpath(buyers_path or os.path.join(panel_of(round_dir), "buyers.jsonl"))
    files = [os.path.join(round_dir, "round.json"), buyers_path]
    missing = [problem(f, 0, None, "missing") for f in files if not os.path.exists(f)]
    if missing:
        raise RecordErrors(missing)
    if os.path.exists(os.path.join(round_dir, "answers.jsonl")):
        files.append(os.path.join(round_dir, "answers.jsonl"))
    batch_dir = os.path.join(round_dir, "answers")
    if os.path.isdir(batch_dir):
        files += [os.path.join(batch_dir, f) for f in sorted(os.listdir(batch_dir)) if f.endswith(".jsonl")]
    if os.path.exists(os.path.join(round_dir, "scores.jsonl")):
        files.append(os.path.join(round_dir, "scores.jsonl"))
    results = [validate_file(f) for f in files]
    errors = [e for r in results for e in r["errors"]]
    if errors:
        raise RecordErrors(errors)
    meta = results[0]["data"]
    buyers = {b["id"]: b for b in results[1]["data"]}
    answers, scores, where_scored = {}, {}, {}
    for r in results[2:]:
        into = answers if r["kind"] == "answers" else scores
        for n, rec in zip(r["lines"], r["data"]):
            bid = rec["buyer_id"]
            if bid not in buyers:
                errors.append(problem(r["file"], n, "buyer_id", f"unknown buyer {bid}"))
            elif bid in into:
                errors.append(problem(r["file"], n, "buyer_id", f"second record for {bid}"))
            if rec["round"] != meta["label"]:
                errors.append(problem(r["file"], n, "round", f"{rec['round']!r} is not this round's label"))
            if r["kind"] == "answers" and sorted(rec["options"]) != sorted(meta["options"]):
                errors.append(problem(r["file"], n, "options", "not the round's options"))
            into[bid] = rec
            if r["kind"] == "scores":
                where_scored[bid] = (r["file"], n)
    for bid, score in scores.items():
        answer = answers.get(bid)
        if answer and normalise(score["quote"]) not in normalise(answer["reaction"]):
            errors.append(problem(*where_scored[bid], "quote", f"{bid}'s quote is not in their reaction"))
    if errors:
        raise RecordErrors(errors)
    return Round(round_dir, meta, buyers, answers, scores)
