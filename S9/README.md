# S9: run it in production: cost, release, monitoring and security

You wrap the store analytics assistant from S8 with the four things that make it safe to run. Each stage is a short function with a test. No key is needed for the tests.

| File | What it is |
|---|---|
| `prod_tools.py` | Your work: stage 1 (`SpendGuard`, `trim_context`), stage 2 (`load_config`, `pick_version`, `rollback`), stage 3 (`log_event`), stage 4 (`redact`). `monthly_cost` and `volume_at_ceiling` are given. |
| `test_prod.py` | `python test_prod.py` prints "stage N ok" for each stage you have finished. |
| `make_usage_log.py` | Builds `usage.db`: six weeks of synthetic logs (no model was called). Run once. |
| `queries.sql` | Stage 3: write three read-only SELECTs. |
| `monitor.py` | Stage 3: the weekly monitoring report. It has a fault. Find it. |
| `thresholds.json` | Fill in a threshold and an owner for each of four metrics before `monitor.py` will run. |
| `incident.md` | Stage 3: the incident note. |
| `budget.json`, `cost_report.py`, `cost_sheet.xlsx` | Stage 1: cost at 1x, 5x and 50x, in code and in a spreadsheet with formulas. |
| `config/`, `flags.json`, `versions.json`, `prompts/`, `rollout.py` | Stage 2: environments, versions and a staged rollout. |
| `attacks.csv`, `attack.py`, `weak_assistant.py`, `scope.py` | Stage 4: attack the assistant you inherited, then patch one weakness. `scope.py` is the fix kit. |

Setup (the S8 folder must already work):
```
cd S9
source ../S8/.venv/bin/activate        # or create a new venv and pip install google-genai pydantic
cp .env.example .env                    # paste your key after GOOGLE_API_KEY=
python make_usage_log.py
python test_prod.py
```
`attack.py` needs the S8 `retail.db`: run `python make_data.py` in your S8 folder if you have not.
