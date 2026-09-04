"""
design_recommendation.py

Generates AI-assisted design recommendations (REQ-005: data model,
relationships, transformations, validation checks, KPI definitions, DAX
measures, report pages, slicers, visual design) from an already-analyzed
request's approved requirements (see src/email_analysis.py,
src/excel_analysis.py) and, optionally, its approved field mapping (see
src/field_mapping.py).

Missing-field detection happens first and is deterministic, not AI-driven --
reuses requirement_clarification.find_missing_fields() so an incomplete
requirement is flagged before spending a model call on it, and so AI is
never asked to recommend a design for data it doesn't have.
"""

import json
import os
import re

import anthropic

from src.requirement_clarification import find_missing_fields

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1536
REQUEST_TIMEOUT_SECONDS = 30.0

RECOMMENDATION_FIELDS = (
    "data_model",
    "relationships",
    "transformations",
    "validation_checks",
    "kpi_definitions",
    "dax_measures",
    "report_pages",
    "slicers",
    "visual_design",
)

_PROMPT_TEMPLATE = """You are a Power BI solution architect. A stakeholder's reporting
requirement has already been captured and approved, and its source fields
have already been mapped onto this system's approved schema columns. Read
both and recommend a design -- do not invent requirements the input doesn't
support.

Rules:
- Base every recommendation on the approved requirements and field mapping
  below. Do not invent KPIs, fields, or objectives they don't state.
- Keep each list item short (a single sentence or shorter).

Approved requirements:
{{requirements}}

Approved field mapping (source column -> schema field):
{{field_mapping}}

Return your answer as a single JSON object with exactly these fields and no
others, each an array of strings:
- data_model (tables/entities needed)
- relationships (how those tables relate)
- transformations (data prep/shaping steps)
- validation_checks (data quality checks to run before publishing)
- kpi_definitions (each KPI's calculation, in plain English)
- dax_measures (candidate DAX measure names and what they compute)
- report_pages (report pages/tabs to build)
- slicers (filter/slicer controls to include)
- visual_design (chart types and layout guidance)

Reply with only the JSON object -- no text before or after it.
"""


class DesignRecommendationError(Exception):
    """Raised when the model cannot be reached or fails to respond."""


class InvalidDesignRecommendationResponseError(DesignRecommendationError):
    """Raised when the model responds but the reply isn't a valid, complete recommendation set."""


class IncompleteRequirementsError(Exception):
    """Raised when the analyzed request is missing required fields -- design
    recommendations need requirement_clarification.py resolved first."""

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__(f"analysis is missing required fields: {missing_fields}")


def generate_design_recommendations(
    analysis: dict, field_mapping: dict | None = None, client: anthropic.Anthropic | None = None
) -> dict:
    """Generates design recommendations from an already-analyzed request's
    approved requirements and (optional) approved field mapping.

    Raises IncompleteRequirementsError before ever calling the model if the
    requirement has missing fields (see find_missing_fields()).
    """
    missing = find_missing_fields(analysis)
    if missing:
        raise IncompleteRequirementsError(missing)

    if client is None:
        client = _build_client()

    filled_prompt = _PROMPT_TEMPLATE.replace("{{requirements}}", json.dumps(analysis)).replace(
        "{{field_mapping}}", json.dumps(field_mapping or {})
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": filled_prompt}],
        )
    except anthropic.APIError as exc:
        raise DesignRecommendationError("design recommendation request failed") from exc

    reply_text = _extract_text(response)
    if reply_text is None:
        raise InvalidDesignRecommendationResponseError("model returned no text content")

    parsed = _extract_json(reply_text)
    if parsed is None:
        raise InvalidDesignRecommendationResponseError("model response was not valid JSON")

    return _validate(parsed)


def _build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise DesignRecommendationError("ANTHROPIC_API_KEY is not configured")
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


def _validate(parsed: dict) -> dict:
    if not isinstance(parsed, dict):
        raise InvalidDesignRecommendationResponseError("model response was not a JSON object")

    result = {}
    for field in RECOMMENDATION_FIELDS:
        value = parsed.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InvalidDesignRecommendationResponseError(
                f"field '{field}' was missing or not a list of strings"
            )
        result[field] = value
    return result
