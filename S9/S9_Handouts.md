# S9 handouts: what to build, one page per stage

MESA PGP Cohort 4 | Term 2: Advanced AI | Session 9

Check each stage with `python test_prod.py`. Nothing needs a key except `attack.py`.

## Stage 1: cost control (10 minutes)

In `prod_tools.py`:

- `SpendGuard(daily_cap_inr, user_cap_inr)`. `allow(user, est_cost)` is True unless adding the cost would take the day's total or that user's total MORE THAN its cap (equal is allowed). `record(user, cost)` adds the real cost. `reset()` starts a new day.
- `trim_context(chunks, budget_tokens, keep)`. Tokens are estimated as `ceil(len(text) / 4)`. Keep the chunks named in `keep` always, then add the others in order while they fit; skip one that does not fit and try the next. Return the chosen chunks in their original order.

Then fill `budget.json` and run `python cost_report.py`. In `cost_sheet.xlsx` fill the yellow cells with formulas: cost per question, per 1,000, the monthly cost at 1x, 5x and 50x against your ceiling, the volume where it breaks, and the cost after trimming and caching.

**Done when:** `stage 1 ok`; the report shows your numbers; the sheet has formulas, not typed totals.

## Stage 2: release (8 minutes)

- `load_config(env, config_dir, environ)`. `base.json` first, then `<env>.json` on top. `env` must be `dev`, `test` or `live`, else `ConfigError`. In `test` and `live` a missing or empty `GOOGLE_API_KEY` raises `ConfigError`. Return `has_key` (True or False), never the key. Add `env`.
- `pick_version(user_id, flags)`. The candidate if there is one and `bucket(user_id, salt) < rollout_percent`, else the live version. `bucket` is given.
- `rollback(flags, reason, now)`. Return a NEW dict: `rollout_percent` 0, one history entry `{"action": "rollback", "from": candidate, "reason": reason, "at": now}`, live unchanged. Do not change the dict you were given.

Then `python rollout.py` (who gets the candidate) and `python rollout.py --rollback "reason"` (a dry run; `--apply` writes `flags.json`).

**Done when:** `stage 2 ok`.

## Stage 3: monitoring and the bug hunt (17 minutes)

1. Fill `thresholds.json`: a threshold and an owner (a person) for usage, cost, reliability and quality. Do it before you open the data.
2. `log_event(con, ev)` in `prod_tools.py`. One row in `events`. Never store the question: `q_hash` is the first 12 hex characters of `sha256(redact(question))`. Use `?` placeholders.
3. In `queries.sql`, under each marker, one read-only SELECT:
   - Q1: users who asked at least one question each week. Columns `week`, `askers`. Week is `strftime('%W', ts)`.
   - Q2: for each prompt version, the number of questions and the average cost, rounded to 5 places.
   - Q3: questions per day for the first 7 days with data.
4. Run `python monitor.py`. Compare its adoption numbers with your Q1. One of them is wrong. Find the line, fix it, explain the diff.
5. Write `incident.md`: what the report showed, what was true, the cause, the fix. One or two lines each, with numbers.

**Done when:** `stage 3 ok`.

## Stage 4: security (17 minutes)

1. `redact(text)` in `prod_tools.py`: emails to `[EMAIL]`, PAN to `[PAN]`, 12-digit Aadhaar to `[AADHAAR]`, Indian mobile numbers (9876543210, 98765 43210, +91 98765 43210) to `[PHONE]`. Rupee amounts such as 2,48,969, store ids, dates and order ids must come back unchanged.
2. `python attack.py --impl weak_assistant.py`. Note the score. Patch ONE weakness:
   - A: scope in code. Replace the open database connection with `scope.run(stores, sql)`.
   - B: take the secret out of the system prompt.
   - C: escape the reply: `html.escape(text)`.
3. Run `attack.py` again. Write the score before and after, and what the patch was.

**Done when:** `stage 4 ok` and a before and after score.

## Your verdict: five lines

1. Cost: It costs Rs __ a question; Rs __ a month at 1x, __ at 5x, __ at 50x; the ceiling breaks at __ a day.
2. Release: v2 went to __% of users; I would / would not widen it because __.
3. Monitoring: the bug was __; the report said __ and the truth was __.
4. Security: I attacked it __ ways; __ held; I patched __ and it went from __ to __.
5. Weakest point: what I still do not know is __.

## Commit (tonight)

```
git checkout -b s9
git add prod_tools.py queries.sql monitor.py incident.md thresholds.json budget.json cost_sheet.xlsx
git status
git commit -m "S9: production layer"
```

If you are stuck, the finished `prod_tools.py` is on the `solutions` branch: `git fetch origin solutions`, then `git checkout origin/solutions -- prod_tools.py`.
