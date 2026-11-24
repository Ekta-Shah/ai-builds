"""python test_bench.py: checks your stage 2 to 5 functions. No key needed."""
import bench_tools as b


def stage2():
    calls, waits = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"
    assert b.backoff_call(flaky, sleep=waits.append) == "ok" and len(calls) == 3
    assert 2 <= waits[0] < 3.01 and 4 <= waits[1] < 5.01, waits  # 2*2**0 and 2*2**1, plus under 1 s of jitter
    n = []

    def bad():
        n.append(1)
        raise ValueError("API key not valid")
    try:
        b.backoff_call(bad, sleep=waits.append)
        raise AssertionError("a non-retryable error must be raised")
    except ValueError:
        assert len(n) == 1, "do not retry errors that are not rate limits"
    m = []

    def always():
        m.append(1)
        raise RuntimeError("503 UNAVAILABLE")
    try:
        b.backoff_call(always, retries=2, sleep=lambda s: None)
        raise AssertionError("must raise after the last retry")
    except RuntimeError:
        assert len(m) == 3


def stage3():
    assert b.p95([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == 10 and b.p95(list(range(1, 21))) == 19 and b.p95([5]) == 5
    assert abs(b.cost_inr(1_000_000, 500_000, {"input_per_m": 0.5, "output_per_m": 2.0}, 80) - 120) < 1e-9
    rows = [{"bucket": "a", "passed": True}, {"bucket": "a", "passed": False}, {"bucket": "b", "passed": True}]
    s = b.bucket_scores(rows)
    assert s["a"] == 0.5 and s["b"] == 1 and abs(s["all"] - 2 / 3) < 1e-9, s


def stage4():
    rule = {"min_score": 0.8, "max_holdout_drop": 0.1, "max_p95_seconds": 10, "max_cost_per_1000_inr": 100}
    res = {"cheap": {"score": 0.7, "holdout": 0.7, "p95": 3, "cost_per_1000": 10},
           "mid": {"score": 0.9, "holdout": 0.85, "p95": 6, "cost_per_1000": 40},
           "big": {"score": 0.95, "holdout": 0.95, "p95": 12, "cost_per_1000": 300},
           "lucky": {"score": 0.95, "holdout": 0.6, "p95": 3, "cost_per_1000": 5}}
    chosen, why = b.decide(res, rule)
    assert chosen == "mid", chosen
    assert why["cheap"] == ["score"] and why["big"] == ["p95", "cost"] and why["lucky"] == ["holdout"] and why["mid"] == [], why
    assert b.decide({"x": res["cheap"]}, rule)[0] is None


def stage5():
    assert b.monthly_cost(0.5, 200, 5) == 15000 and b.monthly_cost(0.5, 200) == 3000
    assert b.volume_at_ceiling(0.5, 15000) == 1000


for n, f in [(2, stage2), (3, stage3), (4, stage4), (5, stage5)]:
    try:
        f()
        print(f"stage {n} ok")
    except NotImplementedError as e:
        print(f"stage {n}: not written yet ({e})")
    except AssertionError as e:
        print(f"stage {n}: FAIL {e}")
