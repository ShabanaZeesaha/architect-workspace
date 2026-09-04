import sqlite3

from src.audit_trail import AuditTrail


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_append_and_get_round_trip_an_entry(tmp_path):
    db_path = str(tmp_path / "audit.db")
    trail = AuditTrail(db_path)
    conn = _connect(db_path)

    with conn:
        trail.ensure_schema(conn)
        trail.append(conn, "req-1", "analyst-1", "request_submitted", "2026-01-01T00:00:00+00:00")
    conn.close()

    entries = trail.get("req-1")

    assert len(entries) == 1
    assert entries[0].request_id == "req-1"
    assert entries[0].analyst_id == "analyst-1"
    assert entries[0].event == "request_submitted"
    assert entries[0].error_category is None


def test_get_filters_by_request_id(tmp_path):
    db_path = str(tmp_path / "audit.db")
    trail = AuditTrail(db_path)
    conn = _connect(db_path)

    with conn:
        trail.ensure_schema(conn)
        trail.append(conn, "req-1", "analyst-1", "request_submitted", "2026-01-01T00:00:00+00:00")
        trail.append(conn, "req-2", "analyst-1", "request_submitted", "2026-01-01T00:00:01+00:00")
    conn.close()

    entries = trail.get("req-2")

    assert [e.request_id for e in entries] == ["req-2"]


def test_get_with_no_request_id_returns_all_entries_in_order(tmp_path):
    db_path = str(tmp_path / "audit.db")
    trail = AuditTrail(db_path)
    conn = _connect(db_path)

    with conn:
        trail.ensure_schema(conn)
        trail.append(conn, "req-1", "analyst-1", "request_submitted", "2026-01-01T00:00:00+00:00")
        trail.append(conn, "req-1", "analyst-1", "analysis_completed", "2026-01-01T00:00:01+00:00")
    conn.close()

    entries = trail.get()

    assert [e.event for e in entries] == ["request_submitted", "analysis_completed"]


def test_append_stores_error_category_when_given(tmp_path):
    db_path = str(tmp_path / "audit.db")
    trail = AuditTrail(db_path)
    conn = _connect(db_path)

    with conn:
        trail.ensure_schema(conn)
        trail.append(
            conn, "req-1", "analyst-1", "analysis_failed", "2026-01-01T00:00:00+00:00", "invalid_model_response"
        )
    conn.close()

    entries = trail.get("req-1")

    assert entries[0].error_category == "invalid_model_response"
