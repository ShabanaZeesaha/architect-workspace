import json
import os
import re

import anthropic

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
REQUEST_TIMEOUT_SECONDS = 30.0

REQUIRED_FIELDS = (
    "business_objectives",
    "scope",
    "kpis",
    "filters",
    "calculations",
    "visual_requirements",
    "reporting_expectations",
)

# Reuses this repo's existing prompt convention (see
# docs/Assignment_1/prompts/triage-report-request/v1.0.0.md): a {{message}}
# placeholder, an explicit "don't invent facts" rule, and a "JSON only" reply
# instruction, adapted to the capture-request field set.
_PROMPT_TEMPLATE = """You are a business analyst intake assistant. A stakeholder has sent a
request message describing a reporting or dashboard need. Read it and
extract only what the message actually states.

Rules:
- Do not invent objectives, scope, KPIs, filters, calculations, visuals, or
  reporting expectations the message doesn't state.
- If a field isn't mentioned in the message, return it as an empty list.
- Keep each list item short and drawn directly from the message.

Stakeholder message:
{{message}}

Return your answer as a single JSON object with exactly these fields and no
others, each an array of strings:
- business_objectives
- scope
- kpis
- filters
- calculations
- visual_requirements
- reporting_expectations

Reply with only the JSON object -- no text before or after it.
"""


class EmailAnalysisError(Exception):
    """Raised when the model cannot be reached or fails to respond."""


class InvalidEmailAnalysisResponseError(EmailAnalysisError):
    """Raised when the model responds but the reply isn't a valid, complete analysis."""


def analyze_email(text: str, client: anthropic.Anthropic | None = None) -> dict:
    """Analyze email request text into business_objectives, scope, kpis,
    filters, calculations, visual_requirements, and reporting_expectations
    using the configured Claude Haiku model.
    """
    if client is None:
        client = _build_client()

    filled_prompt = _PROMPT_TEMPLATE.replace("{{message}}", text)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            messages=[{"role": "user", "content": filled_prompt}],
        )
    except anthropic.APIError as exc:
        raise EmailAnalysisError("email analysis request failed") from exc

    reply_text = _extract_text(response)
    if reply_text is None:
        raise InvalidEmailAnalysisResponseError("model returned no text content")

    parsed = _extract_json(reply_text)
    if parsed is None:
        raise InvalidEmailAnalysisResponseError("model response was not valid JSON")

    return _validate(parsed)


def _build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EmailAnalysisError("ANTHROPIC_API_KEY is not configured")
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
        raise InvalidEmailAnalysisResponseError("model response was not a JSON object")

    result = {}
    for field in REQUIRED_FIELDS:
        value = parsed.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InvalidEmailAnalysisResponseError(f"field '{field}' was missing or not a list of strings")
        result[field] = value
    return result
