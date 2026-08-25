import pytest
from openpyxl import Workbook

from src.excel_analysis import (
    CorruptExcelFileError,
    UnsupportedExcelFormatError,
    analyze_report,
)


def test_analyze_report_extracts_content_from_labeled_and_tabular_sheets(tmp_path):
    workbook = Workbook()
    notes = workbook.active
    notes.title = "Notes"
    notes.append(["Objective: Increase visibility into quarterly regional sales performance"])
    notes.append(["Scope: Q1 2026 regional sales data across all product lines"])
    notes.append(["KPI: Total Revenue"])
    notes.append(["Filter: Region"])
    notes.append(["Calculation: Net Margin = Revenue - Cost"])
    notes.append(["Visual: Include a bar chart comparing revenue by region"])
    notes.append(["Reporting Expectation: Weekly summary email every Monday"])
    data = workbook.create_sheet("Data")
    data.append(["Region", "Revenue", "Cost", "Margin"])
    data.append(["East", 1000, 600, "=B2-C2"])
    data.append(["West", 1500, 900, "=B3-C3"])
    path = tmp_path / "sample_report.xlsx"
    workbook.save(path)

    result = analyze_report(str(path))

    assert "Notes" in result["scope"]
    assert "Data" in result["scope"]
    assert "Q1 2026 regional sales data across all product lines" in result["scope"]
    assert "Increase visibility into quarterly regional sales performance" in result["objectives"]
    assert "Total Revenue" in result["kpis"]
    assert "Revenue" in result["kpis"]
    assert "Region" in result["filters"]
    assert "Net Margin = Revenue - Cost" in result["calculations"]
    assert "B2-C2" in result["calculations"]
    assert "Include a bar chart comparing revenue by region" in result["visual_requirements"]
    assert "Weekly summary email every Monday" in result["reporting_expectations"]


def test_analyze_report_raises_on_corrupt_file(tmp_path):
    path = tmp_path / "report.xlsx"
    path.write_bytes(b"not a real workbook")

    with pytest.raises(CorruptExcelFileError):
        analyze_report(str(path))


def test_analyze_report_raises_on_unsupported_format(tmp_path):
    path = tmp_path / "report.csv"
    path.write_text("a,b,c")

    with pytest.raises(UnsupportedExcelFormatError):
        analyze_report(str(path))
