# PowerBI Blueprint — Demo Narrative

Speaking notes for presenting PowerBI Blueprint. Three beats: the problem, the one moment, the guardrail.

## The Problem

Every new Power BI report starts the same way: a stakeholder sends a message. An email, a Teams ping, sometimes a screenshot of an Excel report that doesn't match the dashboard anymore. Somewhere in that message is a business objective, a KPI, a data source, maybe a deadline — but it's buried in a paragraph of context, and right now a human reads every single one of these, one at a time, and decides by hand whether there's enough here to start building. That doesn't scale, and it's inconsistent — two analysts read the same message and reach different conclusions about what's actually being asked.

## The One Moment

Here's a real message: a stakeholder asks that each cost-center owner only see their own center's numbers on the spend report — but also wants a single combined report where leadership can compare all cost centers side by side. Read quickly, that sounds like two reasonable asks in one email. It isn't. Those are two access rules that can't both be true at once, and a tired analyst skimming a Friday inbox would wave it through.

*[Run it live here.]* The system doesn't wave it through. It comes back with `requirement_status: "conflicting"` and two follow-up questions asking which rule actually governs. That's the moment — not that the AI "understood" the request, but that it caught the contradiction a human under time pressure was about to miss.

## The Guardrail

The reason I trust that answer isn't the AI's confidence score — it's the rule underneath it. A request only gets marked ready to move forward if six specific things are present and unambiguous: business objective, calculation logic, data source, field mapping, priority, stakeholder approval. Miss one, it's `needs_human_review` — full stop, regardless of how fluent or confident the model's answer sounds. Confidence is only a second check on top of that, for cases that pass the rule but still feel shaky — the same way `msg12` got flagged in an earlier run despite technically checking every box.

And the boundary that makes this safe to actually use: the tool never approves anything. "Ready to move forward" means *enough is confirmed to start drafting* — not signed off. Every request, ready or not, still needs a person's name on it before work begins. The system's job is to make sure nothing slips through *unexamined* — not to replace the examination.
