# S7: Pick a model

Benchmark three Gemini models on your own Dhruva cases, choose one by a rule you write first, and price it at 1x, 5x and 50x volume.

## Setup (same environment as S6)

```
cd ai-builds && git pull && cd S7
source .venv/bin/activate          # Windows: .venv\Scripts\activate
cp .env.example .env               # paste GOOGLE_API_KEY=...
python test_bench.py               # four lines saying "not written yet" is correct
python -c "from google import genai; c = genai.Client(); [print(m.name) for m in c.models.list()]"
```

## What is here

| File | What it is |
|---|---|
| `dhruva_agent/` | The agent under test. The model comes from `DHRUVA_MODEL`; `bench.py` sets it |
| `bench_cases.csv` | 20 cases in three buckets (obvious, borderline, differs); 5 are held back. You add 5 of your own |
| `rule.json` | Your decision rule: write it before any run |
| `prices.json` | Per-model USD per million tokens and the exchange rate. You fill it from the live price sheet |
| `bench_tools.py` | Seven functions you write in stages 2 to 5 (the finished file is on the `solutions` branch) |
| `test_bench.py` | Tests for your functions. No key needed |
| `bench.py` | Runs one model over the cases, and prints the report and decision |

## Five stages

1. **Cases and rule.** Add 5 rows to `bench_cases.csv`; fill every field of `rule.json`.
2. **Reliability.** Write `backoff_call`. Test: `python test_bench.py` prints stage 2 ok.
3. **Measure.** Write `p95`, `cost_inr`, `bucket_scores`; fill `prices.json` from https://ai.google.dev/gemini-api/docs/pricing.
4. **Decide.** Write `decide`.
5. **Rupees.** Write `monthly_cost` and `volume_at_ceiling`.

Between stages 3 and 4, run the three models:

```
python bench.py --model <lite-model> --rpm 12
python bench.py --model <flash-model> --rpm 12
python bench.py --model <pro-model> --rpm 12
python bench.py --report
```

## If you are stuck

```
git fetch origin solutions
git checkout origin/solutions -- bench_tools.py
```

| Problem | Fix |
|---|---|
| 404 or model not found | Use a model name exactly as your key lists it |
| 429 or RESOURCE_EXHAUSTED | A limit. `backoff_call` waits; lower `--rpm`; pair up |
| `report` says fill these in first | `rule.json` or `prices.json` still has null |
| Every reply says ERROR | A bad key or a wrong model name (not retried) |
