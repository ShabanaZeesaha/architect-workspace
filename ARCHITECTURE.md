# Architecture

Status: **FOUNDATION APPROVED** (2026-07-30). This document records the approved
folder architecture for AI-Project and the reasoning behind it. It reflects
structure only — no product features are described or implied here.

## Project context

This is a personal workspace for working through an AI course (see
`README.md`). As of this writing, no requirements doc, Project Builder
output, or course brief has been located in the repository, so the specific
product (what it does, who it serves) is **not yet defined** and is not
guessed at in this document. Update this section once that definition
exists.

## Stack (from `requirements.txt`)

- flask
- python-dotenv
- requests
- supabase
- pytest

## Governing rules (`CLAUDE.md`)

1. **Naming:** every test file lives at `tests/test_<module>.py`, mirroring
   the module it tests in `src/<module>.py`.
2. **File size:** files under `src/` stay under 200 lines; split before
   adding more code if a change would exceed it.
3. **Running tests:** run the full suite with `pytest tests/` from the repo
   root.

## Approved structure

```
AI-Project/
├── src/            EXISTING
├── tests/          EXISTING
├── .venv/          GENERATED / DO-NOT-TOUCH
├── README.md       EXISTING
├── CLAUDE.md        EXISTING / DO-NOT-TOUCH
├── PROGRESS.md      EXISTING
├── ARCHITECTURE.md  NEW (this file)
├── requirements.txt EXISTING
└── .env             DEFERRED — not created; see below
```

No new top-level folders were approved or created. Every folder in the
approved architecture already existed or is tool-generated; the only
outstanding item (`.env`) is intentionally deferred.

### `src/`
- **Purpose:** production Python modules (the package under test).
- **Belongs:** feature modules, each under 200 lines.
- **Never:** tests, scratch scripts, data dumps, secrets, virtual env.
- **Rule:** CLAUDE.md Rule 1, Rule 2.
- **Status:** EXISTING.
- **Verify:** `(Get-Content <file> | Measure-Object -Line).Lines` ≤ 200;
  `pytest tests/` discovers a matching test per module.

### `tests/`
- **Purpose:** test suite mirroring `src/` one-for-one.
- **Belongs:** `test_<module>.py` files only.
- **Never:** production code, non-test helpers without `test_` prefix.
- **Rule:** CLAUDE.md Rule 1, Rule 3.
- **Status:** EXISTING.
- **Verify:** `pytest tests/` exits 0.

### `.venv/`
- **Purpose:** isolated interpreter + installed deps from `requirements.txt`.
- **Belongs:** nothing manual — tool-managed only.
- **Never:** manual edits, commits, direct imports.
- **Rule:** implied by Python stack + `requirements.txt`.
- **Status:** GENERATED / DO-NOT-TOUCH.
- **Verify:** `pip freeze` (inside it) matches `requirements.txt`.

### `.env` (deferred, not created)
- **Purpose:** local secrets/config (e.g. Supabase URL/key) via
  `python-dotenv`.
- **Rule:** supported by `python-dotenv` + `supabase` in `requirements.txt`.
- **Status:** DEFERRED — creating it means wiring real config for a product
  feature (Supabase integration), which is out of scope for this
  foundation-only pass. Create it when that feature work actually starts.

### Explicitly excluded (no supporting evidence)
`docs/`, `scripts/`, `data/`, `config/`, `static/`, `templates/`,
`migrations/`, `.github/` — none are justified by CLAUDE.md,
`requirements.txt`, or the existing tree today. Re-evaluate only when a
concrete requirement (e.g. a route that renders a template) creates one.

## Open items
- Project definition (what/who/why) is still missing — needed before any
  product feature work begins.
- Week 3 component: name and purpose unknown. Recommended home once defined:
  `src/<week3_module>.py` with mirrored `tests/test_<week3_module>.py`
  (splitting into a package only if it naturally decomposes), per Rule 1,
  staying under 200 lines per Rule 2.
