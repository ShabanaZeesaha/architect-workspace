# Pipeline Run Metadata: orders_ingest_daily

- **Run ID:** orun-20260803-0812
- **Job:** orders_ingest_daily
- **Trigger:** scheduled (daily cron, 08:10 UTC)
- **Upstream source:** orders_api_v2 (primary), failed_run_recovery merge from orun-20260731-old (backfill segment)
- **Target output:** skill-lab/orders.csv
- **Start:** 2026-08-03T08:10:02
- **End:** 2026-08-03T08:26:40
- **Exit code:** 0 (success) — no failure was raised despite warnings below
- **Rows fetched:** 10 (primary batch) + 2 (backfill merge) = 12 written
- **Warnings emitted:** 4
- **Errors emitted:** 0
- **Related config change:** `revenue_positive_filter` validator flag was reverted to `disabled` by a deploy at 2026-08-02T22:40:00 UTC, prior to this run.
- **Related prior run:** orun-20260731-old (status: incomplete/failed) — its unprocessed rows were merged into this run's output without re-validation or timestamp refresh.

## Known gaps in this run

- No idempotency key check on the retry path (upstream timeout retry can duplicate a row).
- No quarantine/reject path for null values in contract-required fields.
- `revenue_positive_filter` was silently disabled at the config level; no alert fired.
- Backfill merge does not re-stamp `load_timestamp` on carried-forward rows.
- Downstream quality gate was not configured to block the run on warnings (exit_code=0 regardless of warning count).
