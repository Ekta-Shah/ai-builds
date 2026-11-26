"""Cost at 1x, 5x and 50x from budget.json, using monthly_cost and volume_at_ceiling. Fill budget.json first.
    python cost_report.py
Tokens come from your S8 meter (or the usage log); prices come from the live price sheet, converted to rupees per million tokens."""
import json, sys
from pathlib import Path
import prod_tools as p

b = json.loads((Path(__file__).parent / "budget.json").read_text())
missing = [k for k, v in b.items() if v is None]
if missing:
    sys.exit("Fill these in first (budget.json): " + ", ".join(missing))
per_q = (b["avg_tokens_in"] * b["price_in_inr_per_million"] + b["avg_tokens_out"] * b["price_out_inr_per_million"]) / 1e6
print(f"cost per question: Rs {per_q:.5f}   per 1,000: Rs {per_q * 1000:.2f}")
for m in (1, 5, 50):
    c = p.monthly_cost(per_q, b["queries_per_day"], m)
    print(f"{m:>3}x  {b['queries_per_day'] * m:>8,} a day   Rs {c:>12,.0f} a month   {'OVER the ceiling' if c > b['monthly_ceiling_inr'] else 'within the ceiling'}")
print(f"the bill reaches the ceiling at {p.volume_at_ceiling(per_q, b['monthly_ceiling_inr']):,.0f} questions a day")
print(f"value per answer Rs {b['value_per_answer_inr']}: cost is {per_q / b['value_per_answer_inr']:.1%} of the value; break-even if cost per answer reaches Rs {b['value_per_answer_inr']}")
