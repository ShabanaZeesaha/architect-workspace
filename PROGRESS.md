# Progress

## 2026-07-30 — Foundation architecture approved
- Reviewed existing structure (`src/`, `tests/`, `requirements.txt`) against
  `CLAUDE.md` rules; confirmed it already conforms.
- Proposed and approved a folder architecture: no new top-level folders
  were needed — `src/`, `tests/` already exist; `.venv/` is tool-generated;
  `.env` is deferred until Supabase integration work actually starts.
- Documented the approved architecture in `ARCHITECTURE.md`.
- Open items: project definition (requirements/brief) not yet located;
  Week 3 component name/purpose not yet known.

## 2026-08-24 — STORY-001: Request intake, AI analysis, and audit trail
- Added durable request intake backed by SQLite (`src/request_intake.py`),
  replacing in-memory storage — requests and audit entries now survive a
  process restart, verified by reopening the database in a fresh instance.
- Added AI analysis of email-based requests (`src/email_analysis.py`) using
  the configured Claude Haiku model, extracting business objectives, scope,
  KPIs, filters, calculations, visual requirements, and reporting
  expectations from the raw request text.
- Added Excel report analysis (`src/excel_analysis.py`), extracting the same
  seven categories from worksheet names, headers, formulas, and labeled
  cells.
- Wired both analysis paths into Flask endpoints (`POST /requests` for email,
  `POST /requests/excel` for file upload) with lifecycle statuses: `intake`
  on submission, `analyzed` on successful analysis, `analysis_failed` on a
  corrupt/unsupported file or an invalid/unavailable model response — the
  original request record is always preserved, never deleted, on failure.
- Every request submission and analysis completion/failure writes a
  timestamped (timezone-aware UTC) audit entry with the analyst ID; failure
  entries carry a safe error category only, never raw model output, file
  paths, or file contents.
- Ran one live smoke test against the real Anthropic API (Claude Haiku, one
  request, a fictional Power BI request) confirming authentication, all
  seven analysis fields, persisted `analyzed` status, and a correct
  `analysis_completed` audit entry — then deleted that test data from the
  local dev database.
- Verification: 21 automated tests passing (`pytest tests/`), covering happy
  paths, corrupt/unsupported files, invalid model responses, simulated API
  failures, and SQLite persistence across process restarts. All external
  API calls in the test suite are mocked — no test spends API credits or
  requires `ANTHROPIC_API_KEY`.

## 2026-09-03 — STORY-003: Requirement clarification (REQ-004)
- Added `src/requirement_clarification.py`: `find_missing_fields()` and
  `generate_followup_questions()` deterministically detect which of the
  seven required analysis fields (`business_objectives`, `scope`, `kpis`,
  `filters`, `calculations`, `visual_requirements`,
  `reporting_expectations`) are empty on an already-analyzed request, and
  return one plain-English follow-up question per missing field — no model
  call needed, since `analyze_email()`/`analyze_report()` already return an
  empty list for anything the source didn't state.
- Wired this into a new `POST /requests/<id>/clarify` endpoint
  (`src/app.py`): 404 for an unknown request, 400 if the request hasn't
  been analyzed yet, 400 `invalid_analysis` if the stored analysis is
  malformed; otherwise returns the follow-up questions (empty list when
  the requirement is already complete).
- Every call to `/clarify` — whether it generates questions or not —
  writes an audit entry (`clarification_questions_generated` or
  `clarification_not_needed`) via a new `RequestIntake.record_clarification()`
  method, so every clarification interaction is traceable, not just the
  ones that found a gap.
- Refactored the audit log itself out of `src/request_intake.py` into a new
  `src/audit_trail.py` (`AuditTrail`/`AuditEntry`) — `request_intake.py`
  was already at 211 lines (over this repo's 200-line file cap) before this
  change, so the split was required before adding `record_clarification()`,
  not optional cleanup. Writes still share the caller's transaction (the
  audit insert happens inside the same `with conn:` block as the request
  state change), preserving the existing atomicity guarantee.
