# Slice plan (each slice ends with a test run and a decision-log line)

| Slice | What gets built | Done when |
|---|---|---|
| 0 | Walking skeleton: question in, hard-coded answer out, eval harness runs | `eval_sql.py` runs end to end and scores near zero |
| 1 | Model writes SQL, code runs it read-only | lookup and aggregate cases pass |
| 2 | Scope in code: views per user, authorizer, timeout | all leak cases pass |
| 3 | Glossary in context, assumptions stated | ambiguous cases pass |
| 4 | Refuse and clarify behaviour | unanswerable cases pass |
| 5 | Narration, token and cost meter | tokens per question printed |
| 6 | Cache and cascade | load test shows fewer calls and failures |
