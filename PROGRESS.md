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
