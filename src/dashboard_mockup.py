"""
dashboard_mockup.py

Generates a dashboard mockup (REQ-006) from an already-generated design
recommendation (see src/design_recommendation.py).

Missing-input detection happens first and is deterministic, not AI-driven:
a design recommendation with no report_pages or visual_design guidance
can't be turned into a mockup, so the model is never called on it. Once
the model replies, src/dashboard_mockup_template.py checks the reply is
well-formed and then separately checks it against this system's approved
dashboard template -- see that module for why those are two distinct
checks.
"""

import json
import os
import re

import anthropic

from src.dashboard_mockup_template import (
    APPROVED_VISUAL_TYPES,
    InvalidDashboardMockupResponseError,
    MockupTemplateMismatchError,
    find_template_violations,
    validate_mockup_shape,
)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
REQUEST_TIMEOUT_SECONDS = 30.0

_MOCKUP_INPUT_FIELDS = ("report_pages", "visual_design")

_PROMPT_TEMPLATE = """You are a Power BI report designer. A design recommendation has already
been generated and approved for a stakeholder's reporting requirement. Turn it into a
dashboard mockup -- do not invent pages or visuals the recommendation doesn't support.

Rules:
- Base every page and visual on the design recommendation below.
- Each visual's "type" MUST be exactly one of these approved types: {{approved_types}}
- Every page must have at least one visual.

Design recommendation:
{{recommendation}}

Return your answer as a single JSON object with exactly this shape and no other fields:
{"pages": [{"title": "<page title>", "visuals": [{"type": "<one of the approved types>", "purpose": "<what this visual shows, one sentence>"}]}]}

Reply with only the JSON object -- no text before or after it.
"""


class DashboardMockupError(Exception):
    """Raised when the model cannot be reached or fails to respond."""


class InvalidRecommendationInputError(Exception):
    """Raised when the input isn't a valid design-recommendation dict."""


class IncompleteRecommendationError(Exception):
    """Raised when the design recommendation has no page/visual guidance to build a
    mockup from -- generate_design_recommendations() must be resolved first."""

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__(f"design recommendation is missing required fields: {missing_fields}")


def find_missing_mockup_input_fields(recommendation: dict) -> list[str]:
    """Returns the names of design-recommendation fields needed to build a mockup
    (report_pages, visual_design) that are empty."""
    if not isinstance(recommendation, dict):
        raise InvalidRecommendationInputError("recommendation must be a dict")

    missing = []
    for field in _MOCKUP_INPUT_FIELDS:
        value = recommendation.get(field)
        if not isinstance(value, list):
            raise InvalidRecommendationInputError(f"field '{field}' was missing or not a list")
        if len(value) == 0:
            missing.append(field)
    return missing


def generate_dashboard_mockup(recommendation: dict, client: anthropic.Anthropic | None = None) -> dict:
    """Generates a dashboard mockup from an already-generated design recommendation.

    Raises IncompleteRecommendationError before ever calling the model if the
    recommendation has no report_pages or visual_design guidance.
    Raises InvalidDashboardMockupResponseError if the reply isn't well-formed.
    Raises MockupTemplateMismatchError if a well-formed reply violates the
    approved template (see dashboard_mockup_template.APPROVED_VISUAL_TYPES).
    """
    missing = find_missing_mockup_input_fields(recommendation)
    if missing:
        raise IncompleteRecommendationError(missing)

    if client is None:
        client = _build_client()

    filled_prompt = _PROMPT_TEMPLATE.replace(
        "{{approved_types}}", ", ".join(sorted(APPROVED_VISUAL_TYPES))
    ).replace("{{recommendation}}", json.dumps(recommendation))

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": filled_prompt}],
        )
    except anthropic.APIError as exc:
        raise DashboardMockupError("dashboard mockup request failed") from exc

    reply_text = _extract_text(response)
    if reply_text is None:
        raise InvalidDashboardMockupResponseError("model returned no text content")

    parsed = _extract_json(reply_text)
    if parsed is None:
        raise InvalidDashboardMockupResponseError("model response was not valid JSON")

    mockup = validate_mockup_shape(parsed)

    violations = find_template_violations(mockup)
    if violations:
        raise MockupTemplateMismatchError(violations)

    return mockup


def _build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise DashboardMockupError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=api_key)


def _extract_text(response) -> str | None:
    for block in getattr(response, "content", []):
        if getattr(block, "type", None) == "text":
            return block.text
    return None


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    return None
