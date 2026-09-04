"""
field_mapping.py

Maps the column headers of an uploaded report onto this system's approved
schema fields: REQUIRED_FIELDS from src/email_analysis.py, the same seven
categories analyze_email()/analyze_report() already populate and
requirement_clarification.py already validates against. That is REQ-003's
"approved current tables and columns" -- no richer data-model schema (real
table/column names) exists yet in this repo; that belongs to STORY-005+.

Headers that don't match any known synonym are flagged for review instead
of silently dropped. This differs from excel_analysis.py's _scan_headers(),
which only classifies kpis/filters from tabular headers and drops anything
else -- this module's whole job is to surface every unmapped header so a
data specialist can decide where it belongs.

Reading supports both real Excel workbooks (.xlsx/.xlsm, via openpyxl) and
.csv, unlike excel_analysis.py which treats .csv as unsupported. That
module parses full multi-sheet workbook content; this one only needs a
single header row, and a CSV export of a report is a reasonable input for
that narrower job.
"""

import argparse
import csv
import sys
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from src.email_analysis import REQUIRED_FIELDS

APPROVED_COLUMNS = REQUIRED_FIELDS

_SUPPORTED_EXTENSIONS = (".xlsx", ".xlsm", ".csv")

_COLUMN_SYNONYMS = {
    "business_objectives": {"objective", "business objective", "goal"},
    "scope": {"scope", "business unit", "department"},
    "kpis": {"kpi", "metric", "revenue", "sales", "profit", "total", "amount", "cost", "margin", "rate", "percent"},
    "filters": {"region", "date", "status", "category", "filter", "segment", "quarter", "year", "month"},
    "calculations": {"calculation", "formula"},
    "visual_requirements": {"visual", "chart", "graph"},
    "reporting_expectations": {"reporting expectation", "expectation", "frequency"},
}


class UnsupportedReportFormatError(Exception):
    """Raised when the file extension is not a supported report format."""


class CorruptReportFileError(Exception):
    """Raised when the file cannot be opened, or has no header row."""


def _normalize(text: str) -> str:
    """Lowercases, replaces underscores/hyphens with spaces, and collapses
    whitespace, so 'Total Revenue', 'total_revenue', and 'TOTAL-REVENUE'
    all compare the same way -- both for an exact approved-column match and
    for the substring keyword match below."""
    text = text.strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def map_fields(headers: list[str]) -> dict[str, str | None]:
    """Maps each incoming header to an approved column name (see
    APPROVED_COLUMNS). Returns a dict keyed by the original header text.
    Each value is the matching approved column, or None if no synonym
    matched -- callers treat None as "flag this field for review".

    A header matches a column either by naming it exactly (e.g. 'KPIs') or
    by containing one of its known synonym words/phrases (e.g. 'Total
    Revenue' contains 'revenue', a kpis synonym) -- a plain equality check
    on the whole header would miss every multi-word real-world header.
    """
    normalized_columns = {column: _normalize(column) for column in _COLUMN_SYNONYMS}

    mapping = {}
    for header in headers:
        normalized_header = _normalize(header)
        matched_column = next(
            (column for column, name in normalized_columns.items() if normalized_header == name),
            None,
        )
        if matched_column is None:
            matched_column = next(
                (
                    column
                    for column, synonyms in _COLUMN_SYNONYMS.items()
                    if any(synonym in normalized_header for synonym in synonyms)
                ),
                None,
            )
        mapping[header] = matched_column
    return mapping


def read_report_headers(path: str) -> list[str]:
    """Reads the header row of an uploaded report (.xlsx, .xlsm, or .csv)
    and returns it as a list of column names.

    Raises UnsupportedReportFormatError for an unrecognized extension, or
    CorruptReportFileError if the file can't be opened/parsed or has no
    header row -- one pair of exception types regardless of format, so
    callers don't need to know which library failure maps to which case.
    """
    lowered = path.lower()
    if not lowered.endswith(_SUPPORTED_EXTENSIONS):
        raise UnsupportedReportFormatError(f"Unsupported file format: {path}")

    if lowered.endswith(".csv"):
        return _read_csv_headers(path)
    return _read_xlsx_headers(path)


def _read_csv_headers(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            headers = next(csv.reader(f), None)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise CorruptReportFileError(f"Could not read report file: {path}") from exc

    if not headers:
        raise CorruptReportFileError(f"Report file has no header row: {path}")
    return headers


def _read_xlsx_headers(path: str) -> list[str]:
    # Deliberately not read_only=True: that mode keeps the workbook's zip
    # archive memory-mapped, which on Windows holds the OS file handle open
    # even after workbook.close() -- callers that save the upload to a temp
    # file and os.remove() it right after (see field_mapping_routes.py) hit
    # a PermissionError. We only need one row, so eager loading is fine.
    try:
        workbook = load_workbook(path, data_only=True)
    except (InvalidFileException, BadZipFile, OSError) as exc:
        raise CorruptReportFileError(f"Could not open Excel file: {path}") from exc

    sheet = workbook.active
    row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    workbook.close()

    if not row or all(value is None for value in row):
        raise CorruptReportFileError(f"Report file has no header row: {path}")
    return [str(value).strip() if value is not None else "" for value in row]


def _main(argv: list[str] | None = None) -> int:
    """CLI entry point: `python -m src.field_mapping <path>` (run from the
    repo root, so the `src.email_analysis` import above resolves)."""
    parser = argparse.ArgumentParser(description="Map a report's column headers to this system's approved fields.")
    parser.add_argument("path", help="Path to a .xlsx, .xlsm, or .csv report")
    args = parser.parse_args(argv)

    try:
        headers = read_report_headers(args.path)
    except (UnsupportedReportFormatError, CorruptReportFileError) as exc:
        print(f"Error: {exc}")
        return 1

    mapping = map_fields(headers)
    mapped = {header: column for header, column in mapping.items() if column is not None}
    flagged = [header for header, column in mapping.items() if column is None]

    print("Mapped fields:")
    for header, column in mapped.items():
        print(f"  {header!r} -> {column}")

    if flagged:
        print("Flagged for review (no matching approved column):")
        for header in flagged:
            print(f"  {header!r}")

    return 0


if __name__ == "__main__":
    sys.exit(_main())
