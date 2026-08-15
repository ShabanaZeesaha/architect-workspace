---
name: system-architect
description: Use when the user has a project idea and wants a system architecture, a technical design, or a diagram of how it would work.
---

# System Architect

Use this skill when the user gives a one-paragraph project idea and wants a concrete system architecture, technical design, or workflow diagram.

## Instructions

1. Read the project idea carefully and extract the real goals, users, workflows, and constraints that are actually mentioned.
2. Identify the specific components this idea needs, such as:
   - frontend
   - backend/API
   - database
   - external services
   - AI/agent layer if the idea depends on automation, reasoning, content creation, or decision-making
3. Tailor the architecture to the idea itself. Do not produce a generic template that ignores the details in the paragraph.
4. Produce a genuine Mermaid flowchart that shows the components and the flow of data between them.
5. Explain each component in one plain-English sentence that a non-technical person could follow.
6. Save the completed result to project-blueprint/architecture.md.

## Output requirements

- Start with a short summary of the project idea.
- List the real components the idea requires, with a brief reason for each.
- Include a Mermaid flowchart showing how the components connect and how data moves.
- Provide a plain-English explanation for each component.
- Keep the architecture grounded in the specific idea rather than using a generic starter template.

## Quality bar

If the idea involves user accounts, payments, notifications, uploads, search, messaging, analytics, or AI assistance, those should appear as concrete architecture elements rather than being treated as vague placeholders.
