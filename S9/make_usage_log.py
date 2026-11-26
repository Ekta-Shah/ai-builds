"""Build usage.db: six weeks of SYNTHETIC logs for the store analytics assistant (no model was called).
Run once: python make_usage_log.py   (it also writes expected.json, the answers your tests check against)."""
import datetime as dt, hashlib, json, os, random, sqlite3

random.seed(9)
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "usage.db")
if os.path.exists(DB):
    os.remove(DB)
USERS = [f"m{i:02d}" for i in range(1, 37)]
STORE = {u: f"S{(i // 3) + 1:02d}" for i, u in enumerate(USERS)}
START = dt.date(2026, 10, 12)
ASKERS = [28, 20, 16, 14, 13, 12]
core = random.sample(USERS, 12)
pool = [u for u in USERS if u not in core]
weekly = []
prev = USERS[:]
for k in ASKERS:
    keep = [u for u in prev if u in core] + [u for u in prev if u not in core]
    sel = core + random.sample([u for u in prev if u not in core], k - 12) if k > 12 else core
    weekly.append(sel); prev = sel
CAND_FROM = dt.date(2026, 11, 9)


def is_cand(u):
    return int(hashlib.sha256(f"s9:{u}".encode()).hexdigest()[:8], 16) % 100 < 20


con = sqlite3.connect(DB)
con.executescript("""
CREATE TABLE events(id INTEGER PRIMARY KEY, ts TEXT, user TEXT, store TEXT, q_hash TEXT, decision TEXT, cached INTEGER,
                    latency_ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, cost_inr REAL, ok INTEGER, version TEXT);
CREATE TABLE logins(id INTEGER PRIMARY KEY, ts TEXT, user TEXT);
""")
ev, lg = [], []
for w, sel in enumerate(weekly):
    wk0 = START + dt.timedelta(weeks=w)
    for u in USERS:
        if random.random() < (0.97 if u in sel else 0.8):
            d = wk0 + dt.timedelta(days=random.randint(0, 5))
            lg.append((f"{d} {random.randint(8, 19):02d}:{random.randint(0, 59):02d}:00", u))
    for u in sel:
        days = [random.randint(0, 5) for _ in range(random.randint(2, 4))]
        if w == 0 and random.random() < 0.7:
            days = [0] + days
        for dd in days:
            d = wk0 + dt.timedelta(days=dd)
            for _ in range(random.randint(10, 20) if (w == 0 and dd == 0) else random.randint(3, 9)):
                ts = f"{d} {random.randint(9, 19):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
                ver = "v2" if (is_cand(u) and d >= CAND_FROM) else "v1"
                cached = random.random() < 0.18
                ok = 0 if random.random() < 0.025 else 1
                tin = 0 if cached else int(random.gauss(1500 if ver == "v2" else 650, 80))
                tout = 0 if cached else int(random.gauss(165, 40))
                lat = 60 if cached else (random.randint(15000, 30000) if not ok else int(random.lognormvariate(7.7, 0.45)))
                dec = random.choices(["sql", "clarify", "refuse"], [0.85, 0.08, 0.07])[0]
                cost = round(tin * 9e-6 + tout * 36e-6, 6)
                qh = hashlib.sha256(f"q{random.randint(1, 120)}".encode()).hexdigest()[:12]
                ev.append((ts, u, STORE[u], qh, dec, int(cached), lat, tin, tout, cost, ok, ver))
ev.sort()
con.executemany("INSERT INTO events(ts,user,store,q_hash,decision,cached,latency_ms,tokens_in,tokens_out,cost_inr,ok,version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ev)
con.executemany("INSERT INTO logins(ts,user) VALUES (?,?)", sorted(lg))
con.commit()
G = {
 "q1": "SELECT strftime('%W', ts) AS week, COUNT(DISTINCT user) AS askers FROM events GROUP BY week ORDER BY week",
 "q2": "SELECT version, COUNT(*) AS questions, ROUND(AVG(cost_inr),5) AS avg_cost FROM events GROUP BY version ORDER BY version",
 "q3": "SELECT date(ts) AS day, COUNT(*) AS questions FROM events GROUP BY day ORDER BY day LIMIT 7",
 "logins_wk": "SELECT strftime('%W', ts) wk, COUNT(DISTINCT user) FROM logins GROUP BY wk ORDER BY wk",
}
exp = {k: [list(r) for r in con.execute(q).fetchall()] for k, q in G.items()}
json.dump(exp, open(os.path.join(HERE, "expected.json"), "w"), indent=1)
print(len(ev), "events,", len(lg), "logins ->", DB)
print("true askers by week:", exp["q1"]); print("login users by week (what the buggy script reports):", exp["logins_wk"])
print("cost by version:", exp["q2"]); print("first 7 days:", exp["q3"])
