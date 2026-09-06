import pytest

from src.lifecycle import InvalidTransitionError
from src.request_intake import RequestIntake
from src.stakeholder_review import StakeholderReview

_DRAFT_SOLUTION = {"pages": [{"title": "Sales Overview", "visuals": ["bar_chart"]}]}


def test_submit_draft_for_review_stores_draft_and_moves_to_in_review(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    intake.update_status(request_id=created["request_id"], analyst_id="analyst-1", new_status="analyzed")
    review = StakeholderReview(db_path)

    updated = review.submit_draft_for_review(
        request_id=created["request_id"], analyst_id="analyst-1", draft_solution=_DRAFT_SOLUTION
    )

    assert updated["status"] == "in_review"
    assert updated["draft_solution"] == _DRAFT_SOLUTION


def test_submit_draft_for_review_writes_one_audit_entry(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    intake.update_status(request_id=created["request_id"], analyst_id="analyst-1", new_status="analyzed")
    review = StakeholderReview(db_path)

    review.submit_draft_for_review(
        request_id=created["request_id"], analyst_id="analyst-1", draft_solution=_DRAFT_SOLUTION
    )

    audit_log = intake.get_audit_log(created["request_id"])
    assert [entry.event for entry in audit_log] == [
        "request_submitted",
        "status_updated",
        "draft_submitted_for_review",
    ]
    review_entry = audit_log[-1]
    assert review_entry.analyst_id == "analyst-1"
    assert review_entry.timestamp


def test_submit_draft_for_review_allows_resubmission_after_changes_requested(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    intake.update_status(request_id=created["request_id"], analyst_id="analyst-1", new_status="analyzed")
    review = StakeholderReview(db_path)
    review.submit_draft_for_review(
        request_id=created["request_id"], analyst_id="analyst-1", draft_solution=_DRAFT_SOLUTION
    )
    intake.update_status(request_id=created["request_id"], analyst_id="reviewer-1", new_status="changes_requested")

    revised_draft = {"pages": [{"title": "Sales Overview", "visuals": ["bar_chart", "kpi_card"]}]}
    updated = review.submit_draft_for_review(
        request_id=created["request_id"], analyst_id="analyst-1", draft_solution=revised_draft
    )

    assert updated["status"] == "in_review"
    assert updated["draft_solution"] == revised_draft


def test_submit_draft_for_review_rejects_an_illegal_transition(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    review = StakeholderReview(db_path)

    with pytest.raises(InvalidTransitionError):
        review.submit_draft_for_review(
            request_id=created["request_id"], analyst_id="analyst-1", draft_solution=_DRAFT_SOLUTION
        )

    unchanged = intake.get_request(created["request_id"])
    assert unchanged["status"] == "intake"
    assert "draft_solution" not in unchanged


def test_submit_draft_for_review_raises_on_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    review = StakeholderReview(db_path)

    with pytest.raises(KeyError):
        review.submit_draft_for_review(
            request_id="does-not-exist", analyst_id="analyst-1", draft_solution=_DRAFT_SOLUTION
        )


def test_get_request_returns_none_for_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    review = StakeholderReview(db_path)

    assert review.get_request("does-not-exist") is None


def _to_in_review(intake, review, analyst_id="analyst-1"):
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id=analyst_id)
    intake.update_status(request_id=created["request_id"], analyst_id=analyst_id, new_status="analyzed")
    review.submit_draft_for_review(
        request_id=created["request_id"], analyst_id=analyst_id, draft_solution=_DRAFT_SOLUTION
    )
    return created["request_id"]


def test_approve_moves_status_to_approved(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    request_id = _to_in_review(intake, review)

    updated = review.approve(request_id=request_id, analyst_id="reviewer-1")

    assert updated["status"] == "approved"


def test_approve_writes_audit_entry_with_approver_id_and_timestamp(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    request_id = _to_in_review(intake, review)

    review.approve(request_id=request_id, analyst_id="reviewer-1")

    audit_log = intake.get_audit_log(request_id)
    approval_entry = audit_log[-1]
    assert approval_entry.event == "draft_approved"
    assert approval_entry.analyst_id == "reviewer-1"
    assert approval_entry.timestamp


def test_approve_rejects_an_illegal_transition(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    with pytest.raises(InvalidTransitionError):
        review.approve(request_id=created["request_id"], analyst_id="reviewer-1")


def test_approve_raises_on_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    review = StakeholderReview(db_path)

    with pytest.raises(KeyError):
        review.approve(request_id="does-not-exist", analyst_id="reviewer-1")


def test_request_changes_moves_status_to_changes_requested_and_logs_feedback(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    request_id = _to_in_review(intake, review)

    updated = review.request_changes(
        request_id=request_id, analyst_id="reviewer-1", feedback="Please add a regional filter"
    )

    assert updated["status"] == "changes_requested"
    audit_log = intake.get_audit_log(request_id)
    feedback_entry = audit_log[-1]
    assert feedback_entry.event == "changes_requested"
    assert feedback_entry.analyst_id == "reviewer-1"
    assert feedback_entry.error_category == "Please add a regional filter"


def test_request_changes_rejects_empty_feedback(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    request_id = _to_in_review(intake, review)

    with pytest.raises(ValueError):
        review.request_changes(request_id=request_id, analyst_id="reviewer-1", feedback="")


def test_request_changes_rejects_an_illegal_transition(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    with pytest.raises(InvalidTransitionError):
        review.request_changes(request_id=created["request_id"], analyst_id="reviewer-1", feedback="fix it")
