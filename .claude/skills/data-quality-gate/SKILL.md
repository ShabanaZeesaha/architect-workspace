---
name: data-quality-gate
description: Use when the user explicitly asks to validate a dataset, CSV, ETL output, or query result, or to assess whether a dataset, dashboard, or report is ready to publish/ship (a "quality check" or "quality gate" on data). Checks the data against a quality contract (or generic defaults) and returns PASS, WARN, or FAIL with evidence and a PUBLISH or BLOCK recommendation. Do NOT use for ordinary requests to write or debug SQL, calculate or define a metric, or design/build a dashboard's layout or visuals — those are not sufficient triggers on their own, even when a dataset is involved. Only invoke when the actual ask is validation or publish-readiness.
---

# Data Quality Gate

## When to use this skill

- The user asks to **validate** a dataset, CSV, ETL output, or query result.
- The user asks whether a dataset, dashboard, or report is **ready to publish**, **safe to ship**, or wants a **quality check / quality gate** run on data.

**Not sufficient to trigger this skill on their own:** writing or debugging a SQL query, calculating or defining a metric, or designing/building a dashboard's layout or visuals — even if a dataset is named or attached. Handle those as ordinary requests. Only invoke this skill when the user's actual ask is validation or publish-readiness, not when a dataset merely appears as an input to some other task.

## Inputs

1. Require a dataset path from the user. If none is given, ask for one before proceeding — do not guess a file.
2. Look for a quality contract:
   - If the user supplies one, use it as-is.
   - Otherwise look for a `quality-contract.md` (or similar) alongside the dataset or in the same directory tree.
   - If no contract exists, state that and fall back to generic checks (schema present, no duplicate keys, no nulls in obviously key/required-looking columns, no negative values in obviously numeric/amount columns).

## Checks to run

Run every check that the contract defines, at minimum covering: schema, freshness, expected volume, key uniqueness, duplicates, required fields, nulls, and numeric rules.

**Before running checks, read `references/quality-checks.md`** — it defines each check, what counts as valid evidence, and PASS/WARN/FAIL thresholds. Read it every time this skill runs, not just the first time.

## Output

1. Present results as a table with columns: `Check | Evidence | Status | Recommended Action`.
   - Evidence must cite concrete values (row numbers, counts, example offending rows) — not vague claims.
   - Status is PASS, WARN, or FAIL per check.
2. Finish with one overall verdict: **PASS**, **WARN**, or **FAIL**.
3. Finish with one recommendation: **PUBLISH** or **BLOCK**.
   - Any FAIL on a hard rule (uniqueness, required fields, numeric validity) → overall FAIL → BLOCK.
   - Only WARNs (e.g. freshness borderline, volume slightly under) → overall WARN → PUBLISH with caveats, at the user's discretion.
   - All checks PASS → overall PASS → PUBLISH.

## Constraints

- Never modify the source data. This is a read-only check — do not write, clean, dedupe, or otherwise alter the dataset file.
- Stay concise and procedural: report findings, do not editorialize.
