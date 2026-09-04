import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from src.audit_trail import AuditEntry, AuditTrail
from src.lifecycle import INITIAL_STATUS, TRANSITIONS, VALID_STATUSES, InvalidTransitionError

__all__ = ["AuditEntry", "InvalidTransitionError", "RequestIntake"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    source_type TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL,
    analysis TEXT
);
"""


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
                conn.executescript(_SCHEMA)
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
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        finally:
            conn.close()
        return self._row_to_request(row) if row is not None else None

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

    def record_clarification(self, request_id: str, analyst_id: str, event: str) -> dict:
        """Appends a requirement-clarification interaction to the audit
        trail. Does not change the request's lifecycle status -- generating
        or reviewing follow-up questions is not itself a status transition.
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
                self._audit.append(conn, request_id, analyst_id, event, timestamp)
        finally:
            conn.close()
        return self.get_request(request_id)

    def get_audit_log(self, request_id: str | None = None) -> list[AuditEntry]:
        return self._audit.get(request_id)

    @staticmethod
    def _row_to_request(row: sqlite3.Row) -> dict:
        record = {
            "request_id": row["request_id"],
            "text": row["text"],
            "source_type": row["source_type"],
            "analyst_id": row["analyst_id"],
            "submitted_at": row["submitted_at"],
            "status": row["status"],
        }
        if row["analysis"] is not None:
            record["analysis"] = json.loads(row["analysis"])
        return record
