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


def _workbook_with_headers(headers: list) -> Workbook:
    workbook = Workbook()
    workbook.active.append(headers)
    return workbook


_VALID_DESIGN_RECOMMENDATION_REPLY = """{
    "data_model": ["Sales fact table", "Region dimension table"],
    "relationships": ["Sales.RegionID -> Region.RegionID"],
    "transformations": ["Aggregate sales by region and quarter"],
    "validation_checks": ["Sales amounts are non-negative"],
    "kpi_definitions": ["Total Revenue = SUM(Sales[Amount])"],
    "dax_measures": ["Total Revenue := SUM(Sales[Amount])"],
    "report_pages": ["Regional Sales Overview"],
    "slicers": ["Region", "Quarter"],
    "visual_design": ["Bar chart comparing revenue by region"]
}"""


def _mock_email_client(reply_text: str = _VALID_EMAIL_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def _mock_design_recommendation_client(reply_text: str = _VALID_DESIGN_RECOMMENDATION_REPLY) -> Mock:
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=reply_text)])
    client = Mock()
    client.messages.create.return_value = response
    return client


def _new_app(tmp_path, email_client=None, design_recommendation_client=None):
    return create_app(
        db_path=str(tmp_path / "test.db"),
        email_client=email_client,
        design_recommendation_client=design_recommendation_client,
    )


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