- Fixed a pre-existing schema mismatch discovered while building this:
  `src/excel_analysis.py` returned the objectives field as `"objectives"`
  while `src/email_analysis.py`'s `REQUIRED_FIELDS` (used everywhere else)
  expects `"business_objectives"`. Left alone, every Excel-sourced request
  would have failed clarification with `invalid_analysis`, or silently
  flagged a stated objective as missing. Renamed the Excel-side key to
  match; updated `tests/test_excel_analysis.py` accordingly.
- Verification: 58 automated tests passing (`pytest tests/`), up from 21 —
  covers missing-field detection, complete-requirement (no questions)
  detection, malformed-analysis input, the new endpoint's 404/400 paths,
  audit-trail logging (including repeated calls each writing their own
  entry), and the Excel-sourced path exercising the same field schema as
  email. All external API calls remain mocked.

## 2026-09-04 — capture-request prompt v1.0.0: evaluation documented, known limitations accepted

- Built the first prompt-library entry end to end: `prompts/capture-request/v1.0.0.md`
  (rung 2 — role/task/audience plus format, constraints, and edge-case rules; no XML
  tags, examples, or scratchpad), `prompts/capture-request/eval.jsonl` (5 confirmed
  test cases — 4 ordinary, 1 deliberately awkward), and a scoring harness
  (`docs/Assignment_1/scripts/score_prompt.py`) that fills each case into the prompt,
  calls Claude, extracts JSON from the reply, and grades only the fields named in
  `expected`.
- Fixed a real bug in the harness along the way: `ask_claude` called
  `response.content[0].text` unconditionally; on `claude-sonnet-5` with adaptive
  thinking on by default, `content[0]` can be a `ThinkingBlock`, which has no `.text`,
  crashing every run. Now collects only `type == "text"` blocks.
- Latest scored run: **0/5 (strict — every field in `expected` must match exactly)**.
- What actually improved across two prompt revisions: `status`, `metrics`,
  `dimensions`, `filters`, `priority`, and `source_system` now match the expected
  value exactly in 4 of 5 cases; the deliberately awkward case (case 5) matches on
  6 of 7 fields, including correctly distinguishing `needs_clarification` from
  `not_a_request`, and correct `null`-vs-`[]` typing on fields it can't determine.
- Remaining failures, by cause:
  - **Prompt-fixable:** case 2's `metrics` returns `"Employee headcount"` instead of
    `"Headcount"` — the same class of naming-padding issue the `source_system`
    normalization rule already fixed for a different field.
  - **Ground-truth inconsistency, not a prompt gap:** `business_question` fails in
    4 of 5 cases. Case 1's expected answer abstracts away the specific breakdown
    ("...over time"); cases 3 and 4's expected answers keep it ("...by cost center",
    "...by priority level"). No single prompt rule can produce both conventions.
  - **Scorer-strictness limit, not a prompt gap:** the `business_question` failures
    are also structural — this harness does plain case/whitespace-insensitive string
    equality on text fields, with no tolerance for a correct paraphrase. Case 5's
    `clarification_needed` fails the same way: correct content, wrong exact wording
    and count against one fixed human-written list, since list comparison here
    requires exact equality rather than order/content-insensitive matching.
- Why we stopped instead of moving to rung 3/4/5: rung 3 (XML tags) addresses
  input/instruction confusion, not paraphrase variance. Rung 4 (examples) would
  anchor the model to one `business_question` convention, fixing some cases while
  breaking others, since the ground truth itself uses two conventions. Rung 5
  (decomposition) targets reasoning depth on hard problems — the model already
  extracts the correct underlying facts (proof: 6 of 7 fields are correct in 4-5 of
  5 cases); the gap is free-text wording determinism, which more reasoning doesn't fix.
- Recommended future improvements (not applied in this pass — `eval.jsonl` and
  `score_prompt.py` were explicitly out of scope): (1) apply the metrics-naming
  tightening rule above; (2) resolve the case-1-vs-3/4 `business_question`
  convention with a reviewer, and update either the prompt rule or the expected
  answers so they're internally consistent; (3) if a hard 5/5 gate is needed later,
  that requires loosening the scorer's text-field comparison (e.g. reusing the
  order/case-insensitive list matching already implemented in the other
  `score_prompt.py` copy at the repo root) or a fuzzier grading method for free-text
  fields — not a prompt change.
