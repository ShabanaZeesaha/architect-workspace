# Standards Checklist

Definitions for each rule checked by `scripts/check_standards.py`, per the root CLAUDE.md.

## 1. File size

- **Rule:** files under `src/` stay ≤200 lines.
- **Evidence:** `line_count` from the script's `file_sizes` output.
- **Scoring:** `line_count > 200` → FAIL. `180–200` → WARN (approaching limit). `≤180` → PASS.

## 2. Test naming

- **Rule:** every `src/<module>.py` has a matching `tests/test_<module>.py`.
- **Evidence:** `exists` from the script's `test_naming` output.
- **Scoring:** `exists: false` → FAIL. `exists: true` → PASS.

## 3. Type hints

- **Rule:** functions in `src/` declare return types at minimum.
- **Evidence:** `has_return_annotation` from the script's `type_hints` output, per function.
- **Scoring:** `has_return_annotation: false` → FAIL for that function. `true` → PASS. Report every FAIL individually — do not collapse multiple missing annotations into one line.
