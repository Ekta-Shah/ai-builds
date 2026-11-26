# S9 jargon buster

MESA PGP Cohort 4 | Term 2: Advanced AI | Session 9

| Word | Plain meaning |
|---|---|
| Token | A word-piece. Models charge by tokens in and tokens out |
| Cost per question | Tokens in times price in, plus tokens out times price out, in rupees |
| Ceiling | The most you will spend a month. You choose it before you look at the bill |
| Flip point | The volume at which the bill reaches the ceiling and you must change something |
| Spend cap | A limit that blocks calls once a day's or a user's spend reaches it |
| Quota | How much one user or key is allowed to use |
| Trimming | Sending less context in each call |
| Cache, cache hit | Keeping an answer to reuse it. A hit is a question served from the cache with no model call |
| Config | Settings in a file (model name, prompt version, limits) that you can change without new code |
| Environment | dev (your laptop), test, live (real users). Each can have its own settings |
| Secret | A key or password. It lives in an environment variable, never in code or git |
| Rollout | Sending a new version to a share of users first |
| Hash | A fixed-length fingerprint of a text. The same input always gives the same hash |
| Rollback | Going back to the previous version in one step |
| Observability | Being able to tell from the outside what a system is doing |
| Log, metric, trace | A log records what happened. A metric is a number over time. A trace follows one request through the steps |
| Threshold | The line that turns a number into an alert |
| Owner | The named person who reads a metric and acts on an alert |
| p95 | The time that 19 out of 20 replies beat. The slow ones are what users remember |
| Incident note | A short record: what the report showed, what was true, the cause, the fix |
| PII | Personal data: names, phones, emails, ID numbers |
| Redaction | Replacing personal data with a tag before it is stored |
| Least privilege | Giving a tool only the access it needs: read-only, only the user's rows |
| Prompt injection | Text that tries to give the model new orders. It can come from the user or hide inside data |
| Attack surface | Every place an attacker could get input in |
