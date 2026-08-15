/* BLUEPRINT — single source of data for the whole knowledge base.
   Every page renders from this object. Nothing here is duplicated by hand
   elsewhere; if a number needs to change, it changes here once. */
const BLUEPRINT = {

  meta: {
    title: "AI-Powered Power BI Requirements System",
    tagline: "From a stakeholder's plain-language request to a clear, structured Power BI requirement.",
    generated: "2026-08-06"
  },

  idea: "Build an AI-powered Power BI requirement system for business stakeholders. Users submit their reporting requirements, the system analyzes and stores them, asks follow-up questions when information is missing, and recommends the appropriate data sources, KPIs, and report structure. On day one, it must turn a stakeholder's business request into clear, structured Power BI requirements.",

  dayOneSentence: "On day one, it must turn a stakeholder's business request into clear, structured Power BI requirements.",

  sections: [
    { id: "summary",      file: "01-summary.html",      title: "The Idea",                   short: "Idea",       nav: "Idea" },
    { id: "components",   file: "02-components.html",   title: "Components",                 short: "Components", nav: "Components" },
    { id: "architecture", file: "03-architecture.html", title: "How It Fits Together",        short: "Architecture", nav: "Architecture" },
    { id: "data-flow",    file: "04-data-flow.html",    title: "Data Flow",                  short: "Data Flow",  nav: "Data Flow" },
    { id: "build-order",  file: "05-build-order.html",  title: "Build Order",                short: "Build Order", nav: "Build Order" },
    { id: "coverage",     file: "06-coverage.html",     title: "Coverage",                   short: "Coverage",   nav: "Coverage" },
    { id: "assumptions",  file: "07-assumptions.html",  title: "Assumptions & Open Question", short: "Assumptions", nav: "Assumptions" },
    { id: "not-covered",  file: "08-not-covered.html",  title: "What This Design Does Not Cover", short: "Not Covered", nav: "Not Covered" }
  ],

  components: [
    {
      id: "intake-ui", name: "Stakeholder Intake UI", layer: "Interaction", shape: "stadium-rect",
      sentence: "Gives business stakeholders a plain-language place to submit a request and see or answer follow-up questions.",
      words: ["business stakeholders", "Users submit their reporting requirements"]
    },
    {
      id: "backend", name: "Backend API / Orchestrator", layer: "Orchestration", shape: "rect",
      sentence: "Routes each submission and answer between the UI, the AI engine, and storage, and keeps track of where a conversation is.",
      words: ["the system analyzes and stores them"]
    },
    {
      id: "engine", name: "AI Analysis and Recommendation Engine", layer: "Intelligence", shape: "rect",
      sentence: "Reads the request for meaning, decides what's missing, writes the next follow-up question, and drafts which KPIs, data sources, and report structure fit.",
      words: ["analyzes", "asks follow-up questions when information is missing", "recommends the appropriate data sources, KPIs, and report structure"]
    },
    {
      id: "claude", name: "Claude LLM API", layer: "Intelligence", shape: "hex", thirdParty: true,
      sentence: "Supplies the actual language understanding and generation the AI engine calls on — this system doesn't train its own model.",
      words: ["analyzes", "recommends"]
    },
    {
      id: "catalog", name: "KPI and Data Source Catalog", layer: "Data", shape: "cyl",
      sentence: "Holds the organization's real, known KPIs and data sources so a recommendation can be checked against what's actually \"appropriate\" instead of invented.",
      words: ["recommends the appropriate data sources, KPIs"]
    },
    {
      id: "reqdb", name: "Requirements Database", layer: "Data", shape: "cyl",
      sentence: "Keeps every submission, follow-up exchange, and finished requirement so the record outlives the browser session.",
      words: ["stores them"]
    },
    {
      id: "structure", name: "Requirement Structuring and Validation", layer: "Orchestration", shape: "rect", guarantee: true,
      sentence: "Forces the AI's draft into a fixed requirements schema and bounces it back for revision if it doesn't fit. This is the component that guarantees the day-one promise of a clear, structured result.",
      words: ["clear, structured Power BI requirements"]
    }
  ],

  layers: ["Interaction", "Orchestration", "Intelligence", "Data"],

  diagrams: {
    architecture: `flowchart TD
    Stakeholder(["Business Stakeholder"]) -->|"types a reporting request"| UI["Stakeholder Intake UI"]
    UI -->|"submits request or answer"| Backend["Backend API / Orchestrator"]
    Backend -->|"save submission"| ReqDB[("Requirements Database")]
    Backend -->|"request text and conversation history"| Engine["AI Analysis and Recommendation Engine"]
    Engine -->|"analysis prompt"| Claude{{"Claude LLM API"}}
    Claude -->|"analysis result"| Engine
    Engine -->|"lookup known KPIs and data sources"| Catalog[("KPI and Data Source Catalog")]
    Catalog -->|"catalog entries"| Engine
    Engine -->|"info missing: follow-up question"| Backend
    Backend -->|"show follow-up question"| UI
    UI -->|"stakeholder answers"| Backend
    Engine -->|"info complete: draft recommendation"| Structure["Requirement Structuring and Validation"]
    Structure -->|"schema check failed: revise"| Engine
    Structure -->|"schema valid: final requirement"| ReqDB
    Structure -->|"finished structured requirement"| Backend
    Backend -->|"display structured requirement"| UI
    UI -->|"delivers finished requirement"| Stakeholder`,

    dataFlow: `sequenceDiagram
    participant Stakeholder
    participant UI as Stakeholder Intake UI
    participant Backend as Backend API
    participant Engine as AI Analysis Engine
    participant Claude as Claude LLM API
    participant Catalog as KPI and Data Source Catalog
    participant Structure as Structuring and Validation
    participant ReqDB as Requirements Database

    Stakeholder->>UI: types business reporting request
    UI->>Backend: submit request text
    Backend->>ReqDB: save raw submission
    Backend->>Engine: request text and conversation history
    Engine->>Claude: analysis prompt
    Claude-->>Engine: analysis result
    Engine->>Catalog: lookup known KPIs and data sources
    Catalog-->>Engine: catalog entries
    alt information missing
        Engine->>Backend: follow-up question
        Backend->>UI: show follow-up question
        UI->>Backend: stakeholder answers
        Backend->>Engine: updated conversation history
    else information complete
        Engine->>Structure: draft KPIs, data sources, report structure
        alt schema invalid
            Structure->>Engine: revise draft
        else schema valid
            Structure->>ReqDB: save final structured requirement
            Structure->>Backend: finished structured requirement
            Backend->>UI: display structured requirement
            UI->>Stakeholder: finished requirement
        end
    end`,

    buildOrder: `gantt
    title Build Order - Day One Path
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d
    section Phases
    Capture and Persist        :p1, 2026-08-10, 5d
    Understand and Ask         :p2, after p1, 5d
    Ground the Recommendation  :p3, after p2, 5d
    Enforce Structure (gate)   :crit, p4, after p3, 5d`
  },

  flowSteps: [
    { n: 1,  actor: "Stakeholder", action: "Types a business reporting request into the Intake UI.", model: false, loop: false },
    { n: 2,  actor: "Intake UI",   action: "Submits the request text to the Backend API.", model: false, loop: false },
    { n: 3,  actor: "Backend API", action: "Saves the raw submission to the Requirements Database.", model: false, loop: false },
    { n: 4,  actor: "Backend API", action: "Forwards the request and conversation history to the AI Analysis Engine.", model: false, loop: false },
    { n: 5,  actor: "AI Engine",   action: "Sends an analysis prompt to the Claude LLM API.", model: true, loop: false },
    { n: 6,  actor: "AI Engine",   action: "Checks the response against the KPI and Data Source Catalog.", model: true, loop: false },
    { n: 7,  actor: "AI Engine",   action: "If information is missing: writes a follow-up question; stakeholder answers and flow returns to step 2.", model: true, loop: true },
    { n: 8,  actor: "AI Engine",   action: "If information is complete: drafts KPIs, data sources, and report structure.", model: true, loop: false },
    { n: 9,  actor: "Structuring & Validation", action: "Checks the draft against the fixed schema; an invalid draft goes back to the AI Engine.", model: false, loop: true },
    { n: 10, actor: "Structuring & Validation", action: "Saves the valid draft to the Requirements Database as the finished requirement.", model: false, loop: false },
    { n: 11, actor: "Backend API", action: "Returns the finished requirement to the Intake UI for the stakeholder to read.", model: false, loop: false }
  ],

  phases: [
    {
      n: 1, name: "Capture & Persist",
      adds: ["Stakeholder Intake UI", "Backend API / Orchestrator", "Requirements Database"],
      proves: "A stakeholder's raw request reliably gets in and stays saved.",
      critical: false, days: 5
    },
    {
      n: 2, name: "Understand & Ask",
      adds: ["AI Analysis and Recommendation Engine", "Claude LLM API"],
      proves: "The system can tell what's missing and hold a real back-and-forth, not just accept whatever's typed.",
      critical: false, days: 5
    },
    {
      n: 3, name: "Ground the Recommendation",
      adds: ["KPI and Data Source Catalog"],
      proves: "Recommendations name things that actually exist in the org, not plausible-sounding inventions.",
      critical: false, days: 5
    },
    {
      n: 4, name: "Enforce Structure",
      adds: ["Requirement Structuring and Validation"],
      proves: "The day-one promise itself: every finished output is a clear, structured requirement, every time.",
      critical: true, days: 5
    }
  ],

  assumptions: [
    {
      n: 1,
      text: "A Power BI requirement has one fixed target schema (Business Objective, Audience, KPI list, Data Sources, Report Structure/pages, Refresh cadence).",
      impact: "The Structuring and Validation schema needs redesign — a real data-model change, not a quick fix."
    },
    {
      n: 2,
      text: "The KPI and Data Source Catalog already exists somewhere in the org (a data dictionary or BI semantic model) and this system only reads it.",
      impact: "If no such catalog exists yet, Phase 3 needs an entire catalog-curation workflow added first — a materially bigger project."
    },
    {
      n: 3,
      text: "The AI Analysis Engine calls a hosted LLM (Claude) rather than a custom-trained model.",
      impact: "A compliance requirement for a private/local model would add hosting and latency components not in this design."
    },
    {
      n: 4,
      text: "Conversations are single-session and synchronous — the stakeholder waits for and answers follow-up questions in one sitting.",
      impact: "Async, multi-day conversations would need session resumption and a notification component this design doesn't have."
    },
    {
      n: 5,
      text: "No authentication or access control is required on day one.",
      impact: "If recommendations must be scoped to a stakeholder's department, an Auth and Identity component has to be added before real data sources are exposed."
    }
  ],

  openQuestion: {
    question: "Does the KPI and Data Source Catalog already exist somewhere in the org, or does this system need to build and maintain it itself?",
    branches: [
      {
        label: "Catalog already exists",
        detail: "Phase 3 is just an integration: point the AI Engine at the existing data dictionary or semantic model. Build order stays as planned."
      },
      {
        label: "Catalog does not exist yet",
        detail: "A catalog-curation subsystem (someone has to define and maintain KPI and data-source entries) becomes a prerequisite project before Phase 3 can start."
      }
    ]
  },

  coverage: [
    { phrase: "business stakeholders", coveredBy: ["Stakeholder Intake UI"], status: "covered" },
    { phrase: "Users submit their reporting requirements", coveredBy: ["Stakeholder Intake UI", "Backend API / Orchestrator"], status: "covered" },
    { phrase: "the system analyzes", coveredBy: ["AI Analysis and Recommendation Engine", "Claude LLM API"], status: "covered" },
    { phrase: "and stores them", coveredBy: ["Requirements Database"], status: "covered" },
    { phrase: "asks follow-up questions when information is missing", coveredBy: ["AI Analysis and Recommendation Engine", "Backend API / Orchestrator"], status: "covered" },
    { phrase: "recommends the appropriate data sources, KPIs, and report structure", coveredBy: ["AI Analysis and Recommendation Engine", "KPI and Data Source Catalog"], status: "covered" },
    { phrase: "clear, structured Power BI requirements (day one)", coveredBy: ["Requirement Structuring and Validation"], status: "covered" },
    { phrase: "user accounts / login", coveredBy: [], status: "not-covered" },
    { phrase: "notifications / email delivery", coveredBy: [], status: "not-covered" },
    { phrase: "publishing into an actual Power BI workspace", coveredBy: [], status: "not-covered" }
  ],

  notCovered: [
    "No authentication, user accounts, or role-based access control — every stakeholder request is treated the same regardless of department or data-access rights.",
    "No notification or email delivery when a requirement is finished — the stakeholder has to return to the same UI to see it.",
    "No hand-off automation into an actual Power BI workspace — the output is a structured requirements document, not a generated .pbix file or a published report.",
    "No versioning or edit history if a stakeholder wants to revise a requirement after it's finalized.",
    "No multi-stakeholder collaboration on a single requirement.",
    "No handling of conflicting or duplicate requirements submitted by different stakeholders."
  ],

  interpretations: {
    architecture: "The AI Engine sits between two loops: a conversation loop back to the stakeholder when information is missing, and a validation loop back from Structuring when the draft doesn't fit the schema — nothing reaches the stakeholder as \"finished\" until both loops close.",
    dataFlow: "Every request passes through the model twice — once to analyze/ask, once to draft a recommendation — but never reaches the stakeholder as done without first clearing the non-AI validation gate.",
    buildOrder: "The first three phases can each look like a working demo on their own; only Phase 4 is what actually keeps the day-one promise, which is why it's marked critical.",
    coverage: "Every clause in the idea paragraph maps to at least one component — there are no unimplemented phrases. The not-covered rows are things a reader might assume are included that the paragraph never actually asked for.",
    componentsLayers: "Two layers do the orchestration work (Orchestration appears twice: routing and validating) while Data and Intelligence each hold exactly the pieces the paragraph's verbs required — nothing extra."
  }
};
