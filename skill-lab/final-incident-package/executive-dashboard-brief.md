# Executive Incident Brief: Orders Dashboard Publish

**Date:** 2026-08-03
**System:** Orders dashboard / `orders_ingest_daily` pipeline
**Decision:** **BLOCK — do not publish**

## What happened

The orders dashboard was scheduled to publish today. Before publishing, the underlying data (`orders.csv`) was run through the automated data quality gate against its published contract. The dataset **failed** on four independent, hard-rule checks:

- A duplicate order record (`ORD-1004` counted twice)
- A required field left blank (order region missing on one record)
- An invalid negative value in the revenue field (one record at -$55.00)
- A stale record pulled in from a previously failed pipeline run, dated three days before the rest of the batch

## Why it happened

Triage of the pipeline's own run log and run metadata traced each issue to a specific, already-logged pipeline behavior from today's run (`orun-20260803-0812`):

- An upstream timeout-and-retry duplicated one order because the retry path has no duplicate-write protection.
- A data-validation warning for a missing region was logged but did not stop the record from passing through.
- A data-quality filter that should catch negative revenue values had been turned off by a configuration change the day before, and no alert caught it.
- A merge of leftover records from a prior failed run pulled in an old record without refreshing its timestamp.

Underlying all four: the pipeline's quality gate is not currently configured to block its own output on warnings — it logged all four problems and still reported success.

## Business impact and ownership

Not established by this incident's evidence. No financial impact figure, incident owner, or resolution time is available from the data or pipeline logs reviewed, and none is asserted here.

## Recommended next business action

Route this to the pipeline/data engineering team owning `orders_ingest_daily` for triage assignment and a fix, using the five technical follow-ups listed in `etl-triage-report.md` (idempotency check on retries, quarantine on missing required fields, alerting on validator config changes, timestamp refresh on backfill merges, and blocking the run on warning thresholds). Re-run the data quality gate against a corrected dataset before attempting to publish again.
