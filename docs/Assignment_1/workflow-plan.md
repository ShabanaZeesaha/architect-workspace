# PowerBI Blueprint — Stakeholder Request Triage Workflow Plan

**Manual task this replaces:** reviewing stakeholder requests (emails, Teams
messages, sometimes an attached Excel report) for new Power BI reports or
changes to existing ones — currently read one at a time by hand.

## 1. Input

- **What:** stakeholder emails, Teams messages, and occasionally an attached
  Excel report, describing a new report or a change to an existing one.
- **Where it lives:** the analyst saves or pastes each request as a plain
  text file into a designated `requests/` folder before running the tool —
  the same mechanic `inbox-triage` already uses. No live inbox/Teams
  integration is required to get started; that can come later once the
  manual-export version proves useful.
- **Volume:** varies request to request — the tool processes whatever is in
  the folder on a given run, no fixed batch size assumed.

## 2. Structured output per request

The same categories the analyst already extracts by hand, as named fields:

`business_objective`, `kpis_and_calculations`, `dimensions`, `filters`
(kept separate from dimensions, not combined), `required_data_sources`,
`report_pages_or_visuals`, `priority` (High/Medium/Low),
`missing_or_unclear_requirements`, `questions_for_stakeholder`, `status`
(`ready_to_move_forward` / `needs_human_review`), and `confidence` (0–1,
the model's own self-assessment — a secondary signal, not the primary gate).

## 3. Runs across the whole folder

Every request file in the folder gets processed in one run: a progress line
per request, one retry on a failed call, the run keeps going if a single
request fails (recorded, not fatal), and a final count of
succeeded/failed/elapsed time/tokens used — the same resilience shape as
`triage_all.py`.

## 4. Quality bar (the gate)

The primary gate is the same rule the analyst already applies by hand, not
just a raw confidence number: a request is **`needs_human_review`** if any
of the following is missing or ambiguous — business objective, calculation
logic, required data source, field mapping (dimensions/filters), priority,
or stakeholder approval. Confidence acts only as a secondary safety net on
top of that rule — a request that technically passes the rule check but
still comes back low-confidence gets flagged too, the way `msg12` was
caught in the inbox-triage run despite passing on paper. Everything else is
**`ready_to_move_forward`**.

**Hard boundary:** the tool never approves a request or makes a final
business decision. "Ready to move forward" means *enough confirmed
information exists to begin drafting requirements and a Power BI skeleton*
— not "approved." Every request, ready or not, still requires sign-off from
an authorized analyst or the stakeholder before work actually starts.

## 5. Deliverable

- A **log**, one row per request, recording every field above plus the gate
  decision and the reason for it.
- A **plain-English summary report** (same shape as `run_report.md`):
  total requests processed, how many are ready vs. need review, a
  breakdown by priority, the specific requests needing review and exactly
  why (including the questions to send back to each stakeholder), any
  processing failures, elapsed time, and token usage — written for someone
  who is never going to open the log.
