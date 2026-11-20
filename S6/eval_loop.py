"""Run the maker alone, then the maker-checker loop, on the same questions. Then compare.

    python eval_loop.py dhruva_maker --rpm 5
    python eval_loop.py dhruva_loop --rpm 5
    python eval_loop.py --compare                       # maker alone vs dhruva_loop
    python eval_loop.py --compare dhruva_loop dhruva_loop2
    (add --all for all 18 questions instead of the default 11; --only 12,13 for particular ones)

A reply is SENT if the agent is the maker alone, or the loop ended in PASS. HOLD and FAIL-at-the-limit are held for a person.
A sent reply is WRONG if it matches the case's bad_if pattern, or a clean case's must_have is missing.
Ground truth lives in scenarios_s6.csv, not in an LLM: the checker is judged by code.
"""
import argparse
import asyncio
import csv
import re
import statistics
import time
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from eval_agent import Counter

HERE = Path(__file__).parent
DEFAULT_IDS = {"1", "2", "3"} | {str(i) for i in range(11, 19)}  # 3 normal questions and the 8 traps


def musthave(pattern, text):
    """'&' joins parts that must all be present; '|' inside a part means any of."""
    return all(re.search(part, text, re.I) for part in pattern.split("&"))


async def run_one(runner, counter, query):
    counter.reset()
    sid = f"s{time.time_ns()}"
    await runner.session_service.create_session(app_name="dhruva", user_id="ira", session_id=sid)
    t0 = time.time()
    msg = types.Content(role="user", parts=[types.Part(text=query)])
    async for _ in runner.run_async(user_id="ira", session_id=sid, new_message=msg):
        pass
    secs = time.time() - t0 - counter.waited
    st = (await runner.session_service.get_session(app_name="dhruva", user_id="ira", session_id=sid)).state
    return st, secs


async def evaluate(name, rpm, ids, pause):
    import importlib
    root = importlib.import_module(f"{name}.agent").root_agent
    counter = Counter(rpm)
    runner = Runner(agent=root, app_name="dhruva", session_service=InMemorySessionService(), plugins=[counter])
    rows = [r for r in csv.DictReader(open(HERE / "scenarios_s6.csv")) if r["id"] in ids]
    out = []
    print(f"{'#':>3} {'kind':5} {'sent':5} {'wrong':5} {'verdict':7} {'calls':>5} {'secs':>6}")
    for row in rows:
        for attempt in range(3):
            try:
                st, secs = await run_one(runner, counter, row["query"])
                break
            except Exception as e:
                m = re.search(r"retry in ([\d.]+)s", str(e))
                if attempt < 2 and ("429" in str(e) or "503" in str(e)):
                    time.sleep(float(m.group(1)) + 2 if m else 20)
                else:
                    st, secs = {"draft": f"ERROR {type(e).__name__}: {str(e)[:100]}"}, 0.0
                    break
        draft, verdict = st.get("draft", "") or "", st.get("verdict", "")
        is_loop = name != "dhruva_maker"
        sent = (verdict == "PASS") if is_loop else True
        bad = bool(row["bad_if"]) and re.search(row["bad_if"], draft, re.I | re.S) is not None
        missing = bool(row["must_have"]) and not musthave(row["must_have"], draft)
        wrong = sent and (bad or missing)
        checks = sum(t in ("approve", "reject", "hold_for_human") for t in counter.tools)
        out.append({"id": row["id"], "kind": row["kind"], "sent": sent, "wrong": wrong, "verdict": verdict or "-",
                    "rounds": checks, "model_calls": counter.model_calls, "tokens": counter.tokens,
                    "seconds": round(secs, 1), "draft": draft.replace("\n", " ")})
        print(f"{row['id']:>3} {row['kind']:5} {'yes' if sent else 'HELD':5} {'WRONG' if wrong else 'ok':5} {verdict or '-':7} {counter.model_calls:>5} {secs:>6.1f}")
        time.sleep(pause)
    with open(HERE / f"results_{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print(f"\n{name}: wrong replies sent {sum(r['wrong'] for r in out)} of {len(out)}; "
          f"model calls per query {statistics.mean(r['model_calls'] for r in out):.1f}")


def load(name):
    p = HERE / f"results_{name}.csv"
    return list(csv.DictReader(open(p))) if p.exists() else None


def compare(an="dhruva_maker", bn="dhruva_loop"):
    a, b = load(an), load(bn)
    if not (a and b):
        print(f"Run both first: eval_loop.py {an}, then {bn}"); return
    ids = {r["id"] for r in a} & {r["id"] for r in b}
    a, b = [r for r in a if r["id"] in ids], [r for r in b if r["id"] in ids]
    T = lambda r: r["wrong"] == "True"
    H = lambda r: r["sent"] == "False"
    bad_a, bad_b = sum(map(T, a)), sum(map(T, b))
    clean = [r for r in b if r["kind"] == "clean"]
    clean_a_ok = {r["id"] for r in a if r["kind"] == "clean" and not T(r)}
    false_blocks = [r for r in clean if H(r) and r["id"] in clean_a_ok]
    n = len(a)
    mean = lambda rs, k: statistics.mean(float(r[k]) for r in rs)
    med = lambda rs: statistics.median(float(r["seconds"]) for r in rs)
    print(f"{an} -> {bn}, cases: {n}")
    print(f"wrong replies sent:    {an} {bad_a}    {bn} {bad_b}")
    print(f"catch rate:            {(bad_a - bad_b) / bad_a:.0%}" if bad_a else "catch rate:            n/a (the maker alone made no wrong reply)")
    print(f"false blocks:          {len(false_blocks)} of {len(clean_a_ok)} replies the maker got right were held by the checker")
    print(f"held for a person:     {sum(map(H, b))} of {n}")
    print(f"model calls per query: {mean(a, 'model_calls'):.1f} -> {mean(b, 'model_calls'):.1f}")
    print(f"median seconds:        {med(a):.1f} -> {med(b):.1f}")
    print(f"tokens per query:      {mean(a, 'tokens'):,.0f} -> {mean(b, 'tokens'):,.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", nargs="?")
    ap.add_argument("--rpm", type=int, default=0)
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--compare", nargs="*", metavar="AGENT", help="compare two result files; default dhruva_maker dhruva_loop")
    a = ap.parse_args()
    if a.compare is not None or not a.agent:
        compare(*(a.compare or ["dhruva_maker", "dhruva_loop"])[:2])
    else:
        ids = set(a.only.split(",")) - {""} or ({str(i) for i in range(1, 19)} if a.all else DEFAULT_IDS)
        asyncio.run(evaluate(a.agent, a.rpm, ids, a.pause))
