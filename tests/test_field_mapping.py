import pytest
from openpyxl import Workbook

from src.field_mapping import (
    APPROVED_COLUMNS,
    CorruptReportFileError,
    UnsupportedReportFormatError,
    map_fields,
    read_report_headers,
)
from src.field_mapping import _main


def test_map_fields_matches_exact_approved_column_names():
    result = map_fields(list(APPROVED_COLUMNS))

    assert result == {column: column for column in APPROVED_COLUMNS}


def test_map_fields_matches_known_synonyms_case_and_whitespace_insensitively():
    headers = ["Total Revenue", " Region ", "KPI"]

    result = map_fields(headers)

    assert result == {"Total Revenue": "kpis", " Region ": "filters", "KPI": "kpis"}


def test_map_fields_flags_unrecognized_header_as_unmapped():
    headers = ["Employee Shoe Size", "Region"]

    result = map_fields(headers)

    assert result["Employee Shoe Size"] is None
    assert result["Region"] == "filters"


def test_map_fields_with_no_headers_returns_empty_mapping():
    result = map_fields([])

    assert result == {}


def test_read_report_headers_returns_first_row_of_a_csv(tmp_path):
    report = tmp_path / "report.csv"
    report.write_text("Region,Total Revenue\nEast,1000\n", encoding="utf-8")

    result = read_report_headers(str(report))

    assert result == ["Region", "Total Revenue"]


def test_read_report_headers_returns_first_row_of_an_xlsx_workbook(tmp_path):
    workbook = Workbook()
    workbook.active.append(["Region", "Total Revenue", "Employee Shoe Size"])
    path = tmp_path / "report.xlsx"
    workbook.save(path)

    result = read_report_headers(str(path))

    assert result == ["Region", "Total Revenue", "Employee Shoe Size"]


def test_read_report_headers_rejects_unsupported_extension(tmp_path):
    report = tmp_path / "report.txt"
    report.write_text("Region,Total Revenue\n", encoding="utf-8")

    with pytest.raises(UnsupportedReportFormatError):
        read_report_headers(str(report))


def test_read_report_headers_raises_on_corrupt_xlsx(tmp_path):
    path = tmp_path / "report.xlsx"
    path.write_bytes(b"not a real workbook")

    with pytest.raises(CorruptReportFileError):
        read_report_headers(str(path))


def test_read_report_headers_raises_on_empty_xlsx(tmp_path):
    workbook = Workbook()
    path = tmp_path / "report.xlsx"
    workbook.save(path)
    # A brand-new sheet has no cells at all, so the header row is empty --
    # distinct from the corrupt-file case above, same exception either way.

    with pytest.raises(CorruptReportFileError):
        read_report_headers(str(path))


def test_read_report_headers_raises_on_empty_csv(tmp_path):
    report = tmp_path / "report.csv"
    report.write_text("", encoding="utf-8")

    with pytest.raises(CorruptReportFileError):
        read_report_headers(str(report))


def test_main_prints_mapped_and_flagged_fields_for_a_valid_report(tmp_path, capsys):
    report = tmp_path / "report.csv"
    report.write_text("Region,Employee Shoe Size\n", encoding="utf-8")

    exit_code = _main([str(report)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "'Region' -> filters" in output
    assert "'Employee Shoe Size'" in output
    assert "Flagged for review" in output


def test_main_returns_nonzero_and_prints_error_for_a_bad_report(tmp_path, capsys):
    report = tmp_path / "report.txt"
    report.write_text("not a report", encoding="utf-8")

    exit_code = _main([str(report)])

    assert exit_code == 1
    assert "Error:" in capsys.readouterr().out
