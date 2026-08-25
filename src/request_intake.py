import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

INITIAL_STATUS = "intake"

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
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    event TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    error_category TEXT
);
"""


@dataclass
class AuditEntry:
    request_id: str
    analyst_id: str
    event: str
    timestamp: str
    error_category: str | None = None


class RequestIntake:
    """SQLite-backed store for submitted requests and their audit trail."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        conn = self._connect()
        try:
            with conn:
                conn.executescript(_SCHEMA)
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
                conn.execute(
                    "INSERT INTO audit_log (request_id, analyst_id, event, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (request_id, analyst_id, "request_submitted", timestamp),
                )
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
                conn.execute(
                    "INSERT INTO audit_log (request_id, analyst_id, event, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (request_id, analyst_id, "analysis_completed", timestamp),
                )
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
                conn.execute(
                    "INSERT INTO audit_log "
                    "(request_id, analyst_id, event, timestamp, error_category) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (request_id, analyst_id, "analysis_failed", timestamp, error_category),
                )
        finally:
            conn.close()
        return self.get_request(request_id)

    def get_audit_log(self, request_id: str | None = None) -> list[AuditEntry]:
        conn = self._connect()
        try:
            if request_id is None:
                rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit_log WHERE request_id = ? ORDER BY id ASC",
                    (request_id,),
                ).fetchall()
        finally:
            conn.close()
        return [
            AuditEntry(
                request_id=row["request_id"],
                analyst_id=row["analyst_id"],
                event=row["event"],
                timestamp=row["timestamp"],
                error_category=row["error_category"],
            )
            for row in rows
        ]

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
