# Tech Stack: AI-Powered Power BI Requirements System

> Build an AI-powered Power BI requirement system for business stakeholders. Users submit their reporting requirements, the system analyzes and stores them, asks follow-up questions when information is missing, and recommends the appropriate data sources, KPIs, and report structure. On day one, it must turn a stakeholder's business request into clear, structured Power BI requirements.

**Scale assumption driving every rating below:** this is a day-one / early-stage build — one small team, four build phases over roughly 20 days (see `architecture.md`), not an enterprise rebuild. A technology can be excellent in general and still rated 🔴 here if it's more machinery than this specific system needs on day one.

## Fit-Rating Key

| Icon | Meaning |
|---|---|
| 🟢 great fit | Matches this project's size and needs — pick it, move on. |
| 🟡 good fit | Works, but there's a real caveat worth reading first. |
| 🔴 consider carefully | Where this plan is most likely to hurt — a genuine risk, not a nitpick. |

## Where This Stack Is Most Likely to Break

This stack is most likely to break in one place: the **KPI and Data Source Catalog**. Every other row below is an ordinary early-stage web stack — React, Express, Postgres, a managed host — but the catalog recommendation only works if an org data dictionary or BI semantic model *already exists* to read from. `architecture.md`'s own Assumption 2 and its "one question that would most change the design" both point at the same fact: if that catalog doesn't already exist, Phase 3 stops being an integration and becomes its own catalog-curation project, and no technology choice below fixes that — only an answer to that open question does.

## Recommendations

Grouped by what each piece actually is: something a person touches, something you write, something you store, something you depend on, or something the data flow needs that the component list never named.

### Things a person touches

| Component | Recommended Tech | Fit | Why (plain English) | Learn More Prompt |
|---|---|---|---|---|
| Stakeholder Intake UI | React 18 + Vite (TypeScript) | 🟢 | A friendly form-and-chat screen for typing a request and answering follow-up questions — React is the most common toolkit for screens like this, and Vite starts it up in seconds with no setup. | "Explain React and Vite to me like I'm new to frontend frameworks, using my AI-Powered Power BI Requirements System's Stakeholder Intake UI as the example. What would the follow-up question screen actually look like in code?" |

### Things you write

| Component | Recommended Tech | Fit | Why (plain English) | Learn More Prompt |
|---|---|---|---|---|
| Backend API / Orchestrator | Node.js + Express (TypeScript) | 🟢 | The traffic cop between the UI, the AI, and the database — Express is a small, well-understood way to write API routes without dragging in a bigger framework than a handful of endpoints needs. | "Explain Node.js and Express to me like I'm new to backend frameworks, using my Power BI Requirements System's Backend API / Orchestrator as the example. How would it route a submission to the AI Engine and back?" |
| AI Analysis and Recommendation Engine | Anthropic TypeScript SDK (`@anthropic-ai/sdk`, Messages API) | 🟡 | The code that actually talks to Claude and decides what to do with the answer — the plain SDK is a thin, well-documented wrapper, not a bigger "agent framework." **Caveat:** it gives you no built-in retry loop or structured-output enforcement, so you write that glue yourself (Zod, below, covers the output side). | "Explain the Anthropic TypeScript SDK to me like I'm new to calling LLM APIs, using my AI Analysis and Recommendation Engine as the example. What would the analysis prompt and response handling look like?" |
| Requirement Structuring and Validation | Zod | 🟢 | A schema — think of it as a strict form template — that Zod checks the AI's draft against before anything counts as "finished." This is the actual code-level mechanism behind the day-one promise. | "Explain Zod to me like I'm new to schema validation, using my Requirement Structuring and Validation component as the example. What would the fixed requirements schema look like in code?" |

### Things you store

| Component | Recommended Tech | Fit | Why (plain English) | Learn More Prompt |
|---|---|---|---|---|
| Requirements Database | PostgreSQL 16 | 🟢 | A single reliable place to keep every submission, follow-up answer, and finished requirement — Postgres handles this project's structured, fixed-schema data comfortably with room to grow. | "Explain PostgreSQL to me like I'm new to databases, using my Requirements Database as the example. What tables would I actually have?" |
| KPI and Data Source Catalog | PostgreSQL (read-only schema, same instance) | 🔴 | The org's existing list of real KPIs and data sources, queried but not owned by this system. **Caveat:** this rating only holds if that list already exists somewhere in the org — if it doesn't, this row understates a materially bigger project (see "Where This Stack Is Most Likely to Break" above). | "Explain how to connect to an existing PostgreSQL-based data catalog to me like I'm new to databases, using my KPI and Data Source Catalog component as the example. What would a read-only query look like?" |

### Things you depend on

| Component | Recommended Tech | Fit | Why (plain English) | Learn More Prompt |
|---|---|---|---|---|
| Claude LLM API | Claude Sonnet 5 (Anthropic API) | 🟢 | The language model that reads the request, asks good follow-up questions, and drafts the recommendation — Sonnet 5 balances quality and cost well for structured back-and-forth text tasks like this one, without paying for reasoning power this task doesn't need day one. | "Explain Claude Sonnet 5 to me like I'm new to choosing LLM models, using my Power BI Requirements System as the example. Why is it a good fit for analyzing stakeholder requests instead of a smaller or bigger model?" |

### Things the data flow needs

The component list never names a place for the system to actually run — but the data flow (someone besides you has to reach the UI) requires one.

