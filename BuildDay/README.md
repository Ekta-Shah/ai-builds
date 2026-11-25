# Build day: a store analytics assistant, from one line to a product

Problem statement: "Store managers ask a question in plain English and get a trusted number."

| File | What it is |
|---|---|
| `make_data.py` | Builds `retail.db`: 12 stores, 60 products, about 220,000 sales lines. Run `python make_data.py` once. |
| `glossary.md` | Table and metric definitions. This is the semantic layer. |
| `users.json` | Four users and the stores each may see. |
| `golden_questions.csv` | 28 questions with a gold query or a pass pattern. 6 are held back (`holdout` = 1). |
| `eval_sql.py` | Scores any `answer(question, user)` function. |
| `load_test.py` | Fires many questions at once and reports throughput, p95, failures and cache hits. |
| `templates/` | PRD, architecture, decision log, a `CLAUDE.md` for your coding agent, and a slice plan. |

A working reference build is on the `solutions` branch. Open it only after your own version has a score.

Setup:
```
python -m venv .venv && source .venv/bin/activate
pip install google-genai pydantic
cp .env.example .env     # paste your key after GOOGLE_API_KEY=
python make_data.py
```
Your function must be `answer(question, user) -> dict` with keys `rows` (list of tuples), `text` (string), `tokens_in`, `tokens_out`.
Score it: `python eval_sql.py --impl yourfile.py`.
