---
name: mvp-scoper
description: Use when the user wants to know what to build first, see what their idea could look like, and get a short pitch for it.
allowed-tools: Read, Write, Bash(*--print-to-pdf*)
---

# MVP Scoper

Use this skill when the user has a project idea and wants three concrete things: what to build first, what it could look like, and a short pitch to show someone. Works best after `system-architect` and `tech-stack-recommender` have already produced `project-blueprint/architecture.md` and `project-blueprint/tech-stack.md`, but must still produce useful output if they haven't run yet.

## Instructions

1. Read `project-blueprint/architecture.md` and `project-blueprint/tech-stack.md` fully if they exist. Pull the real idea summary, the real components, and the real recommended technologies from them — never invent components that aren't there. If either file is missing, work from the idea as described in the conversation and say so plainly in `mvp-plan.md`'s Notes section.
2. Produce exactly three files in `project-blueprint/`:
   - `mvp-plan.md`
   - `mockup.html`
   - `one-pager.pdf`

### 1. mvp-plan.md — the smallest real slice to build in Week 1

- Follow `template.md` (in this skill's folder) exactly — same section headings, same order — so every plan this skill produces has the same shape.
- Identify the smallest real slice of the idea that could be built in one week and would prove the idea actually works. This is a proof-of-concept core, not a backlog of everything the product will eventually need.
- Every checklist item must trace back to a specific component in `architecture.md` and a specific technology in `tech-stack.md`. No generic filler ("set up CI/CD", "write documentation") unless the idea specifically needs it in week one.
- Write it as a literal, actionable checklist (`- [ ] ...`) a solo builder could follow start to finish in a week.
- Save to `project-blueprint/mvp-plan.md`.

### 2. mockup.html — a real mockup of the main screen

- One self-contained HTML file: inline `<style>`, no external requests (no CDN links, no external fonts/icon libraries, no remote images).
- Show the idea's main screen — whichever sells the idea better, a landing page or the core in-app view.
- Real, idea-specific content: an actual product name, actual sample data and copy that could plausibly belong to this idea. No "Lorem ipsum", no "Card 1 / Card 2" placeholders, no gray wireframe boxes standing in for content.
- Visually real, not structural: a coherent color palette, a real layout (nav, hero/main area, sections), icons (inline SVG or unicode/emoji — never an external icon font), a readable type scale. It should look like something worth screenshotting and showing someone, not a bare skeleton of divs.
- Save to `project-blueprint/mockup.html`.

### 3. one-pager.pdf — a short marketing pitch, as a real PDF

- Marketing pitch, not a technical spec: what it does, who needs it, one sentence on why it matters. Short, punchy, icon-led lines — not paragraphs of prose or an architecture summary.
- Build path: write a single print-styled HTML file first (one page, `@page` sized, no overflow) to a scratch location, then convert it to PDF in one Bash call using a headless browser's print-to-PDF flag. Use whichever browser binary is actually installed on this machine (`msedge`, `chrome`, `google-chrome`, or `chromium` are all acceptable) — check what's available before picking one.
- Example command shape:
  ```
  msedge --headless --disable-gpu --print-to-pdf="project-blueprint/one-pager.pdf" --print-to-pdf-no-header "file:///<absolute path to the scratch one-pager html>"
  ```
- Never save the one-pager as a `.md` or `.html` file renamed with a `.pdf` extension — it must be produced by an actual PDF-generating tool (headless-Chrome print-to-PDF, a Python library such as reportlab, or a Node library such as puppeteer).
- Delete the scratch HTML once the PDF exists — only the PDF ships in `project-blueprint/`.
- Save to `project-blueprint/one-pager.pdf`.

## Output requirements

- All three files land in `project-blueprint/`, alongside `architecture.md` and `tech-stack.md` when present.
- `mvp-plan.md`'s section order and headings match `template.md` verbatim.
- `mockup.html` opens correctly in a browser with zero external network requests.
- `one-pager.pdf` is a real, valid single-page PDF — never a renamed `.html`/`.md` file.

## Quality bar

- Nothing generic: the mockup's copy, the plan's checklist items, and the one-pager's pitch must all be specific to the idea actually discussed, never filled with placeholder text.
- If `architecture.md` or `tech-stack.md` don't exist yet, still produce all three files, but flag it plainly in `mvp-plan.md`'s Notes section so the user knows the plan wasn't grounded in a saved architecture.
- The three files must agree with each other — the mockup should show the same product the plan is building and the one-pager is pitching, not three disconnected ideas of what this is.
