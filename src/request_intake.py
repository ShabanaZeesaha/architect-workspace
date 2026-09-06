import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from src.audit_trail import AuditEntry, AuditTrail
from src.lifecycle import INITIAL_STATUS, TRANSITIONS, VALID_STATUSES, InvalidTransitionError
from src.request_schema import ensure_schema, fetch_request

__all__ = ["AuditEntry", "InvalidTransitionError", "RequestIntake"]


class RequestIntake:
    """SQLite-backed store for submitted requests, with a shared AuditTrail
    for their audit history."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self._audit = AuditTrail(db_path)

        conn = self._connect()
        try:
            with conn:
                ensure_schema(conn)
                self._audit.ensure_schema(conn)
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def submit_request(self, text: str, source_type: str, analyst_id: str) -> dict:
        request_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO requests "
                    "(request_id, text, source_type, analyst_id, submitted_at, status) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (request_id, text, source_type, analyst_id, timestamp, INITIAL_STATUS),
                )
                self._audit.append(conn, request_id, analyst_id, "request_submitted", timestamp)
        finally:
            conn.close()
        return self.get_request(request_id)

    def get_request(self, request_id: str) -> dict | None:
        return fetch_request(self.db_path, request_id)

    def complete_analysis(self, request_id: str, analyst_id: str, analysis: dict) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        analysis_json = json.dumps(analysis)

        conn = self._connect()
        try:
            with conn:
                cursor = conn.execute(
                    "UPDATE requests SET analysis = ?, status = ? WHERE request_id = ?",
                    (analysis_json, "analyzed", request_id),
                )
                if cursor.rowcount == 0:
                    raise KeyError(f"Unknown request_id: {request_id}")
                self._audit.append(conn, request_id, analyst_id, "analysis_completed", timestamp)
        finally:
            conn.close()
        return self.get_request(request_id)

    def fail_analysis(self, request_id: str, analyst_id: str, error_category: str) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            with conn:
                cursor = conn.execute(
                    "UPDATE requests SET status = ? WHERE request_id = ?",
                    ("analysis_failed", request_id),
                )
                if cursor.rowcount == 0:
                    raise KeyError(f"Unknown request_id: {request_id}")
                self._audit.append(
                    conn, request_id, analyst_id, "analysis_failed", timestamp, error_category
                )
        finally:
            conn.close()
        return self.get_request(request_id)

    def update_status(self, request_id: str, analyst_id: str, new_status: str) -> dict:
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status!r}")

        timestamp = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            with conn:
                row = conn.execute(
                    "SELECT status FROM requests WHERE request_id = ?", (request_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown request_id: {request_id}")

                current_status = row["status"]
                if new_status == current_status:
                    return self.get_request(request_id)

                if new_status not in TRANSITIONS[current_status]:
                    raise InvalidTransitionError(
                        f"Cannot transition from {current_status!r} to {new_status!r}"
                    )

                conn.execute(
                    "UPDATE requests SET status = ? WHERE request_id = ?",
                    (new_status, request_id),
                )
                self._audit.append(conn, request_id, analyst_id, "status_updated", timestamp)
        finally:
            conn.close()
        return self.get_request(request_id)

    def record_clarification(
        self, request_id: str, analyst_id: str, event: str, error_category: str | None = None
    ) -> dict:
        """Appends an audit-only interaction to the audit trail without
        changing the request's lifecycle status -- generating/reviewing
        follow-up questions, or mapping fields on an upload, is not itself a
        status transition. Originally added for requirement clarification
        (REQ-004); reused as-is by field mapping (REQ-003, see
        src/field_mapping_routes.py) since both are "record what happened"
        actions. error_category is optional and only field mapping's
        failure path sets it, matching fail_analysis()'s pattern above.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            with conn:
                row = conn.execute(
                    "SELECT request_id FROM requests WHERE request_id = ?", (request_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown request_id: {request_id}")
                self._audit.append(conn, request_id, analyst_id, event, timestamp, error_category)
        finally:
            conn.close()
        return self.get_request(request_id)

    def get_audit_log(self, request_id: str | None = None) -> list[AuditEntry]:
        return self._audit.get(request_id)