- Status: `prompts/capture-request/v1.0.0.md` remains `status: draft`. Mentor
  confirmed 5/5 is not required; goal was documented evaluation and learning, which
  this entry satisfies.
- Verification: `python scripts/score_prompt.py prompts/capture-request/v1.0.0.md
  prompts/capture-request/eval.jsonl`, run from `docs/Assignment_1`, 2026-09-03/09-04.
  No changes made to `eval.jsonl` or either `score_prompt.py` copy.

## 2026-09-04 — STORY-005: Design recommendation generation (REQ-005, REQ-011)
- Added `src/design_recommendation.py`: `generate_design_recommendations()`
  calls the configured Claude Haiku model to recommend a data model,
  relationships, transformations, validation checks, KPI definitions, DAX
  measures, report pages, slicers, and visual design from an
  already-approved request's requirements and (optional) field mapping.
  Missing-field detection runs first and is deterministic — reuses
  `requirement_clarification.find_missing_fields()` — so an incomplete
  requirement is flagged and the model is never called on data it doesn't
  have.
- Wired this into a new `POST /requests/<id>/design-recommendations`
  endpoint (`src/design_recommendation_routes.py`), registered from
  `src/app.py` with an injectable client mirroring the existing
  `email_client` pattern. Every outcome — missing data, recommendations
  generated, or the model failing/returning garbage — writes one audit
  entry (`design_recommendations_missing_data`,
  `design_recommendations_generated`, or `design_recommendations_failed`),
  so recommendations are always traceable for human review, never
  auto-approved.
- Extracted `src/requirement_clarification_routes.py` out of `app.py`
  (behavior unchanged) because `app.py` was already at this repo's
  200-line cap before this story's route could be added — same split
  rationale as STORY-004's `field_mapping_routes.py`.
- Verification: 91 automated tests passing (`pytest tests/`), up from 83 —
  8 new route tests (happy path, field-mapping passthrough, missing-data
  flag with no model call, 404/400 paths, invalid model response,
  simulated API failure) and 7 new unit tests for the core module. All
  external API calls remain mocked.

## 2026-09-04 — STORY-006: Dashboard mockup generation (REQ-006)
- Added `src/dashboard_mockup_template.py`: defines this system's approved
  dashboard template as a deterministic contract — `APPROVED_VISUAL_TYPES`
  (bar_chart, line_chart, pie_chart, kpi_card, table, matrix, slicer, map,
  gauge), `validate_mockup_shape()` (is a model reply well-formed at all),
  and `find_template_violations()` (does an already-well-formed mockup
  actually comply — an unapproved visual type, or a page with no visuals).
  Split into its own module from the start, not as a later line-count fix,
  because REQ-006's "matches the approved template" acceptance criterion
  needed its own independently testable contract, distinct from AI-call
  orchestration.
- Added `src/dashboard_mockup.py`: `generate_dashboard_mockup()` builds a
  mockup from an already-generated design recommendation
  (`src/design_recommendation.py`, STORY-005). Missing-input detection runs
  first and is deterministic — a recommendation with empty `report_pages`
  or `visual_design` never reaches the model (`IncompleteRecommendationError`).
  A well-formed-but-non-compliant reply raises `MockupTemplateMismatchError`
  as an outcome distinct from `InvalidDashboardMockupResponseError`
  (malformed JSON/shape), matching the acceptance criteria's separate
  "generates a mockup" vs. "matches the approved template" conditions.
- Wired this into a new `POST /requests/<id>/dashboard-mockup` endpoint
  (`src/dashboard_mockup_routes.py`), registered from `src/app.py` with an
  injectable client mirroring the existing `design_recommendation_client`
  pattern. A design recommendation isn't persisted anywhere (STORY-005's
  endpoint only returns it, never stores it on the request record), so the
  recommendation is supplied directly in the request payload here rather
  than fetched from the stored record.
- Every outcome — missing data, mockup generated, template mismatch, or the
  model failing/returning garbage — writes one audit entry via
  `RequestIntake.record_clarification()` (`dashboard_mockup_missing_data`,
  `dashboard_mockup_generated`, `dashboard_mockup_template_mismatch`, or
  `dashboard_mockup_failed`).
