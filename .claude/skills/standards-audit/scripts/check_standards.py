"""Deterministic checks for the three testable rules in the root CLAUDE.md.

Run from the repo root: python .claude/skills/standards-audit/scripts/check_standards.py
Prints a single JSON object to stdout; makes no writes anywhere.
"""
import ast
import json
from pathlib import Path

SRC_DIR = Path("src")
TESTS_DIR = Path("tests")
MAX_LINES = 200


def check_file_sizes() -> list[dict]:
    results = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        line_count = sum(1 for _ in path.open(encoding="utf-8"))
        results.append({"file": str(path), "line_count": line_count, "limit": MAX_LINES})
    return results


def check_test_naming() -> list[dict]:
    results = []
    for path in sorted(SRC_DIR.glob("*.py")):
        if path.stem in ("__init__",):
            continue
        expected = TESTS_DIR / f"test_{path.stem}.py"
        results.append({"module": str(path), "expected_test": str(expected), "exists": expected.exists()})
    return results


def check_type_hints() -> list[dict]:
    results = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                results.append({
                    "file": str(path),
                    "function": node.name,
                    "line": node.lineno,
                    "has_return_annotation": node.returns is not None,
                })
    return results


def main() -> None:
    report = {
        "file_sizes": check_file_sizes(),
        "test_naming": check_test_naming(),
        "type_hints": check_type_hints(),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
