"""Production layer for the store analytics assistant. Students write the functions marked STAGE; no model key needed to test them."""
import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path


class ConfigError(Exception):
    pass


# GIVEN
def monthly_cost(cost_per_query, queries_per_day, multiplier=1, days=30):
    """Rupees a month at `multiplier` times today's volume."""
    return cost_per_query * queries_per_day * multiplier * days


def volume_at_ceiling(cost_per_query, monthly_ceiling, days=30):
    """Queries a day at which the monthly bill reaches the ceiling."""
    return monthly_ceiling / (cost_per_query * days)


def bucket(user_id, salt):
    """A number from 0 to 99, the same every time for the same user and salt, spread evenly."""
    return int(hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:8], 16) % 100


def promote(flags, now):
    new = deepcopy(flags)
    new["history"].append({"action": "promote", "from": flags["live"], "to": flags["candidate"], "at": now})
    new["live"], new["candidate"], new["rollout_percent"] = flags["candidate"], None, 0
    return new


# STAGE 1: cost control
class SpendGuard:
    """Stops spending before the bill does. A call is allowed only if, after adding its estimated cost, neither the day's
    total nor that user's total is MORE THAN its cap (equal to the cap is allowed).
      SpendGuard(daily_cap_inr, user_cap_inr)
      allow(user, est_cost_inr) -> True or False. It does not record anything.
      record(user, cost_inr)    -> add the real cost to the day's total and to that user's total.
      reset()                   -> a new day: all totals back to zero."""

    def __init__(self, daily_cap_inr, user_cap_inr):
        self.daily_cap, self.user_cap = daily_cap_inr, user_cap_inr
        self.reset()

    def reset(self):
        self.total, self.by_user = 0.0, {}

    def allow(self, user, est_cost_inr):
        return (self.total + est_cost_inr <= self.daily_cap + 1e-9
                and self.by_user.get(user, 0.0) + est_cost_inr <= self.user_cap + 1e-9)

    def record(self, user, cost_inr):
        self.total += cost_inr
        self.by_user[user] = self.by_user.get(user, 0.0) + cost_inr


def trim_context(chunks, budget_tokens, keep):
    """chunks: list of (name, text). keep: set of names that must always stay (the rules, the table you need).
    Tokens are estimated as ceil(len(text) / 4). Start with the kept chunks, then add the other chunks in their given
    order while the total stays within budget_tokens; a chunk that does not fit is skipped and the next one is tried.
    Return the chosen (name, text) pairs in their ORIGINAL order. Kept chunks stay even if they alone exceed the budget."""
    est = lambda t: math.ceil(len(t) / 4)
    used = sum(est(t) for n, t in chunks if n in keep)
    chosen = set(keep)
    for n, t in chunks:
        if n not in keep and used + est(t) <= budget_tokens:
            chosen.add(n); used += est(t)
    return [(n, t) for n, t in chunks if n in chosen]


# STAGE 2: release
def load_config(env, config_dir, environ):
    """Config = config_dir/base.json, then config_dir/<env>.json on top (the later file wins on any key).
    env must be dev, test or live: otherwise raise ConfigError. In test and live the secret GOOGLE_API_KEY must be in
    `environ` (a dict): if it is missing or empty raise ConfigError. The secret value must never appear in the returned
    dict: add "has_key": True or False instead. Also add "env": env."""
    if env not in ("dev", "test", "live"):
        raise ConfigError(f"unknown environment: {env}")
    cfg = json.loads((Path(config_dir) / "base.json").read_text())
    cfg.update(json.loads((Path(config_dir) / f"{env}.json").read_text()))
    key = bool(environ.get("GOOGLE_API_KEY"))
    if env in ("test", "live") and not key:
        raise ConfigError("GOOGLE_API_KEY is not set")
    cfg["has_key"], cfg["env"] = key, env
    return cfg


def pick_version(user_id, flags):
    """The candidate version if there is a candidate and bucket(user_id, salt) < rollout_percent, else the live version."""
    if flags.get("candidate") and bucket(user_id, flags["salt"]) < flags["rollout_percent"]:
        return flags["candidate"]
    return flags["live"]


def rollback(flags, reason, now):
    """Return a NEW flags dict (do not change the one passed in) with rollout_percent 0 and one entry appended to history:
    {"action": "rollback", "from": <the candidate>, "reason": reason, "at": now}. The live version is unchanged."""
    new = deepcopy(flags)
    new["history"].append({"action": "rollback", "from": flags["candidate"], "reason": reason, "at": now})
    new["rollout_percent"] = 0
    return new


# STAGE 4 (redaction is used by stage 3's logger)
PATTERNS = [
    ("EMAIL", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ("PAN", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    ("AADHAAR", r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    ("PHONE", r"(?<![\d,.])(?:\+91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)"),
]


def redact(text):
    """Replace personal data with a tag before anything is logged: emails -> [EMAIL], PAN numbers (5 letters, 4 digits,
    1 letter) -> [PAN], 12-digit Aadhaar numbers (with optional spaces or dashes) -> [AADHAAR], Indian mobile numbers
    (10 digits starting 6-9, written 9876543210 or 98765 43210, optional +91 or 0) -> [PHONE]. Leave everything else alone: rupee amounts like 2,48,969,
    store ids like S03, dates and order ids must come back unchanged."""
    for tag, pat in PATTERNS:
        text = re.sub(pat, f"[{tag}]", text)
    return text


# STAGE 3: monitoring
def log_event(con, ev):
    """Write one row to the events table and commit. ev has: ts, user, store, question, decision, cached (0 or 1),
    latency_ms, tokens_in, tokens_out, cost_inr, ok (0 or 1), version.
    The question text must NEVER be stored: store q_hash = the first 12 hex characters of sha256(redact(question)), so the
    same question gives the same hash. Use ? placeholders: user names are untrusted input."""
    q = hashlib.sha256(redact(ev["question"]).encode()).hexdigest()[:12]
    con.execute("INSERT INTO events(ts,user,store,q_hash,decision,cached,latency_ms,tokens_in,tokens_out,cost_inr,ok,version) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (ev["ts"], ev["user"], ev["store"], q, ev["decision"], ev["cached"], ev["latency_ms"], ev["tokens_in"],
                 ev["tokens_out"], ev["cost_inr"], ev["ok"], ev["version"]))
    con.commit()