| Component | Recommended Tech | Fit | Why (plain English) | Learn More Prompt |
|---|---|---|---|---|
| Hosting & Deployment | Render (managed PaaS — a company that runs your servers for you) | 🟡 | Where the frontend, backend, and database actually run once someone besides you can reach them. **Caveat:** Render needs almost no setup for a day-one system, but you trade away fine-grained infrastructure control, and costs can climb awkwardly if usage grows a lot. | "Explain Render (or a similar managed PaaS) to me like I'm new to deployment, using my Power BI Requirements System as the example. What would go live on day one?" |

## Fit Summary

🟢 5 · 🟡 2 · 🔴 1 — 8 rows total.

**Least confident about:**
1. **KPI and Data Source Catalog (🔴).** The rating itself is confident — the risk is real — but the *right* technology depends entirely on an answer this document doesn't have: does the catalog already exist, and if so, in what system? "A read-only Postgres schema" is a placeholder for "whatever the org's real data dictionary turns out to be."
2. **Hosting & Deployment (🟡).** Render is the safe day-one default, but this is the row most likely to change once real traffic or compliance requirements show up — see "How Hard to Undo" below.

## What to Learn First, In Order

1. **PostgreSQL** — everything else stores into or reads from it; understanding tables first makes every other piece make sense.
2. **Express** — the shape every other piece connects through (UI in, AI engine out, database underneath).
3. **Zod** — small, fast payoff, and it's the direct code behind the day-one promise.
4. **Anthropic SDK / Claude API** — the "AI" part, but it only makes sense once you know what shape of data it has to produce (Zod, learned first).
5. **React + Vite** — the UI can be stubbed with plain HTML while the backend loop gets proven; learn it once there's something real to display.
6. **Render (hosting)** — last, once there's something worth deploying.

## Alternatives Considered

| Component | Alternative | Why Not |
|---|---|---|
| Stakeholder Intake UI | Next.js | Its server-rendering and file-based routing solve problems (SEO, multi-page navigation) this single intake-and-follow-up flow doesn't have yet. |
| Backend API / Orchestrator | Python + FastAPI | A fine choice on its own, but it splits the stack across two languages (TypeScript frontend, Python backend) for no requirement-driven reason. Express keeps one language end-to-end. |
| AI Analysis and Recommendation Engine | Full Claude Agent SDK / LangChain | Built for autonomous, multi-tool agent loops. This engine's actual job — analyze, ask-or-draft, wait for validation — doesn't need that orchestration machinery; it's unused weight on day one. |
| Claude LLM API | Claude Opus 5 | Stronger reasoning than a structured extraction-and-drafting task needs, at meaningfully higher cost and latency per stakeholder submission. |
| KPI and Data Source Catalog | A dedicated catalog microservice, built in-house | Premature — `architecture.md` assumes the catalog already exists elsewhere. Building one is a different, larger project that should only start once that assumption is confirmed false. |
| Requirements Database | MongoDB | The requirement schema is fixed and relational (Assumption 1 in `architecture.md`). A document store adds flexibility this project doesn't need and gives up the cross-record consistency a relational store provides for free. |
| Requirement Structuring and Validation | Hand-written if/else checks | Works today, breaks silently the first time the schema grows a field. Zod keeps the check declarative, in one place, and impossible to accidentally skip. |
| Hosting & Deployment | Self-managed VPS + Docker + Nginx | More control, but real ongoing ops burden (patching, TLS, uptime) for a team that, per `architecture.md`, is trying to prove a day-one promise — not run infrastructure. |

## How Hard Is Each Decision to Undo

| Component | Difficulty to change later | Why |
|---|---|---|
| Stakeholder Intake UI (React + Vite) | Easy | The UI is the most replaceable layer — it talks to the backend over a normal HTTP API, so swapping frameworks doesn't touch anything else. |
| Backend API / Orchestrator (Express) | Medium | The frontend depends on its route shapes, but Express itself is a thin layer over plain HTTP — a rewrite is real work, not a rearchitecture. |
| AI Analysis and Recommendation Engine (Anthropic SDK) | Medium | Swapping model providers means rewriting prompts and re-tuning behavior, not just plumbing — the SDK call itself is easy to change, the prompt engineering behind it isn't. |
| Claude LLM API (Claude Sonnet 5) | Medium | Usually a config change plus prompt re-tuning to move to a different Claude model; moving to a different vendor entirely is closer to the AI Engine's "medium" above. |
| KPI and Data Source Catalog (Postgres, read-only) | Easy | It's read-only queries against someone else's data — pointing them at a different source doesn't touch anything this system owns. |
| Requirements Database (Postgres) | Hard | All persisted data has to migrate, and the fixed schema (Assumption 1) is load-bearing for the rest of the system — this is the hardest row to walk back. |
| Requirement Structuring and Validation (Zod) | Easy | Validation logic is isolated in one schema file — swapping the library doesn't touch the data it validates. |
| Hosting & Deployment (Render) | Medium | Moving off a managed PaaS means learning infrastructure you didn't need before, but it's an ops migration, not a code rewrite. |

## What This Document Does NOT Tell You

- **Exact Postgres table and column names** — that's a data-model design task, not a tech-stack pick.
- **Prompt wording for the Claude calls** — the analysis and drafting prompts still have to be written and iterated on; "use Claude Sonnet 5" says nothing about what you ask it.
- **Whether the KPI catalog actually exists in your org** — the single open question that changes the whole KPI/Catalog row and, per `architecture.md`, the whole Phase 3 scope.
- **Cost estimates** — both Anthropic API usage and Render's pricing tier depend on real traffic this document doesn't know yet.
- **Authentication** — `architecture.md` explicitly has none on day one, so no row above addresses it; adding auth later touches the Backend, the UI, and possibly the Catalog's access rules.
