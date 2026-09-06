import pytest

from src.dashboard_publication import DashboardPublication, PublicationError
from src.data_validation import DataValidation
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


class _FakePublisher:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def publish(self, draft_solution):
        self.calls.append(draft_solution)
        if self.error is not None:
            raise self.error
        return self.result


def _to_validated(tmp_path, analyst_id="analyst-1"):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    validation = DataValidation(db_path)

    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id=analyst_id)
    intake.complete_analysis(request_id=created["request_id"], analyst_id=analyst_id, analysis=_ANALYSIS)
    review.submit_draft_for_review(request_id=created["request_id"], analyst_id=analyst_id, draft_solution=_ACCURATE_DRAFT)
    review.approve(request_id=created["request_id"], analyst_id="reviewer-1")
    validation.validate(request_id=created["request_id"], analyst_id="data-specialist-1")

    return db_path, created["request_id"], intake


def test_publish_succeeds_and_moves_to_published(tmp_path):
    db_path, request_id, intake = _to_validated(tmp_path)
    publication = DashboardPublication(db_path)
    publisher = _FakePublisher(result={"dashboard_url": "https://app.powerbi.com/dashboards/abc123"})

    updated = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=publisher)

    assert updated["status"] == "published"
    audit_log = intake.get_audit_log(request_id)
    entry = audit_log[-1]
    assert entry.event == "dashboard_published"
    assert entry.analyst_id == "designer-1"
    assert entry.error_category == "https://app.powerbi.com/dashboards/abc123"


def test_publish_failure_moves_to_publication_failed_and_logs_error(tmp_path):
    db_path, request_id, intake = _to_validated(tmp_path)
    publication = DashboardPublication(db_path)
    publisher = _FakePublisher(error=RuntimeError("Power BI service unreachable"))

    updated = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=publisher)

    assert updated["status"] == "publication_failed"
    audit_log = intake.get_audit_log(request_id)
    entry = audit_log[-1]
    assert entry.event == "dashboard_publication_failed"
    assert "Power BI service unreachable" in entry.error_category


def test_publish_with_no_dashboard_url_is_treated_as_a_failure(tmp_path):
    db_path, request_id, intake = _to_validated(tmp_path)
    publication = DashboardPublication(db_path)
    publisher = _FakePublisher(result={})

    updated = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=publisher)

    assert updated["status"] == "publication_failed"
    audit_log = intake.get_audit_log(request_id)
    entry = audit_log[-1]
    assert entry.event == "dashboard_publication_failed"
    assert "not available" in entry.error_category


def test_publish_can_be_retried_after_a_failure_and_succeeds(tmp_path):
    db_path, request_id, intake = _to_validated(tmp_path)
    publication = DashboardPublication(db_path)
    failing_publisher = _FakePublisher(error=RuntimeError("timed out"))

    first_attempt = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=failing_publisher)
    assert first_attempt["status"] == "publication_failed"

    working_publisher = _FakePublisher(result={"dashboard_url": "https://app.powerbi.com/dashboards/abc123"})
    second_attempt = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=working_publisher)

    assert second_attempt["status"] == "published"
    audit_log = intake.get_audit_log(request_id)
    assert [entry.event for entry in audit_log[-2:]] == [
        "dashboard_publication_failed",
        "dashboard_published",
    ]


def test_publish_retried_twice_after_repeated_failure_logs_each_attempt(tmp_path):
    db_path, request_id, intake = _to_validated(tmp_path)
    publication = DashboardPublication(db_path)
    failing_publisher = _FakePublisher(error=RuntimeError("timed out"))

    publication.publish(request_id=request_id, analyst_id="designer-1", publisher=failing_publisher)
    second_attempt = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=failing_publisher)

    assert second_attempt["status"] == "publication_failed"
    audit_log = intake.get_audit_log(request_id)
    assert [entry.event for entry in audit_log[-2:]] == [
        "dashboard_publication_failed",
        "dashboard_publication_failed",
    ]


def test_publish_rejects_a_draft_that_has_not_been_validated(tmp_path):
    db_path = str(tmp_path / "requests.db")
    intake = RequestIntake(db_path)
    review = StakeholderReview(db_path)
    publication = DashboardPublication(db_path)
    created = intake.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    intake.complete_analysis(request_id=created["request_id"], analyst_id="analyst-1", analysis=_ANALYSIS)
    review.submit_draft_for_review(request_id=created["request_id"], analyst_id="analyst-1", draft_solution=_ACCURATE_DRAFT)
    review.approve(request_id=created["request_id"], analyst_id="reviewer-1")

    with pytest.raises(InvalidTransitionError):
        publication.publish(request_id=created["request_id"], analyst_id="designer-1", publisher=_FakePublisher())


def test_publish_with_no_publisher_configured_is_treated_as_a_failure(tmp_path):
    db_path, request_id, intake = _to_validated(tmp_path)
    publication = DashboardPublication(db_path)

    updated = publication.publish(request_id=request_id, analyst_id="designer-1", publisher=None)

    assert updated["status"] == "publication_failed"
    audit_log = intake.get_audit_log(request_id)
    assert audit_log[-1].error_category == "publication client is not configured"


def test_publish_raises_on_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    publication = DashboardPublication(db_path)

    with pytest.raises(KeyError):
        publication.publish(request_id="does-not-exist", analyst_id="designer-1", publisher=_FakePublisher())


def test_get_request_returns_none_for_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    publication = DashboardPublication(db_path)

    assert publication.get_request("does-not-exist") is None
