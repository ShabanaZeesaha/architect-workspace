import pytest

from src.requirement_clarification import (
    RequirementClarificationError,
    find_missing_fields,
    generate_followup_questions,
)

_COMPLETE_ANALYSIS = {
    "business_objectives": ["Increase visibility into quarterly regional sales"],
    "scope": ["Q1 2026 regional sales"],
    "kpis": ["Total Revenue"],
    "filters": ["Region"],
    "calculations": ["Net Margin = Revenue - Cost"],
    "visual_requirements": ["Bar chart comparing revenue by region"],
    "reporting_expectations": ["Weekly summary email"],
}


def test_find_missing_fields_returns_empty_list_for_a_complete_analysis():
    missing = find_missing_fields(_COMPLETE_ANALYSIS)

    assert missing == []


def test_find_missing_fields_returns_the_names_of_empty_fields():
    analysis = dict(_COMPLETE_ANALYSIS, kpis=[], filters=[])

    missing = find_missing_fields(analysis)

    assert missing == ["kpis", "filters"]


def test_find_missing_fields_raises_for_non_dict_input():
    with pytest.raises(RequirementClarificationError):
        find_missing_fields("not a dict")


def test_find_missing_fields_raises_when_a_required_field_is_absent():
    analysis = {k: v for k, v in _COMPLETE_ANALYSIS.items() if k != "scope"}

    with pytest.raises(RequirementClarificationError):
        find_missing_fields(analysis)


def test_find_missing_fields_raises_when_a_field_is_not_a_list():
    analysis = dict(_COMPLETE_ANALYSIS, kpis="Total Revenue")

    with pytest.raises(RequirementClarificationError):
        find_missing_fields(analysis)


def test_generate_followup_questions_returns_empty_list_for_a_complete_requirement():
    questions = generate_followup_questions(_COMPLETE_ANALYSIS)

    assert questions == []


def test_generate_followup_questions_returns_one_question_per_missing_field():
    analysis = dict(_COMPLETE_ANALYSIS, business_objectives=[], visual_requirements=[])

    questions = generate_followup_questions(analysis)

    assert len(questions) == 2
    assert any("business objective" in q for q in questions)
    assert any("visual" in q or "chart" in q for q in questions)


def test_generate_followup_questions_are_non_empty_strings():
    analysis = dict(_COMPLETE_ANALYSIS, scope=[])

    questions = generate_followup_questions(analysis)

    assert len(questions) == 1
    assert all(isinstance(q, str) and q.strip() for q in questions)
