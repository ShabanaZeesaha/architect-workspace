"""
audit_trail.py

Append-only audit log shared by request intake, analysis, and requirement
clarification: every interaction on a request writes one row here. Writes
take an open connection so they land in the same transaction as the
caller's own change (e.g. updating a request's status); reads open their
own connection since they don't need to share a transaction.

Split out of request_intake.py to keep that file under this repo's 200-line
limit (see CLAUDE.md) once requirement clarification needed to append here
too.
"""

import sqlite3
from dataclasses import dataclass
from typing import Optional

__all__ = ["AuditEntry", "AuditTrail"]

_SCHEMA = """
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
    error_category: Optional[str] = None


class AuditTrail:
    """Owns the audit_log table."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(_SCHEMA)

    def append(
        self,
        conn: sqlite3.Connection,
        request_id: str,
        analyst_id: str,
        event: str,
        timestamp: str,
        error_category: Optional[str] = None,
    ) -> None:
        conn.execute(
            "INSERT INTO audit_log (request_id, analyst_id, event, timestamp, error_category) "
            "VALUES (?, ?, ?, ?, ?)",
            (request_id, analyst_id, event, timestamp, error_category),
        )

    def get(self, request_id: Optional[str] = None) -> list[AuditEntry]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
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
