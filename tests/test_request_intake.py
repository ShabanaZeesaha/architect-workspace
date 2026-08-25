from src.request_intake import RequestIntake


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
