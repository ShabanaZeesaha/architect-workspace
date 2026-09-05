"""
powerbi_solution.py

Generates a draft Power BI solution (REQ-007) from an already-generated,
template-checked dashboard mockup (see src/dashboard_mockup.py -- STORY-006).

The input mockup's own shape is re-validated here (reusing
dashboard_mockup_template.validate_mockup_shape() rather than rebuilding
that check) before the model is ever called, since this module receives
the mockup directly from the caller, not from a trusted internal source.
Once the model replies, src/powerbi_solution_template.py checks the reply
is well-formed and then separately checks it aligns with the source
mockup -- see that module for why those are two distinct checks.
"""

import json
import os
import re

import anthropic

from src.dashboard_mockup_template import (
    APPROVED_VISUAL_TYPES,
    InvalidDashboardMockupResponseError,
    validate_mockup_shape,
)
from src.powerbi_solution_template import (
    DraftMockupMismatchError,
    InvalidDraftSolutionResponseError,
    find_mockup_alignment_violations,
    validate_solution_shape,
)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
REQUEST_TIMEOUT_SECONDS = 30.0

_PROMPT_TEMPLATE = """You are a Power BI report designer. A dashboard mockup has already been
generated and reviewed for a stakeholder's reporting requirement. Turn it into a draft Power BI
solution by adding, for every visual, the specific data fields or DAX measures it would bind to.

Rules:
- Keep exactly the same pages, in the same order, with exactly the same titles as the mockup below.
- Keep exactly the same visuals per page, in the same order, with exactly the same "type" as the
  mockup below. Do not add, remove, or reorder pages or visuals.
- Every visual's "type" MUST remain exactly one of these approved types: {{approved_types}}
- For every visual, add a "field_bindings" list naming the specific fields or DAX measures that
  visual would be bound to, based on its purpose. Never leave "field_bindings" empty.

Dashboard mockup:
{{mockup}}

Return your answer as a single JSON object with exactly this shape and no other fields:
{"pages": [{"title": "<page title, unchanged from the mockup>", "visuals": [{"type": "<unchanged from the mockup>", "purpose": "<unchanged from the mockup>", "field_bindings": ["<field or measure name>"]}]}]}

Reply with only the JSON object -- no text before or after it.
"""


class PowerBiSolutionError(Exception):
    """Raised when the model cannot be reached or fails to respond."""


class InvalidMockupInputError(Exception):
    """Raised when the input isn't a valid dashboard-mockup dict."""


def generate_draft_powerbi_solution(mockup: dict, client: anthropic.Anthropic | None = None) -> dict:
    """Generates a draft Power BI solution from an already-generated dashboard mockup.

    Raises InvalidMockupInputError before ever calling the model if the mockup itself
    isn't well-formed.
    Raises InvalidDraftSolutionResponseError if the reply isn't well-formed.
    Raises DraftMockupMismatchError if a well-formed reply doesn't align with the
    source mockup (different pages, order, or visual types).
    """
    try:
        validated_mockup = validate_mockup_shape(mockup)
    except InvalidDashboardMockupResponseError as exc:
        raise InvalidMockupInputError(str(exc)) from exc

    if client is None:
        client = _build_client()

    filled_prompt = _PROMPT_TEMPLATE.replace(
        "{{approved_types}}", ", ".join(sorted(APPROVED_VISUAL_TYPES))
    ).replace("{{mockup}}", json.dumps(validated_mockup))

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": filled_prompt}],
        )
    except anthropic.APIError as exc:
        raise PowerBiSolutionError("draft Power BI solution request failed") from exc

    reply_text = _extract_text(response)
    if reply_text is None:
        raise InvalidDraftSolutionResponseError("model returned no text content")

    parsed = _extract_json(reply_text)
    if parsed is None:
        raise InvalidDraftSolutionResponseError("model response was not valid JSON")

    solution = validate_solution_shape(parsed)

    violations = find_mockup_alignment_violations(solution, validated_mockup)
    if violations:
        raise DraftMockupMismatchError(violations)

    return solution


def _build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise PowerBiSolutionError("ANTHROPIC_API_KEY is not configured")
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
