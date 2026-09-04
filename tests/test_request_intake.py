import pytest

from src.request_intake import InvalidTransitionError, RequestIntake


def test_submit_request_records_a_valid_request(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))

    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    assert created["request_id"]
    assert created["text"] == "Need a sales dashboard"
    assert created["source_type"] == "email"
    assert created["analyst_id"] == "analyst-1"
    assert created["status"] == "intake"
    assert created["submitted_at"]


def test_submit_request_produces_audit_entry_without_secrets(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))

    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    audit_log = store.get_audit_log(created["request_id"])

    assert len(audit_log) == 1
    entry = audit_log[0]
    assert entry.request_id == created["request_id"]
    assert entry.analyst_id == "analyst-1"
    assert entry.event == "request_submitted"
    assert entry.timestamp == created["submitted_at"]
    assert not hasattr(entry, "text")


def test_request_and_audit_data_persist_across_new_instances(tmp_path):
    db_path = str(tmp_path / "requests.db")
    store = RequestIntake(db_path)

    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    reopened_store = RequestIntake(db_path)
    reloaded_request = reopened_store.get_request(created["request_id"])
    reloaded_audit_log = reopened_store.get_audit_log(created["request_id"])

    assert reloaded_request == created
    assert len(reloaded_audit_log) == 1
    assert reloaded_audit_log[0].request_id == created["request_id"]
    assert reloaded_audit_log[0].analyst_id == "analyst-1"
    assert reloaded_audit_log[0].event == "request_submitted"


def test_update_status_updates_status_and_writes_audit_entry(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    updated = store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="analyzed")

    assert updated["status"] == "analyzed"

    audit_log = store.get_audit_log(created["request_id"])
    assert [entry.event for entry in audit_log] == ["request_submitted", "status_updated"]
    status_entry = audit_log[1]
    assert status_entry.request_id == created["request_id"]
    assert status_entry.analyst_id == "pm-1"
    assert status_entry.timestamp


def test_update_status_raises_on_unknown_request_id(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))

    with pytest.raises(KeyError):
        store.update_status(request_id="does-not-exist", analyst_id="pm-1", new_status="completed")

    assert store.get_audit_log() == []


def test_update_status_raises_on_invalid_status(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    with pytest.raises(ValueError):
        store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="not_a_real_status")

    unchanged = store.get_request(created["request_id"])
    assert unchanged["status"] == "intake"
    assert [entry.event for entry in store.get_audit_log(created["request_id"])] == ["request_submitted"]


def test_update_status_allows_analysis_failed_to_intake_retry(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="analysis_failed")

    updated = store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="intake")

    assert updated["status"] == "intake"


def test_update_status_allows_analyzed_to_completed(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="analyzed")

    updated = store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="completed")

    assert updated["status"] == "completed"


def test_update_status_blocks_completed_to_intake(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")
    store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="analyzed")
    store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="completed")

    with pytest.raises(InvalidTransitionError):
        store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="intake")

    unchanged = store.get_request(created["request_id"])
    assert unchanged["status"] == "completed"
    events = [entry.event for entry in store.get_audit_log(created["request_id"])]
    assert events == ["request_submitted", "status_updated", "status_updated"]


def test_update_status_blocks_intake_to_completed(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    with pytest.raises(InvalidTransitionError):
        store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="completed")

    unchanged = store.get_request(created["request_id"])
    assert unchanged["status"] == "intake"
    assert [entry.event for entry in store.get_audit_log(created["request_id"])] == ["request_submitted"]


def test_update_status_same_status_is_idempotent_no_op(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    result = store.update_status(request_id=created["request_id"], analyst_id="pm-1", new_status="intake")

    assert result == created
    assert [entry.event for entry in store.get_audit_log(created["request_id"])] == ["request_submitted"]


def test_record_clarification_writes_audit_entry_without_changing_status(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    result = store.record_clarification(
        request_id=created["request_id"], analyst_id="pm-1", event="clarification_questions_generated"
    )

    assert result["status"] == "intake"
    audit_log = store.get_audit_log(created["request_id"])
    assert [entry.event for entry in audit_log] == ["request_submitted", "clarification_questions_generated"]
    assert audit_log[1].analyst_id == "pm-1"
    assert audit_log[1].timestamp


def test_record_clarification_logs_every_call_including_repeats(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="Need a sales dashboard", source_type="email", analyst_id="analyst-1")

    store.record_clarification(
        request_id=created["request_id"], analyst_id="pm-1", event="clarification_not_needed"
    )
    store.record_clarification(
        request_id=created["request_id"], analyst_id="pm-1", event="clarification_not_needed"
    )

    events = [entry.event for entry in store.get_audit_log(created["request_id"])]
    assert events == ["request_submitted", "clarification_not_needed", "clarification_not_needed"]


def test_record_clarification_raises_on_unknown_request_id(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))

    with pytest.raises(KeyError):
        store.record_clarification(
            request_id="does-not-exist", analyst_id="pm-1", event="clarification_not_needed"
        )

    assert store.get_audit_log() == []


def test_record_clarification_stores_error_category_when_given(tmp_path):
    store = RequestIntake(str(tmp_path / "requests.db"))
    created = store.submit_request(text="report.xlsx", source_type="excel", analyst_id="analyst-1")

    store.record_clarification(
        request_id=created["request_id"],
        analyst_id="analyst-1",
        event="field_mapping_failed",
        error_category="corrupt_report",
    )

    audit_log = store.get_audit_log(created["request_id"])
    assert audit_log[1].error_category == "corrupt_report"
