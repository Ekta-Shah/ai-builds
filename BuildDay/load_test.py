"""Fire many questions at an answer() function at once and see what breaks first.
  python load_test.py --impl reference/assistant.py --n 60 --workers 8 [--distinct 15]
--distinct controls how many different questions are repeated: fewer means more cache hits."""
import argparse, csv, importlib.util, os, random, statistics as st, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--impl", required=True); ap.add_argument("--n", type=int, default=60)
ap.add_argument("--workers", type=int, default=8); ap.add_argument("--distinct", type=int, default=15)
a = ap.parse_args()
spec = importlib.util.spec_from_file_location("impl", a.impl); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
cases = [c for c in csv.DictReader(open(os.path.join(HERE, "golden_questions.csv"))) if c["kind"] in ("lookup", "aggregate", "trend", "top-n")]
random.seed(1); pool = random.sample(cases, min(a.distinct, len(cases)))
jobs = [random.choice(pool) for _ in range(a.n)]


def one(c):
    t = time.time()
    try:
        o = mod.answer(c["question"], c["user"]); return dict(ok=True, secs=time.time() - t, cached=o.get("cached", False), tin=o.get("tokens_in", 0), tout=o.get("tokens_out", 0), err="")
    except Exception as e:
        return dict(ok=False, secs=time.time() - t, cached=False, tin=0, tout=0, err=str(e)[:60])


t0 = time.time()
with ThreadPoolExecutor(a.workers) as ex:
    res = list(ex.map(one, jobs))
wall = time.time() - t0
good = [r for r in res if r["ok"]]; s = sorted(r["secs"] for r in good) or [0]
print(f"requests {a.n}  workers {a.workers}  distinct {len(pool)}  wall {wall:.0f}s  throughput {a.n / wall * 60:.0f}/min")
print(f"ok {len(good)}  failed {a.n - len(good)}  cache hits {sum(r['cached'] for r in good)}")
print(f"median {st.median(s):.1f}s  p95 {s[int(0.95 * (len(s) - 1))]:.1f}s  tokens in {sum(r['tin'] for r in good)} out {sum(r['tout'] for r in good)}")
errs = {}
for r in res:
    if r["err"]:
        errs[r["err"]] = errs.get(r["err"], 0) + 1
for e, k in errs.items():
    print(f"  {k} x {e}")
