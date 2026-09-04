# Inbox Triage Run Report

**Run date:** 2026-09-04 01:21
**Messages processed:** 12
**Auto-cleared:** 8
**Needs human review:** 4
**Failed to process:** 0

## What this means

A message is auto-cleared when the model was confident (0.75 or higher) and did not flag it as high urgency. Anything with lower confidence, anything flagged high urgency, and anything that failed to process is held here for a person to check before it's treated as handled.

## By urgency

- High: 3
- Medium: 0
- Low: 9

## By category

- Outage: 2
- Billing: 2
- Sales: 0
- Internal: 5
- Vendor: 1
- Spam: 1
- Unclear: 1

## Needs human review (4)

### msg01.txt
- **Why flagged:** flagged high urgency
- **Summary:** Customer reports their checkout has been returning 500 errors for 40 minutes, blocking all orders and causing lost sales.
- **Suggested action:** Page on-call engineering to check platform/API status for this account, then reply within minutes with an acknowledgment and a call/bridge link for Priya.
- **Owner:** Engineering on-call / Incident Response (with Customer Support comms)
- **Confidence:** 0.95

### msg02.txt
- **Why flagged:** flagged high urgency
- **Summary:** Customer billed for wrong seat count for the third time this quarter, ignored twice, and is threatening to cancel and dispute charges if not resolved by Friday.
- **Suggested action:** Have a named billing/account manager phone Derek directly today, pull the last three invoices to confirm the seat-count error, issue a corrected invoice with a written explanation of the root cause, and confirm all before Friday to prevent cancellation and chargebacks.
- **Owner:** Billing / Account Management (with escalation to Customer Success leadership for retention)
- **Confidence:** 0.95

### msg03.txt
- **Why flagged:** flagged high urgency
- **Summary:** Payroll batch failed on payday, leaving ~140 employees unpaid with a hard bank cutoff this afternoon.
- **Suggested action:** Immediately page on-call IT/finance ops to phone Monica, diagnose the failed payroll batch, and reprocess or initiate a manual/off-cycle payment run before the bank's afternoon cutoff.
- **Owner:** IT operations (on-call) jointly with Finance Ops/Payroll
- **Confidence:** 0.93

### msg12.txt
- **Why flagged:** confidence 0.72 is below the 0.75 threshold
- **Summary:** Ilana is asking when this week's data will refresh on the shared dashboard so she can prep for a Wednesday marketing review.
- **Suggested action:** Check the dashboard/ETL refresh schedule and reply with the expected refresh time (before Wednesday), noting whether current figures are last week's.
- **Owner:** Data / Analytics (BI) team
- **Confidence:** 0.72

## Failures

None this run.

## Run stats

- Elapsed time: 47.2s
- Total input tokens: 10,639
- Total output tokens: 2,310
- Total tokens: 12,949