- Hardened the audit write itself, scoped to this new route only: if
  `record_clarification()` raises `sqlite3.Error` (e.g. a locked or
  unwritable database), the route returns a controlled
  `500 audit_log_unavailable` instead of crashing on an unhandled exception
  or silently returning the original outcome as though it had been logged.
  The older AI-assisted routes (requirement clarification, field mapping,
  design recommendations) were left untouched — this was a targeted fix for
  the new route, not a repo-wide refactor.
- Verification: 123 automated tests passing (`pytest tests/`), up from 91 —
  11 new unit tests for the template contract, 12 for mockup generation, and
  9 new route tests (happy path with a full audit-event-order assertion,
  missing-data gate, 404, missing `analyst_id`/`recommendation`, invalid
  model response, template mismatch, simulated API failure, and the new
  audit-log-failure control path). All external API calls remain mocked.
- Acceptance criteria (exact portal wording, `.colaberry/progress.json`),
  all demonstrated by the tests above:
  - "Given a design recommendation, when processed, then the system
    generates a dashboard mockup." — happy-path route test.
  - "Given a mockup, when reviewed, then it matches the approved template."
    — `find_template_violations()` unit tests plus the route's
    template-mismatch test.
  - "Trust: The system logs mockup generation in the audit trail." —
    audit-event-order assertion in the happy-path route test, plus the new
    audit-log-failure control test.
