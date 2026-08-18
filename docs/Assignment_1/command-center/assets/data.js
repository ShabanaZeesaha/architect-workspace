/* ==========================================================================
   PowerBI Blueprint — Command Center data module
   This is the ONE place project data lives. Every tab reads from here.
   REAL_DATA = what the project has actually produced.
   SAMPLE_DATA = believable made-up values, only for fields REAL_DATA leaves
   empty because nothing has been produced for them yet (system connections,
   story progress, agent skills). Requirements, releases, stories, roles and
   the data model are real — they come straight from the plan, not sample data.
   ========================================================================== */
(function (global) {

  const PROJECT = {
    name: "PowerBI Blueprint",
    pitch: "An AI-powered system for automating the conversion of email-based requests and Excel reports into structured Power BI solutions.",
    demoDate: "2026-10-08",
    buildEndDate: "2026-10-01"
  };

  const RELEASES = [
    { id: "r0", name: "Initial Setup and Trust Spine", stories: 2, start: "2026-08-13", end: "2026-08-23" },
    { id: "r1", name: "Requirement Clarification and Field Mapping", stories: 2, start: "2026-08-23", end: "2026-09-02" },
    { id: "r2", name: "Design Recommendation and Mockup Generation", stories: 2, start: "2026-09-02", end: "2026-09-11" },
    { id: "r3", name: "Draft Generation and Stakeholder Review", stories: 2, start: "2026-09-11", end: "2026-09-21" },
    { id: "r4", name: "Finalization and Publication", stories: 2, start: "2026-09-21", end: "2026-10-01" }
  ];

  // Owners are roles from the user stories ("As a <role>, I want ..."), not scoped AI agents.
  // reqRefs are a best-effort match between each story's title and the requirement text it
  // most directly serves — inferred, not stated verbatim in the plan.
  const STORIES = [
    { id: "STORY-001", title: "Request Intake and Initial Analysis", release: "r0", due: "2026-08-13", owner: "Business Analyst", reqRefs: ["REQ-001", "REQ-002", "REQ-009"] },
    { id: "STORY-002", title: "Lifecycle Tracking Setup", release: "r0", due: "2026-08-23", owner: "Project Manager", reqRefs: ["REQ-008", "REQ-010", "REQ-012"] },
    { id: "STORY-003", title: "Requirement Clarification", release: "r1", due: "2026-08-23", owner: "Business Analyst", reqRefs: ["REQ-004"] },
    { id: "STORY-004", title: "Field Mapping from Excel", release: "r1", due: "2026-09-02", owner: "Data Specialist", reqRefs: ["REQ-003"] },
    { id: "STORY-005", title: "Design Recommendation Generation", release: "r2", due: "2026-09-02", owner: "Business Analyst", reqRefs: ["REQ-005"] },
    { id: "STORY-006", title: "Dashboard Mockup Generation", release: "r2", due: "2026-09-11", owner: "Report Designer", reqRefs: ["REQ-006", "REQ-018"] },
    { id: "STORY-007", title: "Draft Power BI Solution Generation", release: "r3", due: "2026-09-11", owner: "Report Designer", reqRefs: ["REQ-007"] },
    { id: "STORY-008", title: "Stakeholder Review Interface", release: "r3", due: "2026-09-21", owner: "Stakeholder", reqRefs: ["REQ-013", "REQ-017"] },
    { id: "STORY-009", title: "Data Validation and Finalization", release: "r4", due: "2026-09-21", owner: "Data Specialist", reqRefs: ["REQ-014"] },
    { id: "STORY-010", title: "Dashboard Publication", release: "r4", due: "2026-10-01", owner: "Report Designer", reqRefs: ["REQ-015", "REQ-016"] }
  ];

  const REQUIREMENTS = [
    { id: "REQ-001", type: "FUNC", priority: "must", text: "The system must analyze email-based requests to identify business objectives, scope, KPIs, filters, calculations, visual requirements, and reporting expectations." },
    { id: "REQ-002", type: "FUNC", priority: "must", text: "The system must analyze existing Excel reports to identify business objectives, scope, KPIs, filters, calculations, visual requirements, and reporting expectations." },
    { id: "REQ-003", type: "FUNC", priority: "must", text: "The system must map existing Excel fields to approved current tables and columns." },
    { id: "REQ-004", type: "FUNC", priority: "must", text: "The system must detect missing, unclear, or conflicting requirements and generate follow-up questions." },
    { id: "REQ-005", type: "FUNC", priority: "must", text: "The system must recommend data models, relationships, transformations, validation checks, KPI definitions, DAX measures, report pages, slicers, and visual design based on approved requirements and field mappings." },
    { id: "REQ-006", type: "FUNC", priority: "must", text: "The system must generate a dashboard mockup based on an approved organizational report template." },
    { id: "REQ-007", type: "FUNC", priority: "must", text: "The system must generate a draft Power BI solution based on an approved organizational report template." },
    { id: "REQ-008", type: "FUNC", priority: "must", text: "Users must be able to track the complete lifecycle of each request from intake to completion." },
    { id: "REQ-009", type: "CONSTRAINT", priority: "must", text: "The system must use Outlook, Power Automate, SharePoint, AI services, and Power BI to orchestrate the workflow and store inputs and outputs." },
    { id: "REQ-010", type: "SAFE", priority: "must", text: "The system must maintain a traceable status and approval history for each request." },
    { id: "REQ-011", type: "FUNC", priority: "must", text: "AI must assist with analysis, recommendations, mapping, documentation, mockups, and draft generation." },
    { id: "REQ-012", type: "SAFE", priority: "must", text: "AI must not finalize business requirements, approve calculations, or publish a production dashboard without authorized human review and approval." },
    { id: "REQ-013", type: "FUNC", priority: "must", text: "The system must provide a user interface for stakeholders to review and approve draft Power BI solutions." },
    { id: "REQ-014", type: "FUNC", priority: "must", text: "The system must validate data before generating the draft Power BI solution." },
    { id: "REQ-015", type: "FUNC", priority: "must", text: "The system must support the publication of approved Power BI dashboards." },
    { id: "REQ-016", type: "FUNC", priority: "should", text: "The system must provide notifications to users at key stages of the request lifecycle." },
    { id: "REQ-017", type: "FUNC", priority: "should", text: "The system must allow users to manually adjust AI-generated recommendations before approval." },
    { id: "REQ-018", type: "FUNC", priority: "should", text: "The system must support multiple report templates for different organizational needs." }
  ];

  const GUARDRAIL_IDS = ["REQ-010", "REQ-012"];

  const ROLES = ["Business Analyst", "Project Manager", "Data Specialist", "Report Designer", "Stakeholder"];

  const SYSTEMS = ["Outlook", "Power Automate", "SharePoint", "Power BI"];

  // Outcomes: the plan carries no numeric target yet. Left empty on purpose.
  const OUTCOMES = [];

  // Data model: a starting point derived from the requirements above, one entity per
  // thing the system has to store. Not yet created as real tables — for review first.
  const DATA_MODEL = [
    { id: "request", name: "Request", purpose: "The intake unit: one email-based ask or one Excel report submitted for conversion.",
      fields: ["id", "source_type (email | excel)", "received_at", "submitted_by", "subject_or_filename", "current_stage"],
      relates: [{ to: "requirement_draft", phrase: "has one" }, { to: "status_event", phrase: "has many" }, { to: "clarification_question", phrase: "has many" }],
      reqRefs: ["REQ-001", "REQ-002", "REQ-008", "REQ-009"] },
    { id: "requirement_draft", name: "Requirement Draft", purpose: "The structured requirement extracted from a request: objectives, scope, KPIs, filters, calculations, visuals, reporting expectations.",
      fields: ["id", "request_id", "business_objective", "scope", "kpi_list", "filters", "calculations", "visual_requirements", "reporting_expectations", "version", "approved_at"],
      relates: [{ to: "request", phrase: "belongs to" }, { to: "design_recommendation", phrase: "informs" }],
      reqRefs: ["REQ-001", "REQ-002", "REQ-011"] },
    { id: "clarification_question", name: "Clarification Question", purpose: "A follow-up question raised when a request is missing, unclear, or conflicting.",
      fields: ["id", "request_id", "question_text", "raised_at", "answered_at", "answer_text", "status"],
      relates: [{ to: "request", phrase: "belongs to" }],
      reqRefs: ["REQ-004"] },
    { id: "field_mapping", name: "Field Mapping", purpose: "One Excel column mapped to an approved table/column in the current schema.",
      fields: ["id", "request_id", "source_field_name", "source_sheet", "mapped_table", "mapped_column", "confidence", "approved"],
      relates: [{ to: "request", phrase: "belongs to" }, { to: "approved_schema_column", phrase: "references" }],
      reqRefs: ["REQ-003"] },
    { id: "approved_schema_column", name: "Approved Schema Column", purpose: "The org's existing, approved tables and columns — read from, not owned by this system.",
      fields: ["table_name", "column_name", "data_type", "description"],
      relates: [{ to: "field_mapping", phrase: "referenced by" }],
      reqRefs: ["REQ-003"] },
    { id: "design_recommendation", name: "Design Recommendation", purpose: "The AI-drafted data model, relationships, transformations, validation checks, KPI definitions, DAX measures, report pages, slicers, and visual design for one request.",
      fields: ["id", "request_id", "data_model_summary", "relationships", "transformations", "validation_checks", "kpi_definitions", "dax_measures", "report_pages", "slicers", "visual_design_notes", "status"],
      relates: [{ to: "request", phrase: "belongs to" }, { to: "requirement_draft", phrase: "built from" }, { to: "field_mapping", phrase: "built from" }, { to: "mockup", phrase: "informs" }, { to: "draft_solution", phrase: "informs" }],
      reqRefs: ["REQ-005", "REQ-017"] },
    { id: "report_template", name: "Report Template", purpose: "An organizational report template that mockups and drafts are generated against.",
      fields: ["id", "name", "description", "org_unit", "is_default"],
      relates: [{ to: "mockup", phrase: "used by" }, { to: "draft_solution", phrase: "used by" }],
      reqRefs: ["REQ-006", "REQ-007", "REQ-018"] },
    { id: "mockup", name: "Mockup", purpose: "A generated dashboard mockup for stakeholder sign-off before a real draft is built.",
      fields: ["id", "request_id", "template_id", "layout_ref", "generated_at", "approved_by", "approved_at"],
      relates: [{ to: "request", phrase: "belongs to" }, { to: "report_template", phrase: "uses" }],
      reqRefs: ["REQ-006"] },
    { id: "draft_solution", name: "Draft Solution", purpose: "The generated draft Power BI solution, not yet validated or published.",
      fields: ["id", "request_id", "template_id", "design_recommendation_id", "solution_ref", "generated_at", "validation_status"],
      relates: [{ to: "request", phrase: "belongs to" }, { to: "report_template", phrase: "uses" }, { to: "design_recommendation", phrase: "built from" }, { to: "review_decision", phrase: "has many" }],
      reqRefs: ["REQ-007", "REQ-014"] },
    { id: "review_decision", name: "Review Decision", purpose: "A stakeholder's approve / reject / request-changes decision on a draft solution — the human checkpoint the AI cannot skip.",
      fields: ["id", "draft_solution_id", "reviewer", "decision", "comments", "decided_at"],
      relates: [{ to: "draft_solution", phrase: "belongs to" }],
      reqRefs: ["REQ-013", "REQ-012"] },
    { id: "status_event", name: "Status Event", purpose: "One entry in a request's traceable status and approval history — the audit trail behind REQ-010 and REQ-012.",
      fields: ["id", "request_id", "stage", "actor (human | ai)", "action", "note", "occurred_at"],
      relates: [{ to: "request", phrase: "belongs to" }],
      reqRefs: ["REQ-010", "REQ-012"] },
    { id: "published_dashboard", name: "Published Dashboard", purpose: "The finalized, published Power BI dashboard for a request.",
      fields: ["id", "request_id", "draft_solution_id", "published_by", "published_at", "workspace_ref"],
      relates: [{ to: "request", phrase: "belongs to" }, { to: "draft_solution", phrase: "published from" }],
      reqRefs: ["REQ-015"] },
    { id: "notification", name: "Notification", purpose: "A message sent to a user at a key stage of a request's lifecycle.",
      fields: ["id", "request_id", "recipient_role", "stage", "sent_at", "channel"],
      relates: [{ to: "request", phrase: "belongs to" }],
      reqRefs: ["REQ-016"] }
  ];
  const DATA_MODEL_NOTE = "REQ-009 (orchestration across Outlook/Power Automate/SharePoint/Power BI) and REQ-011 (AI assists throughout) are cross-cutting — they shape how these tables get written, not a table of their own.";

  // ---- REAL: nothing has been produced yet on day one ----
  const REAL_DATA = {
    project: PROJECT,
    releases: RELEASES,
    stories: STORIES.map(s => ({ ...s, status: "not_started" })),
    requirements: REQUIREMENTS,
    guardrailIds: GUARDRAIL_IDS,
    roles: ROLES,
    systems: SYSTEMS.map(name => ({ name, status: "unknown", lastChecked: null })),
    outcomes: OUTCOMES,
    dataModel: DATA_MODEL,
    dataModelNote: DATA_MODEL_NOTE,
    agentSkills: Object.fromEntries(ROLES.map(r => [r, []])),
    generatedAt: null
  };

  // ---- SAMPLE: believable made-up shape, clearly labelled wherever it's shown ----
  const SAMPLE_STATUS_BY_RELEASE = {
    r0: "done", r1: "in_progress", r2: "not_started", r3: "not_started", r4: "not_started"
  };
  const SAMPLE_DATA = {
    project: PROJECT,
    releases: RELEASES,
    stories: STORIES.map((s, i) => ({
      ...s,
      status: SAMPLE_STATUS_BY_RELEASE[s.release] === "in_progress"
        ? (i % 2 === 0 ? "in_progress" : "not_started")
        : SAMPLE_STATUS_BY_RELEASE[s.release]
    })),
    requirements: REQUIREMENTS,
    guardrailIds: GUARDRAIL_IDS,
    roles: ROLES,
    systems: [
      { name: "Outlook", status: "connected", lastChecked: "2026-08-17T13:42:00Z" },
      { name: "Power Automate", status: "connected", lastChecked: "2026-08-17T13:41:00Z" },
      { name: "SharePoint", status: "error", lastChecked: "2026-08-17T09:15:00Z" },
      { name: "Power BI", status: "not_connected", lastChecked: "2026-08-16T18:02:00Z" }
    ],
    outcomes: OUTCOMES,
    dataModel: DATA_MODEL,
    dataModelNote: DATA_MODEL_NOTE,
    agentSkills: {
      "Business Analyst": ["Stakeholder interviewing", "Requirement analysis"],
      "Project Manager": ["Lifecycle tracking", "Release planning"],
      "Data Specialist": ["Field mapping", "Data validation"],
      "Report Designer": ["Mockup generation", "DAX authoring"],
      "Stakeholder": ["Review & approval"]
    },
    generatedAt: "2026-08-17T13:42:00Z"
  };

  function getData(mode) {
    return mode === "sample" ? SAMPLE_DATA : REAL_DATA;
  }

  global.CommandCenterData = { getData, REAL_DATA, SAMPLE_DATA };

})(window);
