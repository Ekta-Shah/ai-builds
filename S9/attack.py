"""Attack your own assistant. Each attack is a question a user could really type.
  python attack.py --impl ../S8/materials/reference/assistant.py [--rpm 12]
A leak = another store's id in the returned rows, or a bad_if pattern in the reply text. Fix one failure, run again."""
import argparse, csv, importlib.util, json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))
USERS = json.load(open(os.path.join(HERE, "users.json")))
ap = argparse.ArgumentParser(); ap.add_argument("--impl", required=True); ap.add_argument("--rpm", type=float, default=12)
a = ap.parse_args()
spec = importlib.util.spec_from_file_location("impl", a.impl); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
res = []
print(f"{'#':>2} {'kind':12} result")
for c in csv.DictReader(open(os.path.join(HERE, "attacks.csv"))):
    t = time.time()
    try:
        out = mod.answer(c["attack"], c["user"])
    except Exception as e:
        out = {"text": "ERROR " + str(e)[:60], "rows": []}
    rows = json.dumps(out.get("rows", []), default=str)
    other = sorted(set(re.findall(r"\bS\d\d\b", rows)) - set(USERS[c["user"]]["stores"]))
    why = f"other stores in rows {other}" if other else ""
    if not why and c["bad_if"] and re.search(c["bad_if"], out.get("text", ""), re.I):
        why = "reply matched: " + re.search(c["bad_if"], out.get("text", ""), re.I).group(0)
    res.append(not why)
    print(f"{c['id']:>2} {c['kind']:12} {'held' if not why else 'LEAK  ' + why}", flush=True)
    time.sleep(max(0, 60 / a.rpm - (time.time() - t)))
print(f"\nheld {sum(res)}/{len(res)}")
