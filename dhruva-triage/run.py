import argparse
import json
from pathlib import Path

import config
import cost
import guard
import llm
import loader
import score


def run(path):
    apps = loader.load(path)
    best = 0
    rows = []
    for app in apps:
        reply = llm.assess(app["id"], str(app))
        verdicts = reply["criteria"]
        raw = score.raw_score(verdicts)
        best = max(best, raw)
        fit = round(raw / best * 10, 1)
        gaps = score.missing(verdicts)
        term = guard.anti_thesis(app)
        rec = score.recommend(fit, len(gaps), term)
        inr = cost.cost_inr(reply["tokens_in"], reply["tokens_out"])
        rows.append({"id": app["id"], "name": app["name"], "fit": fit, "rec": rec,
                     "could_not_establish": gaps, "cost_inr": round(inr, 2)})
        Path("reports").mkdir(exist_ok=True)
        Path("reports", app["id"] + ".json").write_text(json.dumps({**rows[-1], "criteria": verdicts}, indent=1))
    print(f"{'application':14}{'fit':>5}  recommendation")
    for r in sorted(rows, key=lambda r: -r["fit"]):
        print(f"{r['name']:14}{r['fit']:>5}  {r['rec']}")
    avg = sum(r["cost_inr"] for r in rows) / len(rows)
    print(f"cost per application: Rs {avg:.2f} (ceiling Rs {config.COST_CEILING_INR}); "
          f"projected quarter ({config.QUARTERLY_VOLUME} apps): Rs {avg * config.QUARTERLY_VOLUME:,.0f}")
    Path("runs").mkdir(exist_ok=True)
    with open("runs/run_log.jsonl", "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps", default="data/applications.csv")
    run(ap.parse_args().apps)
