import sqlite3

import pytest

from src.data_validation import DataValidation, MissingValidationDataError
from src.lifecycle import InvalidTransitionError
from src.request_intake import RequestIntake
from src.stakeholder_review import StakeholderReview

_ANALYSIS = {
    "business_objectives": ["Increase quarterly revenue"],
    "scope": ["North America region"],
    "kpis": ["Monthly Revenue Growth"],
    "filters": ["Region", "Product Category"],
    "calculations": ["Year over year growth rate"],
    "visual_requirements": ["Bar chart of sales by region"],
    "reporting_expectations": ["Weekly refresh"],
}

_ACCURATE_DRAFT = {
    "pages": [
        {
            "title": "Sales Overview",
            "visuals": [{"type": "bar_chart", "purpose": "Show sales by region", "field_bindings": ["Region"]}],
        }
    ]
}

_INACCURATE_DRAFT = {
    "pages": [
        {
            "title": "Sales Overview",
            "visuals": [{"type": "kpi_card", "purpose": "Show customer value", "field_bindings": ["Customer Lifetime Value"]}],
        }
    ]
}


def _to_approved(intake, review, draft_solution, analyst_id="analyst-1"):
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id=analyst_id)
    intake.complete_analysis(request_id=created["request_id"], analyst_id=analyst_id, analysis=_ANALYSIS)
    review.submit_draft_for_review(request_id=created["request_id"], analyst_id=analyst_id, draft_solution=draft_solution)
    review.approve(request_id=created["request_id"], analyst_id="reviewer-1")
    return created["request_id"]


def test_validate_confirms_data_accuracy_and_moves_to_validated(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)
    request_id = _to_approved(intake, review, _ACCURATE_DRAFT)

    updated, violations = validation.validate(request_id=request_id, analyst_id="data-specialist-1")

    assert violations == []
    assert updated["status"] == "validated"


def test_validate_success_writes_audit_entry(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)
    request_id = _to_approved(intake, review, _ACCURATE_DRAFT)

    validation.validate(request_id=request_id, analyst_id="data-specialist-1")

    audit_log = intake.get_audit_log(request_id)
    entry = audit_log[-1]
    assert entry.event == "data_validation_passed"
    assert entry.analyst_id == "data-specialist-1"
    assert entry.timestamp


def test_validate_flags_inaccurate_data_and_moves_to_changes_requested(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)
    request_id = _to_approved(intake, review, _INACCURATE_DRAFT)

    updated, violations = validation.validate(request_id=request_id, analyst_id="data-specialist-1")

    assert len(violations) == 1
    assert updated["status"] == "changes_requested"


def test_validate_failure_logs_violations_in_audit_entry(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)
    request_id = _to_approved(intake, review, _INACCURATE_DRAFT)

    _, violations = validation.validate(request_id=request_id, analyst_id="data-specialist-1")

    audit_log = intake.get_audit_log(request_id)
    entry = audit_log[-1]
    assert entry.event == "data_validation_failed"
    assert entry.error_category == "; ".join(violations)


def test_validate_raises_on_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    validation = DataValidation(db_path)

    with pytest.raises(KeyError):
        validation.validate(request_id="does-not-exist", analyst_id="data-specialist-1")


def test_validate_rejects_a_draft_that_has_not_been_approved(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    intake.complete_analysis(request_id=created["request_id"], analyst_id="analyst-1", analysis=_ANALYSIS)
    review.submit_draft_for_review(request_id=created["request_id"], analyst_id="analyst-1", draft_solution=_ACCURATE_DRAFT)

    with pytest.raises(InvalidTransitionError):
        validation.validate(request_id=created["request_id"], analyst_id="data-specialist-1")


def test_validate_raises_missing_validation_data_error_when_draft_solution_is_absent(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)
    request_id = _to_approved(intake, review, _ACCURATE_DRAFT)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE requests SET draft_solution = NULL WHERE request_id = ?", (request_id,))
    conn.commit()
    conn.close()

    with pytest.raises(MissingValidationDataError):
        validation.validate(request_id=request_id, analyst_id="data-specialist-1")


def test_get_request_returns_none_for_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    validation = DataValidation(db_path)

    assert validation.get_request("does-not-exist") is None
