---
name: standards-audit
description: Use when the user asks to audit, check, or verify this repo's coding standards — file size limits, test file naming, or type hints — across src/ and tests/, or asks whether the codebase is compliant with CLAUDE.md. Do NOT use this skill to fix violations; it only reports findings and cannot edit or create files.
allowed-tools: Read, Grep, Glob, Bash
---

# Standards Audit

## When to use this skill

- The user asks to audit, check, or verify coding standards across the repo.
- The user asks "are we compliant with CLAUDE.md" or similar.
- Not sufficient on its own: asking to fix one already-known violation — do that as an ordinary edit, this skill is the audit pass, not the fix pass.

## Process

1. Run `python .claude/skills/standards-audit/scripts/check_standards.py` from the repo root via Bash. It deterministically checks all three CLAUDE.md rules and prints JSON.
   - Do not count lines or inspect type hints by reading files yourself — the script is authoritative because eyeballing line counts and function signatures across many files is unreliable; that's the entire reason this skill has a script.
2. Before formatting the report, read `references/standards-checklist.md` — it defines what counts as PASS/WARN/FAIL for each rule.
3. Format the script's JSON output as a table: `Rule | File | Status | Detail`.
4. Finish with one overall verdict: **COMPLIANT** or **N VIOLATIONS FOUND**.

## Constraints

- This skill is read-only by design — see `allowed-tools` in the frontmatter, which omits `Write` and `Edit`. It cannot modify or create files even if asked to. If the user wants violations fixed, say so explicitly and handle that as a separate, ordinary request outside this skill.
- Report exactly what the script finds — do not editorialize or soften a FAIL.
