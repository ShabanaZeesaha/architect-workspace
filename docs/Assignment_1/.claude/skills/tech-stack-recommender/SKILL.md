---
name: tech-stack-recommender
description: Use when the user has a system architecture and wants a recommended tech stack, explained simply.
---

# Tech Stack Recommender

Use this skill when the user has an existing system architecture (components + data flow already defined) and wants a concrete, current technology recommended for each piece — explained in plain English, not a generic "industry standard" list.

## Instructions

1. Read `project-blueprint/architecture.md` fully. Pull out every component listed there (e.g. from the Components table and the Mermaid diagram) — frontend, backend, database, AI/LLM layer, catalogs, queues, third-party services, whatever the architecture actually names.
2. For each component, recommend exactly **one** real, currently-maintained technology. No "or X or Y" hedging — pick the one you'd actually ship with, given this idea's scale (a day-one / early-stage system per the architecture doc, not an enterprise-scale rebuild).
3. Assign a fit rating to every recommendation based on how well it matches *this project's actual scale and needs* — not a default rating you give the technology everywhere else:
   - 🟢 **great fit** — squarely matches the scale, team size, and requirements implied by the architecture.
   - 🟡 **good fit** — works fine, but there's a mild mismatch (e.g. more powerful than the idea currently needs, or a small tradeoff worth knowing about).
   - 🔴 **consider carefully** — works but carries a real risk, cost, or scaling mismatch for this idea specifically (e.g. overkill, vendor lock-in, or a known rough edge) — explain the risk, don't just flag it.
4. For each row, write the "why" as one plain-English sentence. No unexplained jargon — if a technical term is unavoidable (e.g. "ORM", "vector database", "managed service"), give a one-line plain-English definition inline.
5. End every row with a copy-ready prompt the user could paste into a later conversation to learn more about that specific technology, framed against their own project. Format: *"Explain \<technology\> to me like I'm new to \<category\>, using my project as the example."* Adjust the framing to fit the technology (e.g. databases, hosting, AI APIs).
6. Save the completed result to `project-blueprint/tech-stack.md`.

## Output requirements

- Open with a one-paragraph summary restating the project idea (pull from `architecture.md`) and the scale assumption driving the ratings (e.g. "day-one / early-stage, not enterprise scale").
- One table, one row per architecture component, with columns: **Component | Recommended Tech | Fit | Why (plain English) | Learn More Prompt**.
- Use short labels and icons over long prose — this is meant to be scannable, not a wall of text.
- Close with a **Fit Summary** line: counts of 🟢 / 🟡 / 🔴 across the table.
- Keep every recommendation traceable to a component that's actually in `architecture.md` — don't invent components that aren't there, and don't skip any that are.

## Quality bar

- Ratings must be earned by this specific idea's scale, not copy-pasted defaults. The same technology (e.g. Kubernetes, a managed vector DB) can be 🔴 for a day-one MVP and 🟢 for a system already proven at scale — justify the rating against what `architecture.md` actually describes.
- Every "why" sentence must be understandable by someone with no engineering background. If it needs a technical term, define it in the same sentence, in plain words.
- Every row must end with a working copy-ready prompt — no row should be left without one.
