import io
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
from openpyxl import Workbook

from src.app import create_app

_VALID_EMAIL_REPLY = """{
    "business_objectives": ["Increase visibility into quarterly regional sales"],
    "scope": ["Q1 2026 regional sales"],
    "kpis": ["Total Revenue"],
    "filters": ["Region"],
    "calculations": ["Net Margin = Revenue - Cost"],
    "visual_requirements": ["Bar chart comparing revenue by region"],
    "reporting_expectations": ["Weekly summary email"]
}"""


def _sample_xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    Workbook().save(buffer)
    return buffer.getvalue()


def _mock_email_client(reply_text: str = _VALID_EMAIL_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def _new_app(tmp_path, email_client=None):
    return create_app(db_path=str(tmp_path / "test.db"), email_client=email_client)


def test_health_returns_ok(tmp_path):
    client = _new_app(tmp_path).test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_version_returns_string(tmp_path):
    client = _new_app(tmp_path).test_client()

    response = client.get("/version")

    assert response.status_code == 200
    assert response.get_json() == {"version": "0.1.0"}


def test_submit_request_records_a_valid_request_and_audit_entry(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["request_id"]
    assert body["source_type"] == "manual"
    assert body["analyst_id"] == "analyst-1"
    assert body["status"] == "intake"

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(body["request_id"])
    assert len(audit_log) == 1
    assert audit_log[0].request_id == body["request_id"]
    assert audit_log[0].analyst_id == "analyst-1"
    assert audit_log[0].event == "request_submitted"
    assert audit_log[0].timestamp == body["submitted_at"]


def test_submit_email_request_analyzes_and_persists_result(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    db_path = str(tmp_path / "test.db")
    email_client = _mock_email_client()
    app = create_app(db_path=db_path, email_client=email_client)
    client = app.test_client()

    response = client.post(
        "/requests",
        json={
            "text": "Need a sales dashboard broken down by region",
            "source_type": "email",
            "analyst_id": "analyst-1",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "analyzed"
    assert body["analysis"]["business_objectives"] == ["Increase visibility into quarterly regional sales"]
    assert body["analysis"]["kpis"] == ["Total Revenue"]
    email_client.messages.create.assert_called_once()

    # Reopen a brand-new RequestIntake on the same database file to prove the
    # analysis and audit trail are durable, not just held in this process.
    from src.request_intake import RequestIntake

    reopened_store = RequestIntake(db_path)
    reloaded_request = reopened_store.get_request(body["request_id"])
    assert reloaded_request["status"] == "analyzed"
    assert reloaded_request["analysis"] == body["analysis"]

    audit_log = reopened_store.get_audit_log(body["request_id"])
    assert [entry.event for entry in audit_log] == ["request_submitted", "analysis_completed"]
    completion_entry = audit_log[1]
    assert completion_entry.request_id == body["request_id"]
    assert completion_entry.analyst_id == "analyst-1"
    assert datetime.fromisoformat(completion_entry.timestamp).tzinfo is not None


def test_submit_email_request_marks_invalid_model_response_as_failed_without_leaking_content(tmp_path):
    email_text = "Need a sales dashboard broken down by region"
    email_client = _mock_email_client(reply_text="not valid json at all")
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()

    response = client.post(
        "/requests",
        json={"text": email_text, "source_type": "email", "analyst_id": "analyst-1"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "invalid_model_response"
    request_id = body["request_id"]

    store = app.config["REQUEST_STORE"]
    stored_request = store.get_request(request_id)
    assert stored_request is not None
    assert stored_request["status"] == "analysis_failed"

    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == ["request_submitted", "analysis_failed"]
    failure_entry = audit_log[1]
    assert failure_entry.error_category == "invalid_model_response"

    for entry in audit_log:
        serialized = f"{entry.request_id}|{entry.analyst_id}|{entry.event}|{entry.timestamp}|{entry.error_category}"
        assert "not valid json at all" not in serialized
        assert email_text not in serialized


def test_submit_email_request_marks_simulated_api_failure_as_failed(tmp_path):
    email_client = Mock()
    request_obj = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    email_client.messages.create.side_effect = anthropic.APIConnectionError(request=request_obj)
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()

    response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "email", "analyst_id": "analyst-1"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "email_analysis_unavailable"

    store = app.config["REQUEST_STORE"]
    stored_request = store.get_request(body["request_id"])
    assert stored_request["status"] == "analysis_failed"

    audit_log = store.get_audit_log(body["request_id"])
    assert audit_log[1].error_category == "email_analysis_unavailable"


def test_submit_excel_request_analyzes_a_valid_workbook(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/requests/excel",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(_sample_xlsx_bytes()), "report.xlsx"),
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["request_id"]
    assert body["status"] == "analyzed"
    assert "scope" in body["analysis"]

    store = app.config["REQUEST_STORE"]
    stored_request = store.get_request(body["request_id"])
    assert stored_request["request_id"] == body["request_id"]
    assert stored_request["analysis"] == body["analysis"]

    audit_log = store.get_audit_log(body["request_id"])
    assert [entry.event for entry in audit_log] == ["request_submitted", "analysis_completed"]

    completion_entry = audit_log[1]
    assert completion_entry.request_id == body["request_id"]
    assert completion_entry.analyst_id == "analyst-1"
    assert datetime.fromisoformat(completion_entry.timestamp).tzinfo is not None


def test_submit_excel_request_rejects_missing_file(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post("/requests/excel", data={"analyst_id": "analyst-1"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_submit_excel_request_rejects_unsupported_file_type(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/requests/excel",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(b"a,b,c"), "report.csv"),
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_submit_excel_request_marks_corrupt_workbook_as_failed_without_leaking_content(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    corrupt_bytes = b"not a real workbook"

    response = client.post(
        "/requests/excel",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(corrupt_bytes), "report.xlsx"),
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    request_id = body["request_id"]
    assert request_id

    store = app.config["REQUEST_STORE"]
    stored_request = store.get_request(request_id)
    assert stored_request is not None
    assert stored_request["status"] == "analysis_failed"

    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == ["request_submitted", "analysis_failed"]

    failure_entry = audit_log[1]
    assert failure_entry.request_id == request_id
    assert failure_entry.analyst_id == "analyst-1"
    assert failure_entry.error_category == "corrupt_excel"
    assert datetime.fromisoformat(failure_entry.timestamp).tzinfo is not None

    for entry in audit_log:
        serialized = f"{entry.request_id}|{entry.analyst_id}|{entry.event}|{entry.timestamp}|{entry.error_category}"
        assert corrupt_bytes.decode() not in serialized
        assert "report.xlsx" not in serialized
        assert os.sep not in serialized
