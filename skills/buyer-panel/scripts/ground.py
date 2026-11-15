"""Real results against the panel's prediction, and the corrected figure later rounds show (GROUND.md). Stdlib only."""
import os

from records import REAL_TESTS, RecordErrors, load, load_round, problem, validate_file, write_jsonl
from tally import discounted_count, summary


def ground(path, panel, weights):
    """Compare one real-results file with the round it tested and store the ratio; returns the grounding line."""
    rec = load(path, "real", "a real/<label>.json file")["data"]
    panel = panel or os.path.join(os.path.dirname(os.path.abspath(path)), os.pardir)
    round_dir = os.path.join(panel, "rounds", rec["round"])
    if not os.path.isdir(round_dir):
        raise RecordErrors([problem(path, 0, "round", f"no round {rec['round']} in {panel}")])
    rnd = load_round(round_dir)
    meta = rnd.meta
    for field in ("price", "currency"):
        if rec[field] != meta[field]:
            raise RecordErrors([problem(path, 0, field, (
                f"the real test used {rec[field]}, round {rec['round']} showed {meta[field]}: "
                "ground against a round with the offer and price tested"))])
    result = summary(rnd, weights)
    expected = discounted_count(result["rows"], weights)
    if not expected:
        raise RecordErrors([problem(path, 0, "round", (
            f"round {rec['round']} predicts no buyer, so there is nothing to compare the real result with"))])
    reached_field, acted_field, measure = REAL_TESTS[rec["test"]]
    reached, acted = rec[reached_field], rec[acted_field]
    s = result["buy_share"]
    grounding = {
        "label": rec["label"], "test": rec["test"], "round": rec["round"], "date": rec["date"],
        "source": rec["source"], "offer": meta["offer"], "price": meta["price"], "currency": meta["currency"],
        "real": {"reached": reached, "acted": acted, "rate": round(acted / reached, 4), "measure": measure},
        "predicted": {"buyers": s["buyers"], "buy": s["buy"], "raw": s["raw"], "discounted": s["discounted"],
                      "weights": weights},
        "ratio": round((acted / reached) / (expected / s["buyers"]), 4),
    }
    ledger = os.path.join(panel, "grounding.jsonl")
    kept = load(ledger, "grounding", "a grounding.jsonl file")["data"] if os.path.exists(ledger) else []
    if any(g["label"] == grounding["label"] for g in kept):
        kept = [grounding if g["label"] == grounding["label"] else g for g in kept]
    else:
        kept.append(grounding)
    write_jsonl(ledger, kept)
    return grounding


def latest_grounding(round_dir):
    """The grounding line with the latest test date (a tie goes to the line written later), or None."""
    ledger = os.path.normpath(os.path.join(round_dir, os.pardir, os.pardir, "grounding.jsonl"))
    if not os.path.exists(ledger):
        return None
    latest = None
    for g in load(ledger, "grounding", "a grounding.jsonl file")["data"]:
        if latest is None or g["date"] >= latest["date"]:
            latest = g
    return latest


def corrected_figure(round_dir, rows, weights):
    """The latest grounding applied to these rows, or None without one."""
    latest = latest_grounding(round_dir)
    if latest is None:
        return None
    m = latest["real"]
    out = {"figure": None, "ratio": latest["ratio"], "grounding": latest["label"], "test": latest["test"],
           "round": latest["round"], "date": latest["date"], "reached": m["reached"], "acted": m["acted"],
           "measure": m["measure"]}
    grounded_on = latest["predicted"]["weights"]
    if grounded_on["by_intent"] != weights["by_intent"]:
        out["problem"] = (f"the ratio was computed on {grounded_on.get('scheme', 'other weights')}, "
                          f"this round uses {weights['scheme']}")
    elif rows:
        out["figure"] = round(latest["ratio"] * discounted_count(rows, weights) / len(rows), 4)
    return out
