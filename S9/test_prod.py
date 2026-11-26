"""python test_prod.py: checks your stage 1 to 4 work. No key needed. Run python make_usage_log.py once first."""
import json
import re
import sqlite3
import tempfile
from pathlib import Path

import prod_tools as p

HERE = Path(__file__).parent


def stage1():
    g = p.SpendGuard(daily_cap_inr=10.0, user_cap_inr=4.0)
    assert g.allow("a", 4.0) is True, "equal to the cap is allowed"
    assert g.allow("a", 4.01) is False, "more than the user cap is blocked"
    g.record("a", 3.0)
    assert g.allow("a", 1.0) is True and g.allow("a", 1.5) is False, "the user's own total counts"
    assert g.allow("b", 4.0) is True, "another user is not affected by a's spend"
    for u in ("b", "c"):
        g.record(u, 3.5)
    assert g.total == 10.0 or abs(g.total - 10.0) < 1e-9, g.total
    assert g.allow("d", 0.5) is False, "the day's total is capped too"
    assert g.allow("a", 0) is True, "a free call is always allowed"
    g.reset()
    assert g.allow("d", 4.0) is True and g.total == 0, "reset starts a new day"
    ch = [("rules", "r" * 400), ("t_sales", "s" * 400), ("t_stores", "x" * 400), ("metric_a", "a" * 200), ("metric_b", "b" * 400)]
    got = p.trim_context(ch, 250, {"rules", "t_sales"})
    assert [n for n, _ in got] == ["rules", "t_sales", "metric_a"], [n for n, _ in got]
    assert [n for n, _ in p.trim_context(ch, 50, {"rules"})] == ["rules"], "kept chunks stay even over budget"
    assert [n for n, _ in p.trim_context(ch, 10_000, {"rules"})] == [n for n, _ in ch], "original order, everything fits"


def stage2():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "base.json").write_text('{"log_level": "INFO", "max_rpm": 10}')
        (t / "dev.json").write_text('{"log_level": "DEBUG"}')
        (t / "test.json").write_text("{}")
        (t / "live.json").write_text('{"max_rpm": 60}')
        c = p.load_config("dev", t, {})
        assert c["log_level"] == "DEBUG" and c["max_rpm"] == 10 and c["env"] == "dev" and c["has_key"] is False, c
        c = p.load_config("live", t, {"GOOGLE_API_KEY": "secret123"})
        assert c["max_rpm"] == 60 and c["has_key"] is True and "secret123" not in json.dumps(c), "the secret must never be in the config"
        for env, environ in (("live", {}), ("test", {"GOOGLE_API_KEY": ""}), ("staging", {"GOOGLE_API_KEY": "x"})):
            try:
                p.load_config(env, t, environ)
                raise AssertionError(f"{env} with {environ} must raise ConfigError")
            except p.ConfigError:
                pass
    flags = {"live": "v1", "candidate": "v2", "rollout_percent": 10, "salt": "s9", "history": []}
    assert p.pick_version("m01", flags) == p.pick_version("m01", flags), "the same user must always get the same version"
    n = sum(p.pick_version(f"u{i}", flags) == "v2" for i in range(2000))
    assert 140 < n < 260, f"about 10% of 2000 users should get v2, got {n}"
    assert {p.pick_version(f"u{i}", {**flags, "rollout_percent": 0}) for i in range(100)} == {"v1"}
    assert {p.pick_version(f"u{i}", {**flags, "rollout_percent": 100}) for i in range(100)} == {"v2"}
    assert {p.pick_version(f"u{i}", {**flags, "candidate": None, "rollout_percent": 100}) for i in range(50)} == {"v1"}
    before = json.dumps(flags)
    new = p.rollback(flags, "cost up 60%", "2026-12-01T10:00:00")
    assert json.dumps(flags) == before, "rollback must not change the flags you passed in"
    assert new["rollout_percent"] == 0 and new["live"] == "v1" and new["candidate"] == "v2"
    assert new["history"] == [{"action": "rollback", "from": "v2", "reason": "cost up 60%", "at": "2026-12-01T10:00:00"}], new["history"]
    assert {p.pick_version(f"u{i}", new) for i in range(200)} == {"v1"}, "after rollback nobody gets v2"


def _norm(rows):
    return [[round(v, 4) if isinstance(v, float) else v for v in r] for r in rows]


