from src.data_validation_rules import find_data_accuracy_violations

_ANALYSIS = {
    "business_objectives": ["Increase quarterly revenue"],
    "scope": ["North America region"],
    "kpis": ["Monthly Revenue Growth"],
    "filters": ["Region", "Product Category"],
    "calculations": ["Year over year growth rate"],
    "visual_requirements": ["Bar chart of sales by region"],
    "reporting_expectations": ["Weekly refresh"],
}


def test_returns_no_violations_when_every_binding_traces_to_the_analysis():
    draft_solution = {
        "pages": [
            {
                "title": "Sales Overview",
                "visuals": [
                    {
                        "type": "bar_chart",
                        "purpose": "Show sales by region",
                        "field_bindings": ["Region", "Revenue Growth"],
                    }
                ],
            }
        ]
    }

    violations = find_data_accuracy_violations(_ANALYSIS, draft_solution)

    assert violations == []


def test_flags_a_binding_that_does_not_trace_to_the_analysis():
    draft_solution = {
        "pages": [
            {
                "title": "Sales Overview",
                "visuals": [
                    {
                        "type": "kpi_card",
                        "purpose": "Show customer value",
                        "field_bindings": ["Customer Lifetime Value"],
                    }
                ],
            }
        ]
    }

    violations = find_data_accuracy_violations(_ANALYSIS, draft_solution)

    assert len(violations) == 1
    assert "Customer Lifetime Value" in violations[0]
    assert "Sales Overview" in violations[0]
    assert "Show customer value" in violations[0]


def test_matching_is_case_insensitive():
    draft_solution = {
        "pages": [
            {"title": "Sales Overview", "visuals": [{"type": "table", "purpose": "List filters", "field_bindings": ["region"]}]}
        ]
    }

    violations = find_data_accuracy_violations(_ANALYSIS, draft_solution)

    assert violations == []


def test_a_visual_with_no_field_bindings_produces_no_violations():
    draft_solution = {
        "pages": [
            {"title": "Sales Overview", "visuals": [{"type": "slicer", "purpose": "Filter by region", "field_bindings": []}]}
        ]
    }

    violations = find_data_accuracy_violations(_ANALYSIS, draft_solution)

    assert violations == []


def test_reports_one_violation_per_unmatched_binding_across_multiple_pages():
    draft_solution = {
        "pages": [
            {
                "title": "Sales Overview",
                "visuals": [{"type": "bar_chart", "purpose": "Show sales", "field_bindings": ["Region", "Fabricated Metric"]}],
            },
            {
                "title": "Details",
                "visuals": [{"type": "table", "purpose": "List records", "field_bindings": ["Another Fabricated Field"]}],
            },
        ]
    }

    violations = find_data_accuracy_violations(_ANALYSIS, draft_solution)

    assert len(violations) == 2