- Note on `.colaberry/progress.json`: this same commit marks all three
  STORY-006 criteria passed and the story verified, but leaves
  `commit_sha`/`commit_url`/`commit_at` `null` — a commit cannot correctly
  record its own resulting hash inside itself (the hash is computed from
  the commit's content, so any value written inside it would necessarily be
  wrong, and this repo's `Trust` principle rules that out). Filling those
  three fields is a small, honest follow-up edit once this commit's real
  hash is known, same as STORY-005's `commit_sha` being filled in by a
  later commit (2b61456) referencing ef74b29's real hash.

## 2026-09-04 — STORY-007: Draft Power BI solution generation (REQ-007)
- Session: CC-20260904-r5fy
- Added `src/powerbi_solution_template.py`: defines the structural contract
  for a draft Power BI solution as its own deterministic module, reusing
  `APPROVED_VISUAL_TYPES` from `src/dashboard_mockup_template.py` rather
  than redefining it. `validate_solution_shape()` checks a model reply is
  well-formed (pages/visuals with an approved type, non-empty purpose, and
  a `field_bindings` list of non-empty strings). `find_mockup_alignment_violations()`
  is the new check this story needed: it diffs an already-well-formed
  solution against the specific dashboard mockup it was built from (same
  page titles/order, same visual types/order per page), which is what
  "aligns with the mockup" means as a testable condition — distinct from
  STORY-006's fixed-template compliance check, since this compares against
  one specific input rather than a static approved list.
- Added `src/powerbi_solution.py`: `generate_draft_powerbi_solution()`
  takes an already-generated STORY-006 dashboard mockup, re-validates its
  shape first (reusing `dashboard_mockup_template.validate_mockup_shape()`,
  raising `InvalidMockupInputError` with no model call on a malformed
  input), then calls the configured Claude Haiku model with a prompt that
  pins pages/visuals/types to exactly match the mockup and asks only for
  the DAX-measure/field bindings each visual needs, then runs shape
  validation and mockup-alignment checking in that order.
- Wired this into a new `POST /requests/<id>/powerbi-solution` endpoint
  (`src/powerbi_solution_routes.py`), registered from `src/app.py` with an
  injectable client mirroring the existing `dashboard_mockup_client`
  pattern. As with STORY-006, the mockup isn't persisted on the request
  record, so it's supplied directly in the request payload. Every outcome
  — invalid mockup input, solution generated, mockup mismatch, or the
  model failing/returning garbage — writes one audit entry
  (`powerbi_solution_invalid_mockup`, `powerbi_solution_generated`,
  `powerbi_solution_mockup_mismatch`, or `powerbi_solution_failed`), with
  the same `500 audit_log_unavailable` guard as STORY-006 if the audit
  write itself fails.
- Verification: 158 automated tests passing (`pytest tests/`), up from
  123 — 16 new unit tests for the template contract (shape validation plus
  six alignment-violation cases), 10 for solution generation (including
  the no-model-call-on-invalid-input case), and 9 new route tests (happy
  path with a full audit-event-order assertion, 404, missing
  `analyst_id`/`mockup`, invalid mockup input, invalid model response,
  mockup mismatch, simulated API failure, and the audit-log-failure
  control path). All external API calls remain mocked — no test spends API
  credits or requires `ANTHROPIC_API_KEY`.
- Acceptance criteria (exact portal wording, `.colaberry/progress.json`),
  all demonstrated by the tests above:
  - "Given a dashboard mockup, when processed, then the system generates a
    draft Power BI solution." — happy-path route test.
  - "Given a draft solution, when reviewed, then it aligns with the
    mockup." — `find_mockup_alignment_violations()` unit tests plus the
    route's mockup-mismatch test.
  - "Trust: The system logs draft generation in the audit trail." —
    audit-event-order assertion in the happy-path route test, plus the
    audit-log-failure control test.
- Files touched: `src/powerbi_solution_template.py` (new),
  `src/powerbi_solution.py` (new), `src/powerbi_solution_routes.py` (new),
  `src/app.py`, `tests/test_powerbi_solution_template.py` (new),
  `tests/test_powerbi_solution.py` (new), `tests/test_app.py`.
- Note on `.colaberry/progress.json`: this same commit marks all three
  STORY-007 criteria passed and the story verified, but leaves
  `commit_sha`/`commit_url`/`commit_at` `null` for the same reason as
  STORY-006 — a commit cannot correctly record its own resulting hash
  inside itself. Those three fields are a small follow-up edit once this
  commit's real hash is known.

## 2026-09-05 — STORY-008: Stakeholder Review Interface (REQ-013, REQ-012)
- Session: CC-20260905-k2vt
- Extended `src/lifecycle.py` with the review/approval stages this story
  needed: `in_review`, `changes_requested`, `approved`. `analyzed` gained a
  new legal transition to `in_review` alongside its existing direct path to
  `completed` (left untouched, so STORY-002's tests still pass unmodified);
  `in_review` can go to `approved` or `changes_requested`;
  `changes_requested` can only go back to `in_review` — a stakeholder must
  see the resubmitted draft again before approving it. `approved` has no
  outgoing transition yet; whatever comes after approval is STORY-009's
  concern (Data Validation and Finalization), not this one.
- STORY-006 and STORY-007 deliberately never persisted the dashboard
  mockup or draft solution on the request record (each route only returns
  what it generates). STORY-008's first criterion — stakeholders can
  access a draft later, a different actor at a different time — needed
  that data to actually be stored, so this story adds a `draft_solution`
  column to the `requests` table, migrated onto the existing dev database
  via an `ALTER TABLE` guard (not just `CREATE TABLE IF NOT EXISTS`, which
  doesn't touch a table that already exists on disk).
- Split `src/request_intake.py`'s table schema/migration and row-decoding
  logic into a new `src/request_schema.py` (`ensure_schema()`,
  `row_to_request()`, `fetch_request()`) — `request_intake.py` hit this
  repo's 200-line cap once the new column and a first pass at the review
  method landed, same split trigger as STORY-003's `audit_trail.py`
  extraction. Both `src/request_intake.py` and the new
  `src/stakeholder_review.py` share this module rather than duplicating
  table knowledge.
- Added `src/stakeholder_review.py`: `submit_draft_for_review()` persists a
  draft and moves the request to `in_review`, reusing the lifecycle
  `TRANSITIONS` map rather than a separate legality rule. `approve()` is
  the *only* code path in this system that can set a request's status to
  `approved` — no AI-calling code in this pipeline ever reaches it — which
  is what satisfies REQ-012's "AI must not finalize... without authorized
  human review and approval" guardrail as a testable condition, not just a
  policy statement. `request_changes()` requires non-empty feedback
  (raises `ValueError` otherwise) and stores it in the audit entry's
  existing `error_category` column — reused as a general free-text detail
  slot, the same way STORY-004's field-mapping audit entries and every
  AI-generation route's failure-detail logging already reuse it; no new
  column needed. Both `approve()` and `request_changes()` share a private
  `_transition()` helper (status-legality check + update + one audit
  entry); `submit_draft_for_review()` stays separate since it also writes
  the `draft_solution` column, a different `UPDATE` shape.
- Added `src/stakeholder_review_routes.py`:
  `POST /requests/<id>/submit-for-review` and
  `POST /requests/<id>/review` (`action`: `approve` | `request_changes`),
  registered from `src/app.py` alongside a new `StakeholderReview` instance
  in `app.config`. No new read endpoint was needed for "stakeholders can
  access it" — the existing `GET /requests/<id>` (`src/app.py`, unchanged)
  already returns the full record, which now includes `draft_solution`
  once a draft has been submitted for review. An illegal transition (e.g.
  approving a request that was never submitted for review) returns a
  controlled `409 invalid_transition` rather than a raw exception.
- Verification: 190 automated tests passing (`pytest tests/`), up from
  171 — 7 new unit tests for `request_schema.py` (schema creation, the
  migration path against a pre-existing table missing the column,
  idempotency, row decoding with/without optional fields, `fetch_request`
  happy path and unknown-id), 14 for `stakeholder_review.py` (all three
  methods' happy paths, illegal-transition and unknown-request-id
  rejections, empty-feedback rejection, and the audit-entry content
  assertions for both the approver-id/timestamp and the feedback-logging
  criteria), and 11 new route tests in `test_app.py` (submit-for-review
  happy path plus its 404/400/409 paths, approve and request-changes happy
  paths with audit-content assertions, missing-feedback and
  invalid-action 400s, and 404/409 on the review endpoint). All existing
  158 tests continue to pass unmodified.
- Acceptance criteria (exact portal wording, `.colaberry/progress.json`),
  all demonstrated by the tests above:
  - "Given a draft, when it is ready for review, then stakeholders can
    access it." — `test_submit_for_review_persists_draft_and_moves_to_in_review`
    (submits, then reads it back via the existing detail endpoint).
  - "Given a draft, when a stakeholder requests changes, then the system
    logs the request." — `test_review_request_changes_logs_the_feedback`
    plus the `request_changes` unit tests.
  - "Trust: Given a draft, when it is approved, then it is logged with the
    approver's ID and timestamp." — `test_review_approve_logs_approver_id_and_timestamp`
    plus the `approve` unit tests.
- Files touched: `src/lifecycle.py`, `src/request_intake.py`,
  `src/request_schema.py` (new), `src/stakeholder_review.py` (new),
  `src/stakeholder_review_routes.py` (new), `src/app.py`,
  `tests/test_request_schema.py` (new), `tests/test_stakeholder_review.py`
  (new), `tests/test_app.py`.
- Note on `.colaberry/progress.json`: this same commit marks all three
  STORY-008 criteria passed and the story verified, but leaves
  `commit_sha`/`commit_url`/`commit_at` `null` for the same reason as
  STORY-006 and STORY-007 — a commit cannot correctly record its own
  resulting hash inside itself. Those three fields are a small follow-up
  edit once this commit's real hash is known.

## 2026-09-05 — STORY-009: Data Validation and Finalization (REQ-014)
- Session: CC-20260905-n7wq
- Extended `src/lifecycle.py` with a `validated` status. `approved` gains
  two legal transitions: `validated` (data accuracy confirmed) or
  `changes_requested` (validation failure) — the failure path deliberately
  reuses STORY-008's existing correction loop (`changes_requested` →
  `in_review` → re-review → re-approve) rather than a parallel one, since
  "flagged for correction" is exactly what `changes_requested` already
  means. `validated` has no outgoing transition yet — publication
  (STORY-010) is out of scope here.
- Added `src/data_validation_rules.py`: `find_data_accuracy_violations()`
  defines "data accuracy confirmed" as a deterministic, testable condition
  — every `field_binding` referenced by an approved draft solution's
  visuals must trace back (case-insensitive substring match, either
  direction) to something actually stated in the request's own `analysis`
  (`business_objectives`, `scope`, `kpis`, `filters`, `calculations`,
  `visual_requirements`, `reporting_expectations`). No model call is
  needed or used — this is a pure function, kept separate from
  `src/data_validation.py` the same way `powerbi_solution_template.py` is
  split from `powerbi_solution.py`. A `field_binding` that doesn't trace
  back is either an upstream-fabricated field or a mismatch introduced
  along the pipeline; either way it can't be finalized without a human
  correcting it.
- Added `src/data_validation.py`: `DataValidation.validate()` fetches the
  request, raises `MissingValidationDataError` if `analysis` or
  `draft_solution` is absent, runs the accuracy check, then atomically
  updates status and writes exactly one audit entry
  (`data_validation_passed` or `data_validation_failed`, the latter
  storing the joined violation list in the audit entry's existing
  `error_category` slot) in a single transaction — same `_transition`
  shape as `StakeholderReview`, reusing `TRANSITIONS` for legality rather
  than hardcoding a status check, so calling `validate()` on a request
  that isn't `approved` raises `InvalidTransitionError` on its own.
- Wired into `POST /requests/<id>/validate`
  (`src/data_validation_routes.py`), registered from `src/app.py`
  alongside a new `DataValidation` instance in `app.config`. Unlike the
  AI-generation routes, there's no separate audit-write step to wrap —
  but this story's failure list explicitly names "audit trail logging
  fails" as a case to handle, so a `sqlite3.Error` raised inside that
  atomic transition/audit write (the whole transaction rolls back,
  leaving status unchanged) is caught here and returned as a controlled
  `500 audit_log_unavailable` instead of an unhandled exception.
- Verification: 209 automated tests passing (`pytest tests/`), up from
  190 — 5 new unit tests for the accuracy rule (match, mismatch,
  case-insensitivity, empty `field_bindings`, multiple violations across
  pages), 8 for `data_validation.py` (both outcomes' status transitions
  and audit content, unknown request, not-yet-approved rejection, and a
  direct-SQL-manipulation test for the missing-data guard), and 6 new
  route tests in `test_app.py` (both outcomes end-to-end through the real
  submit → analyze → submit-for-review → approve → validate flow, 404,
  400 missing `analyst_id`, 409 not-yet-approved, and the
  `audit_log_unavailable` control path, mirroring the same mock pattern
  used by the `dashboard-mockup`/`powerbi-solution` routes but targeting
  `DataValidation._audit.append` directly since this story's transition
  and audit write are atomic inside `DataValidation` itself). All
  existing 190 tests continue to pass unmodified. No external API calls
  in this story — the accuracy check is fully deterministic.
- Manual smoke test (scratch SQLite database, no test client fixtures):
  ran the real Flask app through `create_app()` for both outcomes —
  accurate data ends at `validated` with a `data_validation_passed` audit
  entry, inaccurate data ends at `changes_requested` with a
  `data_validation_failed` audit entry whose `error_category` names the
  unmatched `field_binding`. Both confirmed against the live audit log,
  not just test assertions. Scratch database discarded after the run.
- Acceptance criteria (exact portal wording, `.colaberry/progress.json`),
  all demonstrated by the tests and smoke test above:
  - "Given a draft solution, when validated, then data accuracy is
    confirmed." — `find_data_accuracy_violations()` unit tests plus the
    route's happy-path test and smoke test.
  - "Given a validation failure, when detected, then the system flags it
    for correction." — the `changes_requested` transition, unit-tested
    and smoke-tested.
  - "Trust: The system logs all validation actions in the audit trail." —
    audit-content assertions for both outcomes, unit and route level,
    plus the smoke test's live audit-log check.
- Files touched: `src/lifecycle.py`, `src/data_validation_rules.py`
  (new), `src/data_validation.py` (new), `src/data_validation_routes.py`
  (new), `src/app.py`, `tests/test_data_validation_rules.py` (new),
  `tests/test_data_validation.py` (new), `tests/test_app.py`.
- Note on `.colaberry/progress.json`: this same commit marks all three
  STORY-009 criteria passed and the story verified, but leaves
  `commit_sha`/`commit_url`/`commit_at` `null` for the same reason as
  STORY-006 through STORY-008 — a commit cannot correctly record its own
  resulting hash inside itself. Those three fields are a small follow-up
  edit once this commit's real hash is known.