def test_get_request_returns_current_status_and_audit_trail_in_order(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]
    client.patch(f"/requests/{request_id}/status", json={"status": "analyzed", "analyst_id": "pm-1"})

    response = client.get(f"/requests/{request_id}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["request"]["request_id"] == request_id
    assert body["request"]["status"] == "analyzed"
    assert [entry["event"] for entry in body["audit_log"]] == ["request_submitted", "status_updated"]
    assert body["audit_log"][0]["analyst_id"] == "analyst-1"
    assert body["audit_log"][1]["analyst_id"] == "pm-1"
    assert all(entry["timestamp"] for entry in body["audit_log"])


def test_get_request_returns_404_for_unknown_request_id(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.get("/requests/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"] == "request_not_found"


def test_get_request_does_not_modify_state_or_add_audit_entries(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]

    first = client.get(f"/requests/{request_id}")
    second = client.get(f"/requests/{request_id}")

    assert first.status_code == 200
    assert first.get_json() == second.get_json()

    store = app.config["REQUEST_STORE"]
    assert store.get_request(request_id)["status"] == "intake"
    assert [entry.event for entry in store.get_audit_log(request_id)] == ["request_submitted"]


def test_update_request_status_updates_a_valid_request(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]

    response = client.patch(
        f"/requests/{request_id}/status",
        json={"status": "analyzed", "analyst_id": "pm-1"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "analyzed"

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == ["request_submitted", "status_updated"]
    assert audit_log[1].analyst_id == "pm-1"


def test_update_request_status_rejects_missing_fields(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]

    response = client.patch(f"/requests/{request_id}/status", json={"analyst_id": "pm-1"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_request_status_rejects_invalid_status(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]

    response = client.patch(
        f"/requests/{request_id}/status",
        json={"status": "not_a_real_status", "analyst_id": "pm-1"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_status"

    store = app.config["REQUEST_STORE"]
    assert store.get_request(request_id)["status"] == "intake"


def test_update_request_status_returns_404_for_unknown_request_id(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.patch(
        "/requests/does-not-exist/status",
        json={"status": "completed", "analyst_id": "pm-1"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "request_not_found"


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


def _submit_and_analyze_email_request(client, email_client_reply=_VALID_EMAIL_REPLY, text="Need a sales dashboard"):
    response = client.post(
        "/requests",
        json={"text": text, "source_type": "email", "analyst_id": "analyst-1"},
    )
    return response.get_json()["request_id"]


def test_clarify_request_generates_questions_for_an_incomplete_analysis(tmp_path):
    incomplete_reply = """{
        "business_objectives": ["Increase visibility into quarterly regional sales"],
        "scope": ["Q1 2026 regional sales"],
        "kpis": [],
        "filters": [],
        "calculations": ["Net Margin = Revenue - Cost"],
        "visual_requirements": ["Bar chart comparing revenue by region"],
        "reporting_expectations": ["Weekly summary email"]
    }"""
    email_client = _mock_email_client(reply_text=incomplete_reply)
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(f"/requests/{request_id}/clarify", json={"analyst_id": "pm-1"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["request_id"] == request_id
    assert len(body["questions"]) == 2

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == [
        "request_submitted",
        "analysis_completed",
        "clarification_questions_generated",
    ]
    assert audit_log[-1].analyst_id == "pm-1"


def test_clarify_request_generates_no_questions_for_a_complete_analysis(tmp_path):
    email_client = _mock_email_client()
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(f"/requests/{request_id}/clarify", json={"analyst_id": "pm-1"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["questions"] == []

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == [
        "request_submitted",
        "analysis_completed",
        "clarification_not_needed",
    ]


def test_clarify_request_logs_every_interaction_even_when_called_repeatedly(tmp_path):
    email_client = _mock_email_client()
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    client.post(f"/requests/{request_id}/clarify", json={"analyst_id": "pm-1"})
    client.post(f"/requests/{request_id}/clarify", json={"analyst_id": "pm-1"})

    store = app.config["REQUEST_STORE"]
    events = [entry.event for entry in store.get_audit_log(request_id)]
    assert events == [
        "request_submitted",
        "analysis_completed",
        "clarification_not_needed",
        "clarification_not_needed",
    ]


def test_clarify_request_returns_404_for_unknown_request_id(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post("/requests/does-not-exist/clarify", json={"analyst_id": "pm-1"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "request_not_found"


def test_clarify_request_returns_400_when_analysis_not_available_yet(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]

    response = client.post(f"/requests/{request_id}/clarify", json={"analyst_id": "pm-1"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "no_analysis_available"

    store = app.config["REQUEST_STORE"]
    assert [entry.event for entry in store.get_audit_log(request_id)] == ["request_submitted"]


def test_clarify_request_rejects_missing_analyst_id(tmp_path):
    email_client = _mock_email_client()
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(f"/requests/{request_id}/clarify", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_clarify_excel_request_generates_no_questions_when_workbook_states_everything(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    submit_response = client.post(
        "/requests/excel",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(_sample_xlsx_bytes()), "report.xlsx"),
        },
    )
    request_id = submit_response.get_json()["request_id"]

    response = client.post(f"/requests/{request_id}/clarify", json={"analyst_id": "pm-1"})

    assert response.status_code == 200
    # An empty workbook states nothing except its (auto-named) sheet title,
    # which analyze_report records as "scope" -- so every other field is
    # legitimately missing. This proves the excel path shares the same
    # field schema as the email path (see src/excel_analysis.py's
    # business_objectives key) rather than raising invalid_analysis.
    questions = response.get_json()["questions"]
    assert len(questions) == 6
    assert any("business objective" in q for q in questions)


def test_submit_field_mapping_request_maps_a_valid_workbook(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    workbook_bytes = io.BytesIO()
    _workbook_with_headers(["Region", "Total Revenue"]).save(workbook_bytes)

    response = client.post(
        "/requests/field-mapping",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(workbook_bytes.getvalue()), "report.xlsx"),
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["request_id"]
    assert body["mapped"] == {"Region": "filters", "Total Revenue": "kpis"}
    assert body["flagged"] == []

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(body["request_id"])
    assert [entry.event for entry in audit_log] == ["request_submitted", "field_mapping_completed"]
    assert audit_log[1].analyst_id == "analyst-1"


def test_submit_field_mapping_request_flags_an_unmapped_header_for_review(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    workbook_bytes = io.BytesIO()
    _workbook_with_headers(["Region", "Employee Shoe Size"]).save(workbook_bytes)

    response = client.post(
        "/requests/field-mapping",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(workbook_bytes.getvalue()), "report.xlsx"),
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["mapped"] == {"Region": "filters"}
    assert body["flagged"] == ["Employee Shoe Size"]


def test_submit_field_mapping_request_rejects_missing_file(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post("/requests/field-mapping", data={"analyst_id": "analyst-1"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_submit_field_mapping_request_rejects_unsupported_file_type(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/requests/field-mapping",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(b"not a report"), "report.txt"),
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()

    store = app.config["REQUEST_STORE"]
    assert store.get_audit_log() == []


def test_submit_field_mapping_request_marks_corrupt_workbook_as_failed_without_leaking_content(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    corrupt_bytes = b"not a real workbook"

    response = client.post(
        "/requests/field-mapping",
        data={
            "analyst_id": "analyst-1",
            "file": (io.BytesIO(corrupt_bytes), "report.xlsx"),
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    request_id = body["request_id"]
    assert request_id
    assert body["error"] == "corrupt_report"

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == ["request_submitted", "field_mapping_failed"]

    failure_entry = audit_log[1]
    assert failure_entry.analyst_id == "analyst-1"
    assert failure_entry.error_category == "corrupt_report"

    for entry in audit_log:
        serialized = f"{entry.request_id}|{entry.analyst_id}|{entry.event}|{entry.timestamp}|{entry.error_category}"
        assert corrupt_bytes.decode() not in serialized
        assert os.sep not in serialized


def test_submit_design_recommendation_request_generates_recommendations_for_a_complete_analysis(tmp_path):
    email_client = _mock_email_client()
    design_client = _mock_design_recommendation_client()
    app = _new_app(tmp_path, email_client=email_client, design_recommendation_client=design_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(
        f"/requests/{request_id}/design-recommendations", json={"analyst_id": "pm-1"}
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["request_id"] == request_id
    recommendations = body["recommendations"]
    for field in (
        "data_model",
        "relationships",
        "transformations",
        "validation_checks",
        "kpi_definitions",
        "dax_measures",
        "report_pages",
        "slicers",
        "visual_design",
    ):
        assert field in recommendations

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == [
        "request_submitted",
        "analysis_completed",
        "design_recommendations_generated",
    ]
    assert audit_log[-1].analyst_id == "pm-1"


def test_submit_design_recommendation_request_passes_field_mapping_into_the_prompt(tmp_path):
    email_client = _mock_email_client()
    design_client = _mock_design_recommendation_client()
    app = _new_app(tmp_path, email_client=email_client, design_recommendation_client=design_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    client.post(
        f"/requests/{request_id}/design-recommendations",
        json={"analyst_id": "pm-1", "field_mapping": {"Total Revenue": "kpis"}},
    )

    _, kwargs = design_client.messages.create.call_args
    prompt_sent = kwargs["messages"][0]["content"]
    assert "Total Revenue" in prompt_sent


def test_submit_design_recommendation_request_flags_missing_information_without_calling_model(tmp_path):
    incomplete_reply = """{
        "business_objectives": ["Increase visibility into quarterly regional sales"],
        "scope": ["Q1 2026 regional sales"],
        "kpis": [],
        "filters": [],
        "calculations": ["Net Margin = Revenue - Cost"],
        "visual_requirements": ["Bar chart comparing revenue by region"],
        "reporting_expectations": ["Weekly summary email"]
    }"""
    email_client = _mock_email_client(reply_text=incomplete_reply)
    design_client = _mock_design_recommendation_client()
    app = _new_app(tmp_path, email_client=email_client, design_recommendation_client=design_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(
        f"/requests/{request_id}/design-recommendations", json={"analyst_id": "pm-1"}
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "incomplete_requirements"
    assert body["missing_fields"] == ["kpis", "filters"]
    design_client.messages.create.assert_not_called()

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert [entry.event for entry in audit_log] == [
        "request_submitted",
        "analysis_completed",
        "design_recommendations_missing_data",
    ]
    assert audit_log[-1].error_category == "kpis,filters"


def test_submit_design_recommendation_request_returns_404_for_unknown_request_id(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/requests/does-not-exist/design-recommendations", json={"analyst_id": "pm-1"}
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "request_not_found"


def test_submit_design_recommendation_request_returns_400_when_analysis_not_available_yet(tmp_path):
    app = _new_app(tmp_path)
    client = app.test_client()
    create_response = client.post(
        "/requests",
        json={"text": "Need a sales dashboard", "source_type": "manual", "analyst_id": "analyst-1"},
    )
    request_id = create_response.get_json()["request_id"]

    response = client.post(
        f"/requests/{request_id}/design-recommendations", json={"analyst_id": "pm-1"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "no_analysis_available"

    store = app.config["REQUEST_STORE"]
    assert [entry.event for entry in store.get_audit_log(request_id)] == ["request_submitted"]


def test_submit_design_recommendation_request_rejects_missing_analyst_id(tmp_path):
    email_client = _mock_email_client()
    app = _new_app(tmp_path, email_client=email_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(f"/requests/{request_id}/design-recommendations", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_submit_design_recommendation_request_marks_invalid_model_response_as_failed(tmp_path):
    email_client = _mock_email_client()
    design_client = _mock_design_recommendation_client(reply_text="this is not json")
    app = _new_app(tmp_path, email_client=email_client, design_recommendation_client=design_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(
        f"/requests/{request_id}/design-recommendations", json={"analyst_id": "pm-1"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_model_response"

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert audit_log[-1].event == "design_recommendations_failed"
    assert audit_log[-1].error_category == "invalid_model_response"


def test_submit_design_recommendation_request_marks_unavailable_model_as_failed(tmp_path):
    email_client = _mock_email_client()
    design_client = Mock()
    api_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    design_client.messages.create.side_effect = anthropic.APIConnectionError(request=api_request)
    app = _new_app(tmp_path, email_client=email_client, design_recommendation_client=design_client)
    client = app.test_client()
    request_id = _submit_and_analyze_email_request(client)

    response = client.post(
        f"/requests/{request_id}/design-recommendations", json={"analyst_id": "pm-1"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "design_recommendation_unavailable"

    store = app.config["REQUEST_STORE"]
    audit_log = store.get_audit_log(request_id)
    assert audit_log[-1].event == "design_recommendations_failed"
    assert audit_log[-1].error_category == "design_recommendation_unavailable"
