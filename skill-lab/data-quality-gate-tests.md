# data-quality-gate — Trigger Tests

Manual test prompts for verifying the `data-quality-gate` skill triggers on validation / publish-readiness requests and stays silent on ordinary SQL, metric, or dashboard-design requests.

## Should trigger the skill

1. "Can you validate `skill-lab/orders.csv` against the quality contract before we publish it?"
2. "Run a data quality check on this ETL output — is it safe to publish to the dashboard?"
3. "Is `skill-lab/orders.csv` ready to ship? Check it for duplicates, nulls, and schema drift."

**Expected output for each:** the skill loads `references/quality-checks.md`, then produces a `Check | Evidence | Status | Recommended Action` table covering at minimum schema, freshness, expected volume, key uniqueness, duplicates, required fields, nulls, and numeric rules (or states no contract was found and runs the generic fallback checks instead). Evidence cites concrete values (counts, row numbers, example offending rows) — not vague claims. Output ends with one overall verdict (PASS / WARN / FAIL) and one recommendation (PUBLISH / BLOCK), consistent with the scoring rules in `SKILL.md`. The source dataset file is not modified.

## Should NOT trigger the skill

1. "Write a SQL query to get total orders by region from `orders.csv`."
2. "Design a dashboard layout to show weekly revenue trends."
3. "Calculate the average order value metric from this dataset."

**Expected output for each:** the assistant answers the request directly (writes the SQL, proposes/builds the dashboard layout, computes the metric) without invoking `data-quality-gate` — no quality-check table, no PASS/WARN/FAIL verdict, no PUBLISH/BLOCK recommendation. The dataset being named or used as an input does not by itself justify running the gate.
