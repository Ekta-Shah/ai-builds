"""See who a rollout reaches, and what a rollback does. Dry run by default; --apply writes flags.json.
    python rollout.py                 # who gets the candidate at the current rollout_percent
    python rollout.py --rollback "cost per question up 60%" --apply
"""
import argparse, json, sqlite3
from datetime import datetime
from pathlib import Path

import prod_tools as p

HERE = Path(__file__).parent
ap = argparse.ArgumentParser(); ap.add_argument("--rollback"); ap.add_argument("--apply", action="store_true")
a = ap.parse_args()
flags = json.loads((HERE / "flags.json").read_text())
users = [r[0] for r in sqlite3.connect(HERE / "usage.db").execute("SELECT DISTINCT user FROM events ORDER BY 1")]
got = [u for u in users if p.pick_version(u, flags) == flags.get("candidate")]
print(f"live {flags['live']}, candidate {flags['candidate']} at {flags['rollout_percent']}%: {len(got)} of {len(users)} users get the candidate")
print("  they are:", ", ".join(got) or "nobody")
if a.rollback:
    new = p.rollback(flags, a.rollback, datetime.now().isoformat(timespec="seconds"))
    print(f"rollback: rollout {flags['rollout_percent']}% -> {new['rollout_percent']}%, live stays {new['live']}; history now has {len(new['history'])} entry")
    if a.apply:
        (HERE / "flags.json").write_text(json.dumps(new, indent=2)); print("flags.json updated")
    else:
        print("Dry run: add --apply to write flags.json")
