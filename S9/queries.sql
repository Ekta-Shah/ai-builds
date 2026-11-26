-- Read-only queries on usage.db. Tables: events(id, ts, user, store, q_hash, decision, cached, latency_ms, tokens_in,
-- tokens_out, cost_inr, ok, version) and logins(id, ts, user). ts looks like '2026-10-12 09:30:00'.
-- Week = strftime('%W', ts). Write one SELECT under each marker. Keep the markers.

-- Q1: how many different users asked at least one question in each week? Columns: week, askers. Sorted by week.

-- Q2: what does a question cost on each prompt version? Columns: version, questions, avg_cost (cost_inr averaged, rounded to 5 places). Sorted by version.

-- Q3: how many questions were asked on each of the first 7 days with any data? Columns: day, questions. Sorted by day, 7 rows.
