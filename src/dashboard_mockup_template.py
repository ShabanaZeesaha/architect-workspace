"""
dashboard_mockup_template.py

Defines this system's approved dashboard template (REQ-006) -- the fixed,
deterministic structural contract a generated mockup must satisfy -- and
checks a model-generated mockup against it, in two separate steps:
validate_mockup_shape() confirms the reply is well-formed at all (right
JSON shape, non-empty strings); find_template_violations() then checks an
already-well-formed mockup against the approved template rules (every
page has at least one visual, every visual's type is on the approved
list). A well-formed reply that fails the second check is a template
mismatch, not an invalid response -- dashboard_mockup.py reports these as
two distinct outcomes with two distinct audit events.
"""

APPROVED_VISUAL_TYPES = frozenset(
    {
        "bar_chart",
        "line_chart",
        "pie_chart",
        "kpi_card",
        "table",
        "matrix",
        "slicer",
        "map",
        "gauge",
    }
)


class InvalidDashboardMockupResponseError(Exception):
    """Raised when a model reply isn't a well-formed mockup (wrong shape/types)."""


class MockupTemplateMismatchError(Exception):
    """Raised when a well-formed mockup violates the approved template (an
    unapproved visual type, or a page with no visuals)."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"mockup does not match approved template: {violations}")


def validate_mockup_shape(parsed: dict) -> dict:
    """Confirms a parsed model reply is a well-formed mockup: a non-empty list of
    pages, each with a non-empty title and a list of visuals, each visual with a
    non-empty type and purpose. Does not check template compliance -- see
    find_template_violations().
    """
    if not isinstance(parsed, dict):
        raise InvalidDashboardMockupResponseError("model response was not a JSON object")

    pages = parsed.get("pages")
    if not isinstance(pages, list) or len(pages) == 0:
        raise InvalidDashboardMockupResponseError("field 'pages' was missing or not a non-empty list")

    validated_pages = []
    for page in pages:
        if not isinstance(page, dict):
            raise InvalidDashboardMockupResponseError("each page must be a JSON object")

        title = page.get("title")
        if not isinstance(title, str) or not title:
            raise InvalidDashboardMockupResponseError("each page must have a non-empty 'title'")

        visuals = page.get("visuals")
        if not isinstance(visuals, list):
            raise InvalidDashboardMockupResponseError("each page must have a 'visuals' list")

        validated_visuals = []
        for visual in visuals:
            if not isinstance(visual, dict):
                raise InvalidDashboardMockupResponseError("each visual must be a JSON object")

            visual_type = visual.get("type")
            purpose = visual.get("purpose")
            if not isinstance(visual_type, str) or not visual_type:
                raise InvalidDashboardMockupResponseError("each visual must have a non-empty 'type'")
            if not isinstance(purpose, str) or not purpose:
                raise InvalidDashboardMockupResponseError("each visual must have a non-empty 'purpose'")

            validated_visuals.append({"type": visual_type, "purpose": purpose})

        validated_pages.append({"title": title, "visuals": validated_visuals})

    return {"pages": validated_pages}


def find_template_violations(mockup: dict) -> list[str]:
    """Returns the list of approved-template violations in an already
    shape-validated mockup (see validate_mockup_shape()); empty if it fully
    complies.
    """
    violations = []
    for page in mockup["pages"]:
        if len(page["visuals"]) == 0:
            violations.append(f"page '{page['title']}' has no visuals")
        for visual in page["visuals"]:
            if visual["type"] not in APPROVED_VISUAL_TYPES:
                violations.append(
                    f"page '{page['title']}' uses unapproved visual type '{visual['type']}'"
                )
    return violations
