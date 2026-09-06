"""
data_validation_rules.py

Deterministic "data accuracy" check for STORY-009 (REQ-014). Pure function,
no I/O, no model call -- kept separate from src/data_validation.py (which
owns persistence/transitions) the same way powerbi_solution_template.py is
split from powerbi_solution.py.

"Data accuracy confirmed" means: every field_binding a draft Power BI
solution's visuals reference actually traces back to something the
request's own analysis stated. A field_binding that doesn't correspond to
anything in business_objectives, scope, kpis, filters, calculations,
visual_requirements, or reporting_expectations is flagged -- it's either an
invented field the AI pipeline fabricated somewhere upstream, or a typo/
mismatch introduced along the way. Either way it can't be finalized without
a human correcting it.

Matching is case-insensitive substring containment in either direction
(binding-in-known-text or known-text-in-binding), not exact string equality
-- a binding like "Revenue Growth Rate" should match a stated KPI of
"Monthly Revenue Growth", and a short binding like "Revenue" should match
inside a longer analysis phrase. Exact-only matching would flag accurate
bindings just for being phrased slightly differently than the source text.
"""

from src.email_analysis import REQUIRED_FIELDS


def _known_terms(analysis: dict) -> list[str]:
    terms = []
    for field in REQUIRED_FIELDS:
        for value in analysis.get(field) or []:
            if isinstance(value, str) and value.strip():
                terms.append(value.strip().lower())
    return terms


def _binding_is_known(binding: str, known_terms: list[str]) -> bool:
    binding_lower = binding.strip().lower()
    return any(binding_lower in term or term in binding_lower for term in known_terms)


def find_data_accuracy_violations(analysis: dict, draft_solution: dict) -> list[str]:
    """Returns one violation string per field_binding that doesn't trace
    back to the request's analysis. Empty list means data accuracy is
    confirmed. Assumes draft_solution is already shape-valid (STORY-007
    guarantees this before persisting it) -- this checks accuracy, not
    structure.
    """
    known_terms = _known_terms(analysis)

    violations = []
    for page in draft_solution.get("pages", []):
        for visual in page.get("visuals", []):
            for binding in visual.get("field_bindings", []):
                if not _binding_is_known(binding, known_terms):
                    violations.append(
                        f"page '{page.get('title')}' visual '{visual.get('purpose')}': "
                        f"field_binding '{binding}' does not trace back to the analyzed requirements"
                    )
    return violations
