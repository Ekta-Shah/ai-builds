"""Run the 5 core scenarios (or all 10 with --all) through an agent and print pass rate, model calls and latency.

    python eval_agent.py dhruva_v1
    python eval_agent.py dhruva_v2 --pause 4        # free-tier keys: wait between scenarios
    python eval_agent.py dhruva_v2 --rpm 5          # stay under 5 model calls a minute (free tier)
    python eval_agent.py dhruva_v2 --all            # the 5 core questions plus 5 more (uses 2 to 3 times the model calls)

Pass = the reply contains the expected text (| means any of, & means all of) AND the expected tool was called.
Scenario 5 expects 'already': it needs scenario 4 to run first in the same process (the ticket is remembered).
"""
import argparse
import asyncio
import csv
import importlib
import re
import statistics
import time
from pathlib import Path

from google.adk.plugins import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class Counter(BasePlugin):
    """Counts every model call and tool call, including the ones inside specialist agents."""

    def __init__(self, rpm=0):
        super().__init__(name="counter")
        self.gap, self.last = (60 / rpm if rpm else 0), 0.0
        self.reset()

    def reset(self):
        self.model_calls, self.tokens, self.tools, self.waited = 0, 0, [], 0.0

    async def before_model_callback(self, *, callback_context, llm_request):
        self.model_calls += 1
        wait = self.last + self.gap - time.time()  # stay under a requests-per-minute limit
        if wait > 0:
            self.waited += wait  # pacing time is not the agent's latency
            await asyncio.sleep(wait)
        self.last = time.time()

    async def after_model_callback(self, *, callback_context, llm_response):
        u = llm_response.usage_metadata
        if u:
            self.tokens += (u.prompt_token_count or 0) + (u.candidates_token_count or 0)

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        self.tools.append(tool.name)


def passed(row, text, tools):
    t = text.lower()
    ok = False
    for must in row["expect_text"].lower().split("&"):
        ok = any(alt.strip() in t for alt in must.split("|"))
        if not ok:
            break
    return ok and (not row["expect_tool"] or row["expect_tool"] in tools)


async def run_one(runner, counter, query):
    counter.reset()
    sid = f"s{time.time_ns()}"
    await runner.session_service.create_session(app_name="dhruva", user_id="ira", session_id=sid)
    text, t0 = "", time.time()
    msg = types.Content(role="user", parts=[types.Part(text=query)])
    async for ev in runner.run_async(user_id="ira", session_id=sid, new_message=msg):
        if ev.is_final_response() and ev.content and ev.content.parts:
            text = "".join(p.text or "" for p in ev.content.parts)
    return text, time.time() - t0 - counter.waited


async def main(name, pause, only=None, rpm=0, extra=False):
    root_agent = importlib.import_module(f"{name}.agent").root_agent
    counter = Counter(rpm)
    runner = Runner(agent=root_agent, app_name="dhruva", session_service=InMemorySessionService(), plugins=[counter])
    here = Path(__file__).parent
    rows = list(csv.DictReader(open(here / "scenarios.csv")))
    if extra:
        rows += list(csv.DictReader(open(here / "scenarios_extra.csv")))
    rows = [r for r in rows if not only or r["id"] in only]
    out = []
    print(f"{'#':>2} {'pass':5} {'model calls':>11} {'tool calls':>10} {'seconds':>8}")
    for row in rows:
        for attempt in range(3):
            try:
                text, secs = await run_one(runner, counter, row["query"])
                break
            except Exception as e:  # rate limits and busy servers: wait and retry; give up after 3 tries
                text, secs = f"ERROR {type(e).__name__}: {str(e)[:120]}", 0.0
                m = re.search(r"retry in ([\d.]+)s", str(e))
                if attempt < 2 and ("429" in str(e) or "503" in str(e)):
                    time.sleep(float(m.group(1)) + 2 if m else 20)
                else:
                    break
        ok = passed(row, text, counter.tools)
        out.append({"id": row["id"], "pass": ok, "model_calls": counter.model_calls, "tool_calls": len(counter.tools),
                    "seconds": round(secs, 1), "tokens": counter.tokens, "tools": " ".join(counter.tools), "reply": text})
        print(f"{row['id']:>2} {'yes' if ok else 'NO':5} {counter.model_calls:>11} {len(counter.tools):>10} {secs:>8.1f}")
        time.sleep(pause)
    n = len(out)
    print(f"\n{name}: passed {sum(r['pass'] for r in out)} of {n}; "
          f"model calls per query {statistics.mean(r['model_calls'] for r in out):.1f}; "
          f"median latency {statistics.median(r['seconds'] for r in out):.1f} s; "
          f"tokens per query {statistics.mean(r['tokens'] for r in out):,.0f}")
    with open(f"results_{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--rpm", type=int, default=0, help="max model calls per minute (free key: 5)")
    ap.add_argument("--all", action="store_true", help="add the 5 extra scenarios")
    ap.add_argument("--only", default="", help="comma-separated scenario ids")
    a = ap.parse_args()
    asyncio.run(main(a.agent, a.pause, set(a.only.split(",")) - {""}, a.rpm, a.all))
