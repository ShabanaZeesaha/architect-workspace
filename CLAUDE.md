# CLAUDE.md

## Project: AI-Project

Personal workspace for working through an AI course (see [README.md](README.md)). Python, built around a small Flask app (`src/app.py`) exercised by pytest. Dependencies: `flask`, `python-dotenv`, `requests`, `supabase`, `pytest` (see [requirements.txt](requirements.txt)).

## Coding Standards

1. **Naming:** every test file lives at `tests/test_<module>.py`, mirroring the module it tests in `src/<module>.py`. (Testable: `pytest tests/` must discover and run it — pytest's default discovery depends on this pattern.)
2. **File size:** files under `src/` stay under 200 lines. If a change would push a file over 200 lines, split it before adding more code. (Testable: `(Get-Content <file> | Measure-Object -Line).Lines` ≤ 200.)
3. **Type hints:** functions in `src/` declare return types at minimum (see `create_app() -> Flask` in [src/app.py](src/app.py)).

## Conventions

1. **Running tests:** run the full suite with `pytest tests/` from the repo root. (Testable: exit code 0 = pass.)
2. **Test structure:** tests follow arrange/act/assert with a blank line between each phase (see [tests/test_app.py](tests/test_app.py)).
3. **Secrets:** configuration and credentials (e.g. Supabase keys) load via `python-dotenv` from a local `.env` file, never hard-coded in `src/`.
