# Data Quality Report

**Skill used:** `data-quality-gate`
**Dataset:** `skill-lab/orders.csv`
**Contract:** `skill-lab/quality-contract.md`
**Run date:** 2026-08-03

| Check | Evidence | Status | Recommended Action |
|---|---|---|---|
| Schema | Columns present: `order_id, order_date, region, revenue, load_timestamp`. All contract-referenced columns (`order_id`, `region`, `revenue`, `load_timestamp`) exist; `order_date` is an unlisted extra column with no data impact. | WARN | None required — extra column is informational only. |
| Freshness | Contract requires `load_timestamp` < 24h old. Current time ≈ 2026-08-03T20:34. 11 of 12 rows have `load_timestamp` between 2026-08-03T08:15:00–08:26:00 (~12h old, within threshold). Row 12 (`ORD-1010`) has `load_timestamp` = 2026-07-31T09:00:00, ~83h old. | FAIL | Quarantine/re-stamp `ORD-1010`; confirm no other rows carry stale timestamps before publish. |
| Expected volume | 12 data rows vs. contract minimum of 10. | PASS | None. |
| Key uniqueness (`order_id`) | `ORD-1004` appears twice: row 5 (`load_timestamp=2026-08-03T08:18:00`) and row 11 (`load_timestamp=2026-08-03T08:24:00`), identical `region`/`revenue` otherwise. | FAIL | Deduplicate on `order_id`, keep single authoritative record, before publish. |
| Duplicates (full-row) | No two rows are identical across all columns — the `ORD-1004` pair differs by `load_timestamp`, so this is a key duplicate, not a full-row duplicate. | PASS | None. |
| Required fields (`region`) | Row 7 (`ORD-1006`) has a blank `region` value. | FAIL | Backfill or reject the row; do not publish with a blank required field. |
| Nulls | `region`: 1/12 rows blank (8.3%). No other required/key field has nulls. | FAIL (via required-fields rule) | Same as required-fields action above. |
| Numeric rules (`revenue > 0`) | Row 8 (`ORD-1007`) has `revenue = -55.00`. | FAIL | Confirm whether this is a legitimate refund/adjustment; if so it needs a separate schema/sign convention, not a raw negative in `revenue`. Exclude or correct before publish. |

## Overall Verdict: **FAIL**

## Recommendation: **BLOCK**

Four hard-rule violations were found: duplicate key (`ORD-1004`), a blank required field (`region` on `ORD-1006`), a numeric-rule violation (negative `revenue` on `ORD-1007`), and a stale `load_timestamp` (`ORD-1010`). Per the quality gate's hard-rule policy, any one of these is sufficient to block publish; four independent violations confirm the dataset is not safe to ship as-is.

Source data (`skill-lab/orders.csv`) was not modified during this check, per skill constraints.
