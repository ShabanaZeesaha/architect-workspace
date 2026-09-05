import pytest

from src.dashboard_mockup_template import (
    InvalidDashboardMockupResponseError,
    MockupTemplateMismatchError,
    find_template_violations,
    validate_mockup_shape,
)

_VALID_MOCKUP_REPLY = {
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


def test_validate_mockup_shape_returns_pages_and_visuals_for_a_well_formed_reply():
    result = validate_mockup_shape(_VALID_MOCKUP_REPLY)

    assert result == _VALID_MOCKUP_REPLY


def test_validate_mockup_shape_raises_when_pages_is_missing():
    with pytest.raises(InvalidDashboardMockupResponseError):
        validate_mockup_shape({})


def test_validate_mockup_shape_raises_when_pages_is_empty():
    with pytest.raises(InvalidDashboardMockupResponseError):
        validate_mockup_shape({"pages": []})


def test_validate_mockup_shape_raises_when_a_page_has_no_title():
    reply = {"pages": [{"visuals": [{"type": "bar_chart", "purpose": "x"}]}]}

    with pytest.raises(InvalidDashboardMockupResponseError):
        validate_mockup_shape(reply)


def test_validate_mockup_shape_raises_when_a_visual_has_no_type():
    reply = {"pages": [{"title": "Overview", "visuals": [{"purpose": "x"}]}]}

    with pytest.raises(InvalidDashboardMockupResponseError):
        validate_mockup_shape(reply)


def test_validate_mockup_shape_raises_when_a_visual_has_no_purpose():
    reply = {"pages": [{"title": "Overview", "visuals": [{"type": "bar_chart"}]}]}

    with pytest.raises(InvalidDashboardMockupResponseError):
        validate_mockup_shape(reply)


def test_validate_mockup_shape_allows_a_page_with_zero_visuals():
    reply = {"pages": [{"title": "Overview", "visuals": []}]}

    result = validate_mockup_shape(reply)

    assert result["pages"][0]["visuals"] == []


def test_find_template_violations_returns_empty_list_for_a_compliant_mockup():
    mockup = validate_mockup_shape(_VALID_MOCKUP_REPLY)

    violations = find_template_violations(mockup)

    assert violations == []


def test_find_template_violations_flags_an_unapproved_visual_type():
    mockup = {
        "pages": [
            {
                "title": "Overview",
                "visuals": [{"type": "3d_scatter_globe", "purpose": "x"}],
            }
        ]
    }

    violations = find_template_violations(mockup)

    assert len(violations) == 1
    assert "3d_scatter_globe" in violations[0]


def test_find_template_violations_flags_a_page_with_no_visuals():
    mockup = {"pages": [{"title": "Empty Page", "visuals": []}]}

    violations = find_template_violations(mockup)

    assert len(violations) == 1
    assert "Empty Page" in violations[0]


def test_mockup_template_mismatch_error_carries_the_violations_list():
    error = MockupTemplateMismatchError(["page 'x' has no visuals"])

    assert error.violations == ["page 'x' has no visuals"]
