# Incident note

What the report showed: adoption of 78% to 92% every week (28 to 33 of 36 managers), so nothing alerted.
What was true: only 12 to 28 managers asked a question in a week: 33% by week 46, down from 78% at launch.
Cause: monitor.py counted rows in the logins table, so anyone who opened the page counted as active.
Fix: weekly_active now counts distinct users in the events table (people who asked at least one question).
