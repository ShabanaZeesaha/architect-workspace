"""
requirement_clarification.py

Detects missing information in an already-analyzed request (see
src/email_analysis.py and src/excel_analysis.py) and generates one
plain-English follow-up question per missing field.

Detection is deterministic, not AI-driven: analyze_email() and
analyze_report() already return each of the seven required fields as a
list that is empty when the source didn't mention it, so "missing" is just
"empty list" -- no model call is needed to answer REQ-004's missing-field
case, and the result is reproducible for the same input every time.
Flagging content that is present but genuinely vague or conflicting is a
follow-up increment, not covered here.
"""

from src.email_analysis import REQUIRED_FIELDS

CLARIFICATION_QUESTIONS_GENERATED = "clarification_questions_generated"
CLARIFICATION_NOT_NEEDED = "clarification_not_needed"

_FOLLOWUP_QUESTIONS = {
    "business_objectives": "What business objective should this report or dashboard support?",
    "scope": "What is the scope of this request (e.g. business unit, time period, data source)?",
    "kpis": "Which KPIs or metrics need to be tracked?",
    "filters": "What filters or breakdowns (e.g. by region, product, date) should the report support?",
    "calculations": "Are there specific calculations or formulas this report should use?",
    "visual_requirements": "What chart types or visuals are expected (e.g. bar chart, trend line)?",
    "reporting_expectations": "How often should this report be refreshed or delivered, and who is the audience?",
}


class RequirementClarificationError(Exception):
    """Raised when the input isn't a valid analysis dict (see REQUIRED_FIELDS)."""


def find_missing_fields(analysis: dict) -> list[str]:
    """Returns the names of required fields that are empty (missing) in an
    analysis dict produced by analyze_email() or analyze_report().
    """
    if not isinstance(analysis, dict):
        raise RequirementClarificationError("analysis must be a dict")

    missing = []
    for field in REQUIRED_FIELDS:
        value = analysis.get(field)
        if not isinstance(value, list):
            raise RequirementClarificationError(f"field '{field}' was missing or not a list")
        if len(value) == 0:
            missing.append(field)
    return missing


def generate_followup_questions(analysis: dict) -> list[str]:
    """Returns one follow-up question per missing field, in REQUIRED_FIELDS
    order; an empty list if the requirement is already complete.
    """
    missing = find_missing_fields(analysis)
    return [_FOLLOWUP_QUESTIONS[field] for field in missing]
