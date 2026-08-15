---
name: pytest-scaffold
description: Use when the user asks to create, scaffold, or add a new test file for a module in src/. Generates a tests/test_<module>.py file following this repo's arrange/act/assert convention with blank lines between phases. Do NOT use for editing or fixing an existing test file, or for running tests — only for creating a new one from scratch.
---

# Pytest Scaffold

## When to use this skill

- The user asks to create a new test file for a module in `src/`.
- Not sufficient on its own: asking to edit an existing test, debug a failing test, or just run `pytest`.

## Inputs

1. Require the target module name (e.g. `app` for `src/app.py`). If not given, ask — do not guess.
2. Read the target module (`src/<module>.py`) to identify its public functions and Flask routes.
3. Confirm `tests/test_<module>.py` does not already exist. If it does, stop and tell the user — this skill only creates new files, it never overwrites.

## Process

**Before writing, read `references/example-test.md`** — it has a worked example in this repo's exact style (Flask test client, arrange/act/assert, no comments).

1. Create `tests/test_<module>.py`.
2. For each public function or route in the target module, write one test:
   - Function/test name: `test_<behavior_described>`.
   - Body in three phases — arrange, act, assert — separated by a blank line each, matching [tests/test_app.py](../../../tests/test_app.py).
   - Add type hints on any helper functions, per this repo's coding standard.
3. Do not assert behavior you haven't verified by reading the source function — if the expected output isn't obvious from the code, ask rather than guess.

## Output

Report the file path created and a one-line summary of which functions/routes got a test stub.

## Constraints

- Never overwrite an existing test file — only create new ones.
- Never invent secrets, credentials, or `.env` values in test fixtures.
- Keep generated test files under this repo's 200-line file-size standard; if a module needs more coverage than that, say so instead of writing an oversized file.
