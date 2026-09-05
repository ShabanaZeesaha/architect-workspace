"""
powerbi_solution_template.py

Defines the structural contract for a draft Power BI solution (REQ-007),
generated from an already-generated and template-checked dashboard mockup
(see src/dashboard_mockup.py, src/dashboard_mockup_template.py -- STORY-006).

Two separate checks, same split rationale as dashboard_mockup_template.py:
validate_solution_shape() confirms a model reply is well-formed at all
(right JSON shape, non-empty strings, a visual type on the approved list --
reused from dashboard_mockup_template.py rather than redefined here).
find_mockup_alignment_violations() then checks an already-well-formed
solution against the *specific* mockup it was built from: same page
titles in the same order, same visual types in the same order per page.
A solution is free to add Power BI specifics (field/measure bindings) on
top of the mockup, but must not invent or drop pages/visuals -- mirroring
the "do not invent pages or visuals" rule dashboard_mockup.py's prompt
already enforces one stage up.
"""

from src.dashboard_mockup_template import APPROVED_VISUAL_TYPES


class InvalidDraftSolutionResponseError(Exception):
    """Raised when a model reply isn't a well-formed draft solution (wrong
    shape/types)."""


class DraftMockupMismatchError(Exception):
    """Raised when a well-formed draft solution doesn't align with the
    mockup it was built from (different pages, order, or visual types)."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"draft solution does not align with mockup: {violations}")


def validate_solution_shape(parsed: dict) -> dict:
    """Confirms a parsed model reply is a well-formed draft solution: a
    non-empty list of pages, each with a non-empty title and a list of
    visuals, each visual with an approved type, a non-empty purpose, and a
    list of field_bindings (non-empty strings; the list itself may be
    empty). Does not check alignment with the source mockup -- see
    find_mockup_alignment_violations().
    """
    if not isinstance(parsed, dict):
        raise InvalidDraftSolutionResponseError("model response was not a JSON object")

    pages = parsed.get("pages")
    if not isinstance(pages, list) or len(pages) == 0:
        raise InvalidDraftSolutionResponseError("field 'pages' was missing or not a non-empty list")

    validated_pages = []
    for page in pages:
        if not isinstance(page, dict):
            raise InvalidDraftSolutionResponseError("each page must be a JSON object")

        title = page.get("title")
        if not isinstance(title, str) or not title:
            raise InvalidDraftSolutionResponseError("each page must have a non-empty 'title'")

        visuals = page.get("visuals")
        if not isinstance(visuals, list):
            raise InvalidDraftSolutionResponseError("each page must have a 'visuals' list")

        validated_visuals = []
        for visual in visuals:
            if not isinstance(visual, dict):
                raise InvalidDraftSolutionResponseError("each visual must be a JSON object")

            visual_type = visual.get("type")
            purpose = visual.get("purpose")
            field_bindings = visual.get("field_bindings")
            if not isinstance(visual_type, str) or visual_type not in APPROVED_VISUAL_TYPES:
                raise InvalidDraftSolutionResponseError(
                    f"each visual must have a 'type' from the approved list, got {visual_type!r}"
                )
            if not isinstance(purpose, str) or not purpose:
                raise InvalidDraftSolutionResponseError("each visual must have a non-empty 'purpose'")
            if not isinstance(field_bindings, list) or not all(
                isinstance(binding, str) and binding for binding in field_bindings
            ):
                raise InvalidDraftSolutionResponseError(
                    "each visual must have a 'field_bindings' list of non-empty strings"
                )

            validated_visuals.append(
                {"type": visual_type, "purpose": purpose, "field_bindings": field_bindings}
            )

        validated_pages.append({"title": title, "visuals": validated_visuals})

    return {"pages": validated_pages}


def find_mockup_alignment_violations(solution: dict, mockup: dict) -> list[str]:
    """Returns the list of ways an already shape-validated draft solution
    fails to align with the mockup it was built from -- a different number
    of pages, a page title out of order or missing, or a visual's type not
    matching the mockup at the same position. Empty if the solution's
    structure fully matches.
    """
    violations = []
    solution_pages = solution["pages"]
    mockup_pages = mockup["pages"]

    if len(solution_pages) != len(mockup_pages):
        violations.append(
            f"solution has {len(solution_pages)} page(s), mockup has {len(mockup_pages)}"
        )

    for index, mockup_page in enumerate(mockup_pages):
        if index >= len(solution_pages):
            violations.append(f"solution is missing mockup page '{mockup_page['title']}'")
            continue

        solution_page = solution_pages[index]
        if solution_page["title"] != mockup_page["title"]:
            violations.append(
                f"page {index}: solution title '{solution_page['title']}' does not match "
                f"mockup title '{mockup_page['title']}'"
            )

        solution_visuals = solution_page["visuals"]
        mockup_visuals = mockup_page["visuals"]
        if len(solution_visuals) != len(mockup_visuals):
            violations.append(
                f"page '{mockup_page['title']}': solution has {len(solution_visuals)} visual(s), "
                f"mockup has {len(mockup_visuals)}"
            )

        for visual_index, mockup_visual in enumerate(mockup_visuals):
            if visual_index >= len(solution_visuals):
                continue
            solution_visual = solution_visuals[visual_index]
            if solution_visual["type"] != mockup_visual["type"]:
                violations.append(
                    f"page '{mockup_page['title']}' visual {visual_index}: solution type "
                    f"'{solution_visual['type']}' does not match mockup type '{mockup_visual['type']}'"
                )

    return violations
