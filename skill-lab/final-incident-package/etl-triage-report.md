# ETL Triage Report

**Triggered by:** Data Quality Report verdict = FAIL / BLOCK
**Sources investigated:** `skill-lab/orders-pipeline-failure.log`, `skill-lab/pipeline-run-metadata.md`
**Pipeline:** `orders_ingest_daily`
**Run ID:** `orun-20260803-0812` (2026-08-03T08:10:02 – 08:26:40, exit_code=0)

## Root cause mapping

| Data quality finding | Root cause (from log/metadata) |
|---|---|
| Duplicate `order_id` (`ORD-1004`) | 08:18:41 — upstream request for `ORD-1004` timed out; the retry at 08:18:52 succeeded and was appended without an idempotency-key check on the retry path. The original in-flight write and the retried write both landed, producing two rows for the same order. |
| Blank `region` (`ORD-1006`) | 08:19:10 — schema validation logged `region` missing/null for records created via the upstream mobile-quickadd flow. The row was logged as a warning but passed through instead of being quarantined. |
| Negative `revenue` (`ORD-1007`, -55.00) | 08:19:40 — the `revenue_positive_filter` numeric validator was disabled for this run. Metadata shows the underlying config flag was reverted to `disabled` by a deploy at 2026-08-02T22:40 UTC, one day before this run, so the filter that should have caught (or routed) the negative value never ran. |
| Stale `load_timestamp` (`ORD-1010`) | 08:20:15–08:20:16 — this row came from a backfill merge of a prior failed run (`orun-20260731-old`, status: incomplete). The merge step carried the row's original `load_timestamp` forward instead of re-stamping it, so a 3-day-old record entered today's output looking like part of the current batch. |

## Contributing systemic gap

The run metadata confirms the pipeline's own quality gate was not wired to block on warnings: the run logged 4 warnings and 0 errors but still returned `exit_code=0`. All four issues above were observed and logged by the pipeline itself at run time — none were silent — but nothing in the pipeline stopped the output from being written and handed off as if it were clean.

## What the evidence does NOT establish

The log and metadata files do not contain a financial/business impact figure, a named incident owner, or a committed resolution time. None of those are stated here or anywhere downstream in this triage — they are not available from the investigated evidence and are not invented.

## Suggested technical follow-ups (for pipeline owners, not executed here per scope)

1. Add an idempotency key check to the retry path so a timeout-then-retry cannot double-write a record.
2. Quarantine (not pass-through) any row failing a required-field check.
3. Alert on config changes that disable a data-quality validator (`revenue_positive_filter`), and add a rollback/approval gate for such changes.
4. Re-validate and re-stamp `load_timestamp` on any row entering the output via a backfill/recovery merge.
5. Change the pipeline's exit condition so warnings above a defined threshold cause a non-zero exit / block downstream publish, rather than exit_code=0 regardless of warning count.

No pipeline files were modified as part of this triage, per scope constraints.
