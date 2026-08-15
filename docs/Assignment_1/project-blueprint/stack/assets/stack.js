/* STACK — single source of data for the tech-stack knowledge base.
   Every page renders from this object. Nothing here is duplicated by hand
   elsewhere; if a rating or a prompt needs to change, it changes here once. */
const STACK = {

  meta: {
    title: "Tech Stack — AI-Powered Power BI Requirements System",
    tagline: "One real technology per component, rated against this project's actual day-one scale — not against what's popular.",
    generated: "2026-08-06"
  },

  idea: "Build an AI-powered Power BI requirement system for business stakeholders. Users submit their reporting requirements, the system analyzes and stores them, asks follow-up questions when information is missing, and recommends the appropriate data sources, KPIs, and report structure. On day one, it must turn a stakeholder's business request into clear, structured Power BI requirements.",

  scaleAssumption: "Day-one / early-stage build — one small team, four build phases over roughly 20 days (see architecture.md) — not an enterprise-scale rebuild. A technology can be excellent in general and still rated 🔴 here if it's more machinery than this specific system needs on day one.",

  headline: "This stack is most likely to break in one place: the KPI and Data Source Catalog. Every other row here is an ordinary early-stage web stack — React, Express, Postgres, a managed host — but the catalog recommendation only works if an org data dictionary or BI semantic model already exists to read from. If it doesn't, Phase 3 of the build order stops being an integration and becomes its own catalog-curation project, and no technology choice below fixes that — only an answer to the open question in architecture.md does.",

  fitKey: [
    { fit: "green", icon: "🟢", label: "great fit", meaning: "Matches this project's size and needs — pick it, move on." },
    { fit: "amber", icon: "🟡", label: "good fit", meaning: "Works, but there's a real caveat worth reading first." },
    { fit: "red", icon: "🔴", label: "consider carefully", meaning: "Where this plan is most likely to hurt — a genuine risk, not a nitpick." }
  ],

  sections: [
    { id: "summary",         file: "01-summary.html",         title: "Summary",                 nav: "Summary" },
    { id: "recommendations", file: "02-recommendations.html", title: "Recommendations",         nav: "Stack" },
    { id: "ratings",         file: "03-ratings.html",         title: "Fit Ratings Explained",    nav: "Ratings" },
    { id: "learning-path",   file: "04-learning-path.html",   title: "What to Learn First",      nav: "Learn" },
    { id: "alternatives",    file: "05-alternatives.html",    title: "Alternatives Considered",  nav: "Alternatives" },
    { id: "lock-in",         file: "06-lock-in.html",         title: "How Hard to Undo",         nav: "Lock-In" },
    { id: "topology",        file: "07-topology.html",        title: "What Runs Where",          nav: "Topology" },
    { id: "appendix",        file: "08-appendix.html",        title: "Appendix",                 nav: "Appendix" }
  ],

  groups: [
    { id: "touch",  label: "Things a person touches" },
    { id: "write",  label: "Things you write" },
    { id: "store",  label: "Things you store" },
    { id: "depend", label: "Things you depend on" },
    { id: "flow",   label: "Things the data flow needs" }
  ],

  recommendations: [
    {
      id: "intake-ui", component: "Stakeholder Intake UI", group: "touch", fromComponentList: true,
      tech: "React 18 + Vite (TypeScript)", fit: "green",
      why: "A friendly form-and-chat screen for typing a request and answering follow-up questions — React is the most common toolkit for screens like this, and Vite starts it up in seconds with no setup.",
      caveat: "",
      prompt: "Explain React and Vite to me like I'm new to frontend frameworks, using my AI-Powered Power BI Requirements System's Stakeholder Intake UI as the example. What would the follow-up question screen actually look like in code?"
    },
    {
      id: "backend", component: "Backend API / Orchestrator", group: "write", fromComponentList: true,
      tech: "Node.js + Express (TypeScript)", fit: "green",
      why: "The traffic cop between the UI, the AI, and the database — Express is a small, well-understood way to write API routes without dragging in a bigger framework than a handful of endpoints needs.",
      caveat: "",
      prompt: "Explain Node.js and Express to me like I'm new to backend frameworks, using my Power BI Requirements System's Backend API / Orchestrator as the example. How would it route a submission to the AI Engine and back?"
    },
    {
      id: "engine", component: "AI Analysis and Recommendation Engine", group: "write", fromComponentList: true,
      tech: "Anthropic TypeScript SDK (@anthropic-ai/sdk, Messages API)", fit: "amber",
      why: "The code that actually talks to Claude and decides what to do with the answer — the plain SDK is a thin, well-documented wrapper, not a bigger \"agent framework.\"",
      caveat: "It gives you no built-in retry loop or structured-output enforcement, so you write that glue yourself (Zod, below, covers the output side).",
      prompt: "Explain the Anthropic TypeScript SDK to me like I'm new to calling LLM APIs, using my AI Analysis and Recommendation Engine as the example. What would the analysis prompt and response handling look like?"
    },
    {
      id: "claude", component: "Claude LLM API", group: "depend", fromComponentList: true,
      tech: "Claude Sonnet 5 (Anthropic API)", fit: "green",
      why: "The language model that reads the request, asks good follow-up questions, and drafts the recommendation — Sonnet 5 balances quality and cost well for structured back-and-forth text tasks like this one, without paying for reasoning power this task doesn't need day one.",
      caveat: "",
      prompt: "Explain Claude Sonnet 5 to me like I'm new to choosing LLM models, using my Power BI Requirements System as the example. Why is it a good fit for analyzing stakeholder requests instead of a smaller or bigger model?"
    },
    {
      id: "catalog", component: "KPI and Data Source Catalog", group: "store", fromComponentList: true,
      tech: "PostgreSQL (read-only schema, same instance)", fit: "red",
      why: "The org's existing list of real KPIs and data sources, queried but not owned by this system.",
      caveat: "This rating only holds if that list already exists somewhere in the org — if it doesn't, this row understates a materially bigger project (see the headline above).",
      prompt: "Explain how to connect to an existing PostgreSQL-based data catalog to me like I'm new to databases, using my KPI and Data Source Catalog component as the example. What would a read-only query look like?"
    },
    {
      id: "reqdb", component: "Requirements Database", group: "store", fromComponentList: true,
      tech: "PostgreSQL 16", fit: "green",
      why: "A single reliable place to keep every submission, follow-up answer, and finished requirement — Postgres handles this project's structured, fixed-schema data comfortably with room to grow.",
      caveat: "",
      prompt: "Explain PostgreSQL to me like I'm new to databases, using my Requirements Database as the example. What tables would I actually have?"
    },
    {
      id: "structure", component: "Requirement Structuring and Validation", group: "write", fromComponentList: true,
      tech: "Zod", fit: "green",
      why: "A schema — think of it as a strict form template — that Zod checks the AI's draft against before anything counts as \"finished.\" This is the actual code-level mechanism behind the day-one promise.",
      caveat: "",
      prompt: "Explain Zod to me like I'm new to schema validation, using my Requirement Structuring and Validation component as the example. What would the fixed requirements schema look like in code?"
    },
    {
      id: "hosting", component: "Hosting & Deployment", group: "flow", fromComponentList: false,
      tech: "Render (managed PaaS)", fit: "amber",
      why: "Where the frontend, backend, and database actually run once someone besides you can reach them — the component list never names this, but the data flow can't work without it.",
      caveat: "Render needs almost no setup for a day-one system, but you trade away fine-grained infrastructure control, and costs can climb awkwardly if usage grows a lot.",
      prompt: "Explain Render (or a similar managed PaaS) to me like I'm new to deployment, using my Power BI Requirements System as the example. What would go live on day one?"
    }
  ],

  leastConfident: [
    { recId: "catalog", note: "The rating itself is confident — the risk is real — but the right technology depends entirely on an answer this document doesn't have: does the catalog already exist, and if so, in what system? \"A read-only Postgres schema\" is a placeholder for \"whatever the org's real data dictionary turns out to be.\"" },
    { recId: "hosting", note: "Render is the safe day-one default, but this is the row most likely to change once real traffic or compliance requirements show up." }
  ],

  learningOrder: [
    { n: 1, recId: "reqdb", why: "Everything else stores into or reads from it; understanding tables first makes every other piece make sense." },
    { n: 2, recId: "backend", why: "The shape every other piece connects through — UI in, AI engine out, database underneath." },
    { n: 3, recId: "structure", why: "Small, fast payoff, and it's the direct code behind the day-one promise." },
    { n: 4, recId: "engine", why: "The \"AI\" part, but it only makes sense once you know what shape of data it has to produce (Zod, learned first)." },
    { n: 5, recId: "intake-ui", why: "The UI can be stubbed with plain HTML while the backend loop gets proven; learn it once there's something real to display." },
    { n: 6, recId: "hosting", why: "Last, once there's something worth deploying." }
  ],

  alternatives: [
    { recId: "intake-ui", alt: "Next.js", whyNot: "Its server-rendering and file-based routing solve problems (SEO, multi-page navigation) this single intake-and-follow-up flow doesn't have yet." },
    { recId: "backend", alt: "Python + FastAPI", whyNot: "A fine choice on its own, but it splits the stack across two languages (TypeScript frontend, Python backend) for no requirement-driven reason. Express keeps one language end-to-end." },
    { recId: "engine", alt: "Full Claude Agent SDK / LangChain", whyNot: "Built for autonomous, multi-tool agent loops. This engine's actual job — analyze, ask-or-draft, wait for validation — doesn't need that orchestration machinery; it's unused weight on day one." },
    { recId: "claude", alt: "Claude Opus 5", whyNot: "Stronger reasoning than a structured extraction-and-drafting task needs, at meaningfully higher cost and latency per stakeholder submission." },
    { recId: "catalog", alt: "A dedicated catalog microservice, built in-house", whyNot: "Premature — architecture.md assumes the catalog already exists elsewhere. Building one is a different, larger project that should only start once that assumption is confirmed false." },
    { recId: "reqdb", alt: "MongoDB", whyNot: "The requirement schema is fixed and relational (Assumption 1 in architecture.md). A document store adds flexibility this project doesn't need and gives up the cross-record consistency a relational store provides for free." },
    { recId: "structure", alt: "Hand-written if/else checks", whyNot: "Works today, breaks silently the first time the schema grows a field. Zod keeps the check declarative, in one place, and impossible to accidentally skip." },
    { recId: "hosting", alt: "Self-managed VPS + Docker + Nginx", whyNot: "More control, but real ongoing ops burden (patching, TLS, uptime) for a team that, per architecture.md, is trying to prove a day-one promise — not run infrastructure." }
  ],

  lockIn: [
    { recId: "intake-ui", difficulty: "easy", why: "The UI is the most replaceable layer — it talks to the backend over a normal HTTP API, so swapping frameworks doesn't touch anything else." },
    { recId: "backend", difficulty: "medium", why: "The frontend depends on its route shapes, but Express itself is a thin layer over plain HTTP — a rewrite is real work, not a rearchitecture." },
    { recId: "engine", difficulty: "medium", why: "Swapping model providers means rewriting prompts and re-tuning behavior, not just plumbing — the SDK call itself is easy to change, the prompt engineering behind it isn't." },
    { recId: "claude", difficulty: "medium", why: "Usually a config change plus prompt re-tuning to move to a different Claude model; moving to a different vendor entirely is closer to the AI Engine's \"medium\" above." },
    { recId: "catalog", difficulty: "easy", why: "It's read-only queries against someone else's data — pointing them at a different source doesn't touch anything this system owns." },
    { recId: "reqdb", difficulty: "hard", why: "All persisted data has to migrate, and the fixed schema (Assumption 1) is load-bearing for the rest of the system — this is the hardest row to walk back." },
    { recId: "structure", difficulty: "easy", why: "Validation logic is isolated in one schema file — swapping the library doesn't touch the data it validates." },
    { recId: "hosting", difficulty: "medium", why: "Moving off a managed PaaS means learning infrastructure you didn't need before, but it's an ops migration, not a code rewrite." }
  ],

  topology: {
    yourCode: ["intake-ui", "backend", "engine", "structure"],
    someoneElses: ["reqdb", "catalog", "claude", "hosting"],
    note: "Your code (UI, backend, AI orchestration, validation) all runs from one repo. What it depends on — the database, the catalog it reads, Claude itself, and the host machine — all run on infrastructure you don't own or maintain day to day."
  },

  notTold: [
    "Exact Postgres table and column names — that's a data-model design task, not a tech-stack pick.",
    "Prompt wording for the Claude calls — the analysis and drafting prompts still have to be written and iterated on; \"use Claude Sonnet 5\" says nothing about what you ask it.",
    "Whether the KPI catalog actually exists in your org — the single open question that changes the whole KPI/Catalog row and, per architecture.md, the whole Phase 3 scope.",
    "Cost estimates — both Anthropic API usage and Render's pricing tier depend on real traffic this document doesn't know yet.",
    "Authentication — architecture.md explicitly has none on day one, so no row here addresses it; adding auth later touches the Backend, the UI, and possibly the Catalog's access rules."
  ],

  interpretations: {
    summary: "Five green, two amber, one red — and the one red row is earned, not decorative: it's the same open question architecture.md itself flags as the thing most likely to change this whole design.",
    recommendations: "Reading top to bottom by group: one thing stakeholders touch, three things this team writes, two things it stores, one thing it depends on, and one thing the data flow needed that the component list never named.",
    ratings: "A rating describes fit for THIS project's day-one scale, not a verdict on the technology in general — Claude Opus 5 or a self-managed VPS would both be excellent choices for a different, later-stage version of this system.",
    learningPath: "The order runs bottom-up through the architecture: learn what stores the data first, then what routes it, then what checks its shape, then what generates it — the UI and hosting come last because both can be stubbed out the longest.",
    alternatives: "Every alternative considered here was rejected for the same reason in spirit: it solves a problem this day-one system doesn't have yet, not because it's a worse technology.",
    lockIn: "The database is the one truly hard-to-undo choice — everything else can be swapped with real but bounded effort. That's why Requirements Database got the most scrutiny on the fit table, not the least.",
    topology: "Four pieces live in your own repo; four pieces live on infrastructure someone else runs. Notice the KPI Catalog sits on the \"someone else's\" side even though this system reads from it constantly — that's the whole reason its fit rating is red.",
    appendix: "A tech-stack pick answers \"what,\" not \"how much\" or \"exactly how.\" Everything listed here is a real gap this document leaves for later, not an oversight."
  }
};
