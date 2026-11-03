# dhruva-triage

First-pass triage for Dhruva Capital (Case 3): score each inbound application
against the six thesis criteria with a citation per criterion, apply the
anti-thesis list, say what could not be established, recommend, and log cost.

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # OFFLINE=1 needs no keys
python run.py            # reads data/applications.csv, writes reports/ and runs/run_log.jsonl
```

OFFLINE=1 reads canned model replies from fixtures/llm_responses.json. Company
names are fictional. Prices and the exchange rate in cost.py are illustrative.
