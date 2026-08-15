# Quality Checks Reference

Detailed definitions for the checks listed in `SKILL.md`. Read this before running checks, on every invocation.

Each check below states: what it verifies, what counts as valid evidence, and how to score PASS / WARN / FAIL.

## 1. Schema

- **Verifies:** every column the contract expects is present; no column silently disappeared compared to the contract or a prior known-good schema.
- **Evidence:** the actual column list, diffed against the expected list. Name any missing or unexpected columns explicitly.
- **Scoring:** missing an expected column → FAIL. Extra/unexpected column with no data impact → WARN. Exact match → PASS.

## 2. Freshness

- **Verifies:** the dataset's load/update timestamp is within the contract's max-age threshold.
- **Evidence:** the actual timestamp value and the computed age (e.g. "load_timestamp = 2026-08-01T10:00Z, age = 26h, threshold = 24h").
- **Scoring:** older than threshold → FAIL if the contract marks freshness as hard, otherwise WARN. No timestamp column found → WARN and say so. Within threshold → PASS.

## 3. Expected volume

- **Verifies:** row count against the contract's minimum/expected count.
- **Evidence:** the actual row count vs. the expected/minimum count.
- **Scoring:** below minimum → FAIL. Below expected but at/above minimum (if the contract distinguishes the two) → WARN. At or above expected → PASS.

## 4. Key uniqueness

- **Verifies:** the designated key column has no duplicate values.
- **Evidence:** count of duplicate key values and at least one example (row numbers or key values) if any exist.
- **Scoring:** any duplicate key → FAIL (this is a hard rule). No duplicates → PASS.

## 5. Duplicates

- **Verifies:** no full-row duplicates beyond key duplication (i.e., two rows identical across all columns).
- **Evidence:** count of duplicate rows and example row numbers.
- **Scoring:** any full-row duplicates → WARN unless the contract specifies otherwise. None → PASS.

## 6. Required fields

- **Verifies:** contract-designated required fields are non-empty on every row.
- **Evidence:** per-field blank/null count and example offending row numbers.
- **Scoring:** any blank in a required field → FAIL (hard rule). All populated → PASS.

## 7. Nulls

- **Verifies:** null/blank rate in required and key fields, and broader null rates the contract flags.
- **Evidence:** null count and rate (%) per field checked.
- **Scoring:** nulls in required/key fields → FAIL (covered by check 6, but report the rate here too). Elevated null rate in a non-required field the contract flags → WARN. Otherwise → PASS.

## 8. Numeric rules

- **Verifies:** contract-defined numeric constraints (e.g. must be positive, within a range, non-zero).
- **Evidence:** count of violating rows and example offending values with row numbers.
- **Scoring:** any violation of a contract-stated numeric rule → FAIL (hard rule). No violations → PASS.

## Generic fallback checks (no contract found)

When no quality contract exists, state that explicitly in the output, then run:

- Schema present (columns are readable, non-empty header).
- No duplicate values in any column that looks like a key (e.g. named `*_id`, `id`, or the first column).
- No nulls in columns that look required/key-like.
- No negative values in columns that look numeric/amount-like (e.g. named `*_amount`, `*_revenue`, `*_price`, `*_qty`).

Flag these as generic best-effort checks in the output evidence, not contract-verified rules, so the reader knows the bar is lower than a real contract.