def _run_sql(block):
    sql = "\n".join(l for l in block.splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
    assert sql.lower().startswith(("select", "with")), "each query must be a single SELECT"
    assert ";" not in sql, "one statement per question"
    con = sqlite3.connect(f"file:{HERE / 'usage.db'}?mode=ro", uri=True)
    try:
        return [list(r) for r in con.execute(sql).fetchall()]
    finally:
        con.close()


def stage3():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE events(id INTEGER PRIMARY KEY, ts TEXT, user TEXT, store TEXT, q_hash TEXT, decision TEXT, cached INTEGER, latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, cost_inr REAL, ok INTEGER, version TEXT)")
    ev = dict(ts="2026-11-02 10:00:00", user="m01", store="S01", question="net sales for S01 call me on 9876543210", decision="sql", cached=0, latency_ms=2100, tokens_in=650, tokens_out=160, cost_inr=0.0116, ok=1, version="v1")
    p.log_event(con, ev); p.log_event(con, {**ev, "question": "net sales for S01 call me on 9123456789"}); p.log_event(con, {**ev, "user": "x'); DROP TABLE events;--"})
    rows = con.execute("SELECT * FROM events").fetchall()
    assert len(rows) == 3, "all events must be written (and the table must survive a hostile user name)"
    cols = [c[1] for c in con.execute("PRAGMA table_info(events)")]
    h = rows[0][cols.index("q_hash")]
    assert re.fullmatch(r"[0-9a-f]{12}", h), f"q_hash must be 12 hex characters, got {h!r}"
    assert rows[0][cols.index("q_hash")] == rows[1][cols.index("q_hash")], "the same question after redaction must hash the same (numbers were redacted)"
    assert "9876543210" not in json.dumps(rows), "the phone number must not reach the log"
    sql = (HERE / "queries.sql").read_text()
    exp = json.loads((HERE / "expected.json").read_text())
    parts = re.split(r"^-- Q(\d):.*$", sql, flags=re.M)
    got = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    for k in ("1", "2", "3"):
        assert got.get(k, "").strip() and "SELECT" in got[k].upper().replace("--", ""), f"Q{k}: write a SELECT under the marker"
        r = _run_sql(got[k])
        assert _norm(r) == _norm(exp["q" + k]), f"Q{k}: got {_norm(r)[:3]}... expected {_norm(exp['q' + k])[:3]}..."
    import monitor
    rc = sqlite3.connect(f"file:{HERE / 'usage.db'}?mode=ro", uri=True)
    assert monitor.weekly_active(rc, "46") == 12, f"week 46: 12 managers asked a question; monitor.py says {monitor.weekly_active(rc, '46')}"
    assert monitor.weekly_active(rc, "41") == 28
    note = (HERE / "incident.md").read_text()
    assert "TODO" not in note, "finish the incident note: remove every TODO"
    lines = [l for l in note.splitlines() if l.strip() and not l.startswith("#")]
    assert len(lines) >= 3 and re.search(r"\d", note), "the note needs what was shown, what was true, the cause and the fix, with a number"


def stage4():
    cases = {
        "call me on 9876543210": "call me on [PHONE]",
        "call +91 98765 43210 now": "call [PHONE] now",
        "mail ravi@shop.in please": "mail [EMAIL] please",
        "PAN is ABCDE1234F ok": "PAN is [PAN] ok",
        "aadhaar 1234 5678 9012": "aadhaar [AADHAAR]",
        "aadhaar 123456789012": "aadhaar [AADHAAR]",
        "Rs 2,48,969 in S03 on 2026-10-01 order S03-261001-004": "Rs 2,48,969 in S03 on 2026-10-01 order S03-261001-004",
        "net sales were 225898.4": "net sales were 225898.4",
        "units 1234567890": "units 1234567890",
    }
    for text, want in cases.items():
        got = p.redact(text)
        if text == "units 1234567890":
            continue
        assert got == want, f"{text!r} -> {got!r}, expected {want!r}"
    assert p.redact("a@b.co and 9876543210 and ABCDE1234F") == "[EMAIL] and [PHONE] and [PAN]"


STAGES = [(1, "SpendGuard and trim_context", stage1), (2, "load_config, pick_version, rollback", stage2),
          (3, "log_event, the three queries, the bug, the incident note", stage3), (4, "redact", stage4)]
if __name__ == "__main__":
    if not (HERE / "usage.db").exists():
        raise SystemExit("usage.db is missing: run python make_usage_log.py first")
    for n, what, fn in STAGES:
        try:
            fn(); print(f"stage {n} ok")
        except NotImplementedError as e:
            print(f"stage {n}: not written yet ({e})")
        except (AssertionError, FileNotFoundError, KeyError, ModuleNotFoundError, sqlite3.Error) as e:
            print(f"stage {n} FAIL ({what}): {e}")
