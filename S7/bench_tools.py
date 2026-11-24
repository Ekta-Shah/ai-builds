"""The measuring tools for the S7 benchmark. Students write the functions marked STAGE; no model key needed to test them."""
import math
import random
import re
import time

RETRYABLE = ("429", "503", "504", "RESOURCE_EXHAUSTED", "ResourceExhausted", "UNAVAILABLE", "DEADLINE_EXCEEDED", "ReadError", "ConnectError")


def passed(row, reply):
    """Given: a reply passes if every & part has one | alternative in it, and bad_if (a regex) does not match."""
    t = reply.lower()
    if row.get("bad_if") and re.search(row["bad_if"], t, re.I):
        return False
    return all(any(alt.strip().lower() in t for alt in must.split("|")) for must in row["must_have"].split("&"))


# STAGE 2
def backoff_call(fn, retries=4, base=2.0, sleep=time.sleep):
    """Call fn(). If it raises an error whose text contains a RETRYABLE marker, wait base*2**attempt seconds
    (plus up to 1 s of jitter) and try again, up to `retries` retries. Any other error, or the last failure, is raised."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == retries or not any(k in str(e) for k in RETRYABLE):
                raise
            sleep(base * 2 ** attempt + random.random())


# STAGE 3
def p95(values):
    """Nearest-rank 95th percentile: sort, take the value at position ceil(0.95 * n), counting from 1."""
    v = sorted(values)
    return v[math.ceil(0.95 * len(v)) - 1]


def cost_inr(in_tokens, out_tokens, price, usd_inr):
    """Rupees for one call. price = {"input_per_m": USD per million input tokens, "output_per_m": ...}."""
    usd = in_tokens * price["input_per_m"] / 1e6 + out_tokens * price["output_per_m"] / 1e6
    return usd * usd_inr


def bucket_scores(rows):
    """rows: dicts with "bucket" and "passed" (True/False). Return {bucket: share passed, 0 to 1}, plus "all"."""
    out = {}
    for b in {r["bucket"] for r in rows}:
        sel = [r["passed"] for r in rows if r["bucket"] == b]
        out[b] = sum(sel) / len(sel)
    out["all"] = sum(r["passed"] for r in rows) / len(rows)
    return out


# STAGE 4
def decide(results, rule):
    """results: {model: {"score", "holdout", "p95", "cost_per_1000"}}. rule: min_score, max_holdout_drop,
    max_p95_seconds, max_cost_per_1000_inr. Return (chosen, why) where why maps each model to the list of limits it broke.
    chosen = the cheapest model that breaks none (ties: the higher score); None if every model breaks something."""
    why = {}
    for m, r in results.items():
        broke = []
        if r["score"] < rule["min_score"]:
            broke.append("score")
        if r["score"] - r["holdout"] > rule["max_holdout_drop"]:
            broke.append("holdout")
        if r["p95"] > rule["max_p95_seconds"]:
            broke.append("p95")
        if r["cost_per_1000"] > rule["max_cost_per_1000_inr"]:
            broke.append("cost")
        why[m] = broke
    ok = [m for m in results if not why[m]]
    chosen = min(ok, key=lambda m: (results[m]["cost_per_1000"], -results[m]["score"])) if ok else None
    return chosen, why


# STAGE 5
def monthly_cost(cost_per_query, queries_per_day, multiplier=1, days=30):
    """Rupees a month at `multiplier` times today's volume."""
    return cost_per_query * queries_per_day * multiplier * days


def volume_at_ceiling(cost_per_query, monthly_ceiling, days=30):
    """Queries a day at which the monthly bill reaches the ceiling."""
    return monthly_ceiling / (cost_per_query * days)
