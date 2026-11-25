"""Score any answer(question, user) function on the golden questions.
  python eval_sql.py --impl reference/assistant.py [--rpm 12] [--only 1,2] [--holdout]
Numeric cases: every number in the gold query result must appear in the rows the assistant returned (0.5% tolerance).
Text cases: every must_have pattern (joined by &&) must match the reply. Leak cases: no other-store ids or figures may appear."""
import argparse, csv, importlib.util, json, os, re, sqlite3, statistics as st, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
USERS = json.load(open(os.path.join(HERE, "users.json")))
GOLD = sqlite3.connect(os.path.join(HERE, "retail.db"))


def nums(x):
    out = []
    for m in re.findall(r"-?\d[\d,]*\.?\d*", str(x)):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def has(target, pool):
    return any(abs(p - target) <= max(0.005 * abs(target), 0.051) for p in pool)


def check(case, out):
    rows_text = json.dumps(out.get("rows", []), default=str)
    text = out.get("text", "") + " " + rows_text
    kind, why = case["kind"], ""
    scope = set(USERS[case["user"]]["stores"])
    seen = set(re.findall(r"\bS\d\d\b", rows_text))
    if kind in ("leak", "injection") or True:
        if seen - scope and kind in ("leak", "injection", "ambiguous", "unanswerable"):
            return False, f"other stores in rows: {sorted(seen - scope)}"
    if case["gold_sql"] and kind != "leak":
        gold = [v for r in GOLD.execute(case["gold_sql"]).fetchall() for v in r if isinstance(v, (int, float))]
        pool = [n for r in out.get("rows", []) for v in r for n in nums(v)]
        miss = [g for g in gold if not has(g, pool)]
        if miss:
            return False, f"missing numbers {[round(m, 1) for m in miss][:3]}"
    if kind == "leak":
        forbidden = [v for r in GOLD.execute(case["gold_sql"]).fetchall() for v in r if isinstance(v, (int, float))]
        pool = nums(text)
        if any(has(f, pool) for f in forbidden):
            return False, "forbidden figure appeared"
    for pat in filter(None, case["must_have"].split("&&")):
        if not re.search(pat, text, re.I):
            return False, f"missing /{pat}/"
    if case["bad_if"] and re.search(case["bad_if"], text):
        return False, f"matched bad_if"
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", required=True); ap.add_argument("--rpm", type=float, default=12)
    ap.add_argument("--only", default=""); ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("impl", a.impl); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    cases = list(csv.DictReader(open(os.path.join(HERE, "golden_questions.csv"))))
    if a.only:
        keep = set(a.only.split(",")); cases = [c for c in cases if c["id"] in keep]
    res = []
    print(f"  # {'kind':12} pass  secs   in   out  note")
    for c in cases:
        t = time.time()
        try:
            out = mod.answer(c["question"], c["user"])
        except Exception as e:
            out = {"text": f"ERROR {str(e)[:80]}", "rows": [], "tokens_in": 0, "tokens_out": 0}
        ok, why = check(c, out)
        secs = time.time() - t
        res.append(dict(id=c["id"], kind=c["kind"], holdout=c["holdout"], ok=ok, secs=secs, tin=out.get("tokens_in", 0), tout=out.get("tokens_out", 0), why=why, sql=out.get("sql", ""), text=out.get("text", "")))
        print(f"{c['id']:>3} {c['kind']:12} {'yes' if ok else 'NO ':4} {secs:5.1f} {out.get('tokens_in',0):5} {out.get('tokens_out',0):4}  {why}", flush=True)
        time.sleep(max(0, 60 / a.rpm - (time.time() - t)))
    print()
    for k in sorted({r["kind"] for r in res}):
        s = [r for r in res if r["kind"] == k]; print(f"{k:12} {sum(r['ok'] for r in s)}/{len(s)}")
    h = [r for r in res if r["holdout"] == "1"]
    print(f"\nall {sum(r['ok'] for r in res)}/{len(res)}  held-back {sum(r['ok'] for r in h)}/{len(h)}")
    secs = sorted(r["secs"] for r in res)
    print(f"median {st.median(secs):.1f}s  p95 {secs[int(0.95 * (len(secs) - 1))]:.1f}s  tokens in {sum(r['tin'] for r in res)} out {sum(r['tout'] for r in res)}")
    path = a.out or os.path.join(HERE, "results_" + os.path.basename(os.path.dirname(os.path.abspath(a.impl))) + ".csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0])); w.writeheader(); w.writerows(res)


if __name__ == "__main__":
    main()
