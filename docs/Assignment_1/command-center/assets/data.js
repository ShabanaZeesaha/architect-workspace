/* ==========================================================================
   PowerBI Blueprint — Command Center data module
   This is the ONE place project data lives. Every tab reads from here.
   REAL_DATA = what the project has actually produced.
   SAMPLE_DATA = believable made-up values, only for fields REAL_DATA leaves
   empty because nothing has been produced for them yet (system connections,
   story progress, etc). Requirements, releases, stories and roles are real —
   they come straight from the plan, not from sample data.
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
  const STORIES = [
    { id: "STORY-001", title: "Request Intake and Initial Analysis", release: "r0", due: "2026-08-13", owner: "Business Analyst" },
    { id: "STORY-002", title: "Lifecycle Tracking Setup", release: "r0", due: "2026-08-23", owner: "Project Manager" },
    { id: "STORY-003", title: "Requirement Clarification", release: "r1", due: "2026-08-23", owner: "Business Analyst" },
    { id: "STORY-004", title: "Field Mapping from Excel", release: "r1", due: "2026-09-02", owner: "Data Specialist" },
    { id: "STORY-005", title: "Design Recommendation Generation", release: "r2", due: "2026-09-02", owner: "Business Analyst" },
    { id: "STORY-006", title: "Dashboard Mockup Generation", release: "r2", due: "2026-09-11", owner: "Report Designer" },
    { id: "STORY-007", title: "Draft Power BI Solution Generation", release: "r3", due: "2026-09-11", owner: "Report Designer" },
    { id: "STORY-008", title: "Stakeholder Review Interface", release: "r3", due: "2026-09-21", owner: "Stakeholder" },
    { id: "STORY-009", title: "Data Validation and Finalization", release: "r4", due: "2026-09-21", owner: "Data Specialist" },
    { id: "STORY-010", title: "Dashboard Publication", release: "r4", due: "2026-10-01", owner: "Report Designer" }
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

  // ---- REAL: nothing has been produced yet on day one ----
  const REAL_DATA = {
    project: PROJECT,
    releases: RELEASES,
    stories: STORIES.map(s => ({ ...s, status: "not_started" })),
    requirements: REQUIREMENTS,
    guardrailIds: GUARDRAIL_IDS,
    roles: ROLES,
    systems: SYSTEMS.map(name => ({ name, status: "unknown", lastChecked: null })),
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
    generatedAt: "2026-08-17T13:42:00Z"
  };

  function getData(mode) {
    return mode === "sample" ? SAMPLE_DATA : REAL_DATA;
  }

  global.CommandCenterData = { getData, REAL_DATA, SAMPLE_DATA };

})(window);
