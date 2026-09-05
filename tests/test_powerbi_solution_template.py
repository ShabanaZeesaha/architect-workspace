import pytest

from src.dashboard_mockup_template import validate_mockup_shape
from src.powerbi_solution_template import (
    DraftMockupMismatchError,
    InvalidDraftSolutionResponseError,
    find_mockup_alignment_violations,
    validate_solution_shape,
)

_MOCKUP = validate_mockup_shape(
    {
        "pages": [
            {
                "title": "Regional Sales Overview",
                "visuals": [
                    {"type": "bar_chart", "purpose": "Revenue by region"},
                    {"type": "kpi_card", "purpose": "Total revenue"},
                ],
            }
        ]
    }
)

_VALID_SOLUTION_REPLY = {
    "pages": [
        {
            "title": "Regional Sales Overview",
            "visuals": [
                {
                    "type": "bar_chart",
                    "purpose": "Revenue by region",
                    "field_bindings": ["Sales[Region]", "Total Revenue"],
                },
                {
                    "type": "kpi_card",
                    "purpose": "Total revenue",
                    "field_bindings": ["Total Revenue"],
                },
            ],
        }
    ]
}


def test_validate_solution_shape_returns_pages_visuals_and_field_bindings_for_a_well_formed_reply():
    result = validate_solution_shape(_VALID_SOLUTION_REPLY)

    assert result == _VALID_SOLUTION_REPLY


def test_validate_solution_shape_raises_when_pages_is_missing():
    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape({})


def test_validate_solution_shape_raises_when_pages_is_empty():
    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape({"pages": []})


def test_validate_solution_shape_raises_when_a_page_has_no_title():
    reply = {
        "pages": [
            {"visuals": [{"type": "bar_chart", "purpose": "x", "field_bindings": ["f"]}]}
        ]
    }

    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape(reply)


def test_validate_solution_shape_raises_when_a_visual_type_is_not_approved():
    reply = {
        "pages": [
            {
                "title": "Overview",
                "visuals": [{"type": "3d_scatter_globe", "purpose": "x", "field_bindings": ["f"]}],
            }
        ]
    }

    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape(reply)


def test_validate_solution_shape_raises_when_a_visual_has_no_purpose():
    reply = {
        "pages": [{"title": "Overview", "visuals": [{"type": "bar_chart", "field_bindings": ["f"]}]}]
    }

    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape(reply)


def test_validate_solution_shape_raises_when_field_bindings_is_missing():
    reply = {"pages": [{"title": "Overview", "visuals": [{"type": "bar_chart", "purpose": "x"}]}]}

    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape(reply)


def test_validate_solution_shape_raises_when_field_bindings_contains_an_empty_string():
    reply = {
        "pages": [
            {
                "title": "Overview",
                "visuals": [{"type": "bar_chart", "purpose": "x", "field_bindings": [""]}],
            }
        ]
    }

    with pytest.raises(InvalidDraftSolutionResponseError):
        validate_solution_shape(reply)


def test_validate_solution_shape_allows_a_page_with_zero_visuals():
    reply = {"pages": [{"title": "Overview", "visuals": []}]}

    result = validate_solution_shape(reply)

    assert result["pages"][0]["visuals"] == []


def test_find_mockup_alignment_violations_returns_empty_list_for_an_aligned_solution():
    solution = validate_solution_shape(_VALID_SOLUTION_REPLY)

    violations = find_mockup_alignment_violations(solution, _MOCKUP)

    assert violations == []


def test_find_mockup_alignment_violations_ignores_purpose_and_field_binding_differences():
    reply = {
        "pages": [
            {
                "title": "Regional Sales Overview",
                "visuals": [
                    {
                        "type": "bar_chart",
                        "purpose": "A more detailed restatement of the same purpose",
                        "field_bindings": ["Sales[Region]"],
                    },
                    {"type": "kpi_card", "purpose": "Total revenue", "field_bindings": ["Total Revenue"]},
                ],
            }
        ]
    }
    solution = validate_solution_shape(reply)

    violations = find_mockup_alignment_violations(solution, _MOCKUP)

    assert violations == []


def test_find_mockup_alignment_violations_flags_a_different_page_count():
    reply = {
        "pages": [
            {
                "title": "Regional Sales Overview",
                "visuals": [
                    {"type": "bar_chart", "purpose": "x", "field_bindings": ["f"]},
                    {"type": "kpi_card", "purpose": "x", "field_bindings": ["f"]},
                ],
            },
            {
                "title": "Extra Page",
                "visuals": [{"type": "table", "purpose": "x", "field_bindings": ["f"]}],
            },
        ]
    }
    solution = validate_solution_shape(reply)

    violations = find_mockup_alignment_violations(solution, _MOCKUP)

    assert any("1 page(s)" not in v and "page(s)" in v for v in violations)


def test_find_mockup_alignment_violations_flags_a_page_title_mismatch():
    reply = {
        "pages": [
            {
                "title": "Renamed Page",
                "visuals": [
                    {"type": "bar_chart", "purpose": "x", "field_bindings": ["f"]},
                    {"type": "kpi_card", "purpose": "x", "field_bindings": ["f"]},
                ],
            }
        ]
    }
    solution = validate_solution_shape(reply)

    violations = find_mockup_alignment_violations(solution, _MOCKUP)

    assert len(violations) == 1
    assert "Renamed Page" in violations[0]
    assert "Regional Sales Overview" in violations[0]


def test_find_mockup_alignment_violations_flags_a_different_visual_count():
    reply = {
        "pages": [
            {
                "title": "Regional Sales Overview",
                "visuals": [{"type": "bar_chart", "purpose": "x", "field_bindings": ["f"]}],
            }
        ]
    }
    solution = validate_solution_shape(reply)

    violations = find_mockup_alignment_violations(solution, _MOCKUP)

    assert len(violations) == 1
    assert "1 visual(s)" in violations[0]
    assert "2" in violations[0]


def test_find_mockup_alignment_violations_flags_a_visual_type_mismatch():
    reply = {
        "pages": [
            {
                "title": "Regional Sales Overview",
                "visuals": [
                    {"type": "line_chart", "purpose": "x", "field_bindings": ["f"]},
                    {"type": "kpi_card", "purpose": "x", "field_bindings": ["f"]},
                ],
            }
        ]
    }
    solution = validate_solution_shape(reply)

    violations = find_mockup_alignment_violations(solution, _MOCKUP)

    assert len(violations) == 1
    assert "line_chart" in violations[0]
    assert "bar_chart" in violations[0]


def test_draft_mockup_mismatch_error_carries_the_violations_list():
    error = DraftMockupMismatchError(["page 'x' visual 0: type mismatch"])

    assert error.violations == ["page 'x' visual 0: type mismatch"]
