"""Weekly monitoring report for the store analytics assistant. Reads usage.db (read-only).
    python monitor.py            # prints the four metric families per week and any alerts
Fill thresholds.json first. THIS SCRIPT HAS A FAULT: the adoption number looks plausible and is wrong."""
import json, sqlite3, sys
from pathlib import Path

HERE = Path(__file__).parent
TOTAL_USERS = 36


def connect():
    return sqlite3.connect(f"file:{HERE / 'usage.db'}?mode=ro", uri=True)


def weekly_active(con, week):
    """Managers who used the assistant in this week (strftime('%W') week number, e.g. '43')."""
    return con.execute("SELECT COUNT(DISTINCT user) FROM logins WHERE strftime('%W', ts) = ?", (week,)).fetchone()[0]


def adoption_pct(con, week):
    return 100.0 * weekly_active(con, week) / TOTAL_USERS


def cost_per_question(con, week):
    return con.execute("SELECT AVG(cost_inr) FROM events WHERE strftime('%W', ts) = ?", (week,)).fetchone()[0]


def error_rate_pct(con, week):
    return con.execute("SELECT 100.0 * SUM(1 - ok) / COUNT(*) FROM events WHERE strftime('%W', ts) = ?", (week,)).fetchone()[0]


def unhelpful_pct(con, week):
    """Quality proxy: share of questions the assistant could not answer with SQL (it asked to clarify or refused)."""
    return con.execute("SELECT 100.0 * SUM(decision != 'sql') / COUNT(*) FROM events WHERE strftime('%W', ts) = ?", (week,)).fetchone()[0]


def alerts(row, th):
    out = []
    if row["adoption_pct"] < th["adoption_min_pct"]:
        out.append(f"usage: adoption {row['adoption_pct']:.0f}% is below {th['adoption_min_pct']}% (owner: {th['owners']['usage']})")
    if row["cost_per_q"] > th["cost_per_q_max_inr"]:
        out.append(f"cost: Rs {row['cost_per_q']:.4f} a question is above Rs {th['cost_per_q_max_inr']} (owner: {th['owners']['cost']})")
    if row["error_pct"] > th["error_rate_max_pct"]:
        out.append(f"reliability: errors {row['error_pct']:.1f}% above {th['error_rate_max_pct']}% (owner: {th['owners']['reliability']})")
    if row["unhelpful_pct"] > th["unhelpful_max_pct"]:
        out.append(f"quality: unhelpful {row['unhelpful_pct']:.0f}% above {th['unhelpful_max_pct']}% (owner: {th['owners']['quality']})")
    return out


def main():
    th = json.loads((HERE / "thresholds.json").read_text())
    missing = [k for k, v in th.items() if v is None] + [f"owners.{k}" for k, v in th["owners"].items() if v is None]
    if missing:
        sys.exit("Fill these in first (thresholds.json): " + ", ".join(missing))
    con = connect()
    weeks = [r[0] for r in con.execute("SELECT DISTINCT strftime('%W', ts) FROM events ORDER BY 1")]
    print(f"{'week':>5} {'adopt%':>7} {'Rs/q':>8} {'err%':>6} {'unhelp%':>8}")
    for w in weeks:
        row = dict(adoption_pct=adoption_pct(con, w), cost_per_q=cost_per_question(con, w), error_pct=error_rate_pct(con, w), unhelpful_pct=unhelpful_pct(con, w))
        print(f"{w:>5} {row['adoption_pct']:>7.0f} {row['cost_per_q']:>8.4f} {row['error_pct']:>6.1f} {row['unhelpful_pct']:>8.0f}")
        for a in alerts(row, th):
            print("   ALERT", a)


if __name__ == "__main__":
    main()
