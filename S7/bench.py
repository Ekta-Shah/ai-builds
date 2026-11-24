"""Benchmark models on your own cases.

    python bench.py --model gemini-flash-lite-latest --rpm 12      # run every case once on one model
    python bench.py --model gemini-flash-lite-latest --only 5,6    # a few cases
    python bench.py --report                                       # table + decision from bench_*.csv, prices.json, rule.json

A run writes bench_<model>.csv. The model is set through DHRUVA_MODEL, so the agent code never changes.
"""
import argparse
import asyncio
import csv
import glob
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
import bench_tools as bt


def read_cases(only=None):
    rows = list(csv.DictReader(open(HERE / "bench_cases.csv")))
    return [r for r in rows if not only or r["id"] in only]


def run(model, rpm, only):
    os.environ["DHRUVA_MODEL"] = model  # before the agent is imported
    import importlib
    from google.adk.plugins import BasePlugin
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    root_agent = importlib.import_module("dhruva_agent.agent").root_agent
    gap = 60 / rpm if rpm else 0

    class Meter(BasePlugin):
        last, waited, tin, tout = 0.0, 0.0, 0, 0

        def __init__(self):
            super().__init__(name="meter")

        async def before_model_callback(self, *, callback_context, llm_request):
            wait = Meter.last + gap - time.time()  # pacing under a requests-per-minute limit is not latency
            if wait > 0:
                Meter.waited += wait
                await asyncio.sleep(wait)
            Meter.last = time.time()

        async def after_model_callback(self, *, callback_context, llm_response):
            u = llm_response.usage_metadata
            if u:
                Meter.tin += u.prompt_token_count or 0
                Meter.tout += u.candidates_token_count or 0

    async def once(query):
        Meter.waited = Meter.tin = Meter.tout = 0
        runner = Runner(agent=root_agent, app_name="bench", session_service=InMemorySessionService(), plugins=[Meter()])
        sid = f"s{time.time_ns()}"
        await runner.session_service.create_session(app_name="bench", user_id="ira", session_id=sid)
        msg = types.Content(role="user", parts=[types.Part(text=query)])
        text, t0 = "", time.time()
        async for ev in runner.run_async(user_id="ira", session_id=sid, new_message=msg):
            if ev.is_final_response() and ev.content and ev.content.parts:
                text = "".join(p.text or "" for p in ev.content.parts)
        return text, time.time() - t0 - Meter.waited

    loop = asyncio.new_event_loop()
    out = []
    print(f"{model}\n{'#':>3} {'bucket':10} {'pass':5} {'tries':>5} {'secs':>6} {'in':>6} {'out':>5}")
    for row in read_cases(only):
        tries = [0]

        def attempt():
            tries[0] += 1
            return loop.run_until_complete(once(row["query"]))  # one loop for the whole run: asyncio.run per case floods stderr
        try:
            reply, secs = bt.backoff_call(attempt, retries=5, base=4.0)
        except Exception as e:
            reply, secs = f"ERROR {type(e).__name__}: {str(e)[:100]}", 0.0
        ok = bt.passed(row, reply)
        out.append({"id": row["id"], "bucket": row["bucket"], "holdout": row["holdout"], "passed": ok, "attempts": tries[0],
                    "seconds": round(secs, 2), "in_tokens": Meter.tin, "out_tokens": Meter.tout, "reply": reply.replace("\n", " ")})
        print(f"{row['id']:>3} {row['bucket']:10} {'yes' if ok else 'NO':5} {tries[0]:>5} {secs:>6.1f} {Meter.tin:>6} {Meter.tout:>5}")
    loop.close()
    with open(HERE / f"bench_{model}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)


def summarise(model, rows, price, usd_inr):
    for r in rows:
        r["passed"] = r["passed"] in (True, "True")
    tune = [r for r in rows if r["holdout"] == "no"]
    hold = [r for r in rows if r["holdout"] == "yes"]
    ok = [r for r in rows if not r["reply"].startswith("ERROR")]
    avg = lambda k: sum(float(r[k]) for r in ok) / len(ok)
    per_query = bt.cost_inr(avg("in_tokens"), avg("out_tokens"), price, usd_inr)
    return {"score": bt.bucket_scores(tune)["all"], "buckets": bt.bucket_scores(tune),
            "holdout": bt.bucket_scores(hold)["all"] if hold else 0.0,
            "p95": bt.p95([float(r["seconds"]) for r in ok]), "retries": sum(int(r["attempts"]) - 1 for r in rows),
            "per_query": per_query, "cost_per_1000": per_query * 1000}


def report():
    prices = json.load(open(HERE / "prices.json"))
    rule = json.load(open(HERE / "rule.json"))
    files = sorted(glob.glob(str(HERE / "bench_*.csv")))
    files = [f for f in files if not f.endswith("bench_cases.csv")]
    if not files:
        sys.exit("No bench_<model>.csv files yet. Run bench.py --model <name> first.")
    missing = [k for k, v in rule.items() if v is None] + (["usd_inr"] if prices["usd_inr"] is None else [])
    if missing:
        sys.exit(f"Fill these in first (rule.json / prices.json): {', '.join(missing)}")
    res = {}
    for f in files:
        model = Path(f).stem[len("bench_"):]
        if model not in prices["models"] or prices["models"][model]["input_per_m"] is None:
            print(f"skipping {model}: no price in prices.json")
            continue
        res[model] = summarise(model, list(csv.DictReader(open(f))), prices["models"][model], prices["usd_inr"])
    print(f"{'model':28} {'score':>6} {'holdout':>8} {'p95 s':>6} {'retries':>7} {'Rs/query':>9} {'Rs/1000':>8}   buckets")
    for m, r in res.items():
        b = " ".join(f"{k}={v:.2f}" for k, v in sorted(r["buckets"].items()) if k != "all")
        print(f"{m:28} {r['score']:>6.2f} {r['holdout']:>8.2f} {r['p95']:>6.1f} {r['retries']:>7} {r['per_query']:>9.3f} {r['cost_per_1000']:>8.1f}   {b}")
    chosen, why = bt.decide(res, rule)
    print(f"\nChosen: {chosen}")
    for m, w in why.items():
        print(f"  {m}: {'meets the rule' if not w else 'breaks ' + ', '.join(w)}")
    if chosen:
        c = res[chosen]["per_query"]
        print(f"\nMonthly cost of {chosen} at {rule['queries_per_day']} queries a day:")
        for k in (1, 5, 50):
            print(f"  {k:>2}x: Rs {bt.monthly_cost(c, rule['queries_per_day'], k):,.0f}")
        print(f"  The ceiling of Rs {rule['monthly_ceiling_inr']:,.0f} a month is reached at "
              f"{bt.volume_at_ceiling(c, rule['monthly_ceiling_inr']):,.0f} queries a day "
              f"({bt.volume_at_ceiling(c, rule['monthly_ceiling_inr']) / rule['queries_per_day']:.1f}x today).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--rpm", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    elif a.model:
        run(a.model, a.rpm, set(a.only.split(",")) - {""})
    else:
        ap.error("give --model <name> or --report")
