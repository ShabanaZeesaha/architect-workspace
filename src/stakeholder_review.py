import json
import sqlite3
from datetime import datetime, timezone

from src.audit_trail import AuditTrail
from src.lifecycle import TRANSITIONS, InvalidTransitionError
from src.request_schema import ensure_schema, fetch_request

__all__ = ["StakeholderReview"]


class StakeholderReview:
    """SQLite-backed operations for the STORY-008 review workflow. Shares
    the same `requests` table and audit log as RequestIntake -- reuses
    request_schema.ensure_schema()/fetch_request() rather than duplicating
    table knowledge, same way AuditTrail is shared rather than duplicated.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
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

    def get_request(self, request_id: str) -> dict | None:
        return fetch_request(self.db_path, request_id)

    def submit_draft_for_review(
        self, request_id: str, analyst_id: str, draft_solution: dict
    ) -> dict:
        """Persists a draft solution and moves the request into in_review.
        Reuses the lifecycle TRANSITIONS map so this is only legal from a
        status that actually allows it (analyzed, or changes_requested on a
        resubmission) -- same enforcement RequestIntake.update_status()
        applies, not a separate rule.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        draft_json = json.dumps(draft_solution)

        conn = self._connect()
        try:
            with conn:
                row = conn.execute(
                    "SELECT status FROM requests WHERE request_id = ?", (request_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"Unknown request_id: {request_id}")

                current_status = row["status"]
                if "in_review" not in TRANSITIONS.get(current_status, ()):
                    raise InvalidTransitionError(
                        f"Cannot submit for review from status {current_status!r}"
                    )

                conn.execute(
                    "UPDATE requests SET draft_solution = ?, status = ? WHERE request_id = ?",
                    (draft_json, "in_review", request_id),
                )
                self._audit.append(
                    conn, request_id, analyst_id, "draft_submitted_for_review", timestamp
                )
        finally:
            conn.close()
        return self.get_request(request_id)

    def approve(self, request_id: str, analyst_id: str) -> dict:
        """Approves a draft in review. This is the only path in this system
        that sets status to 'approved' -- the human-approval gate REQ-012
        requires, since no AI-calling code in this pipeline ever reaches
        this method on its own. Logs one audit entry carrying the
        approver's ID and timestamp (AuditEntry.analyst_id/timestamp),
        which is what STORY-008's trust criterion asks for -- no new
        column needed.
        """
        return self._transition(request_id, analyst_id, new_status="approved", event="draft_approved")

    def request_changes(self, request_id: str, analyst_id: str, feedback: str) -> dict:
        """Sends a draft back for revision. feedback is required -- a
        'changes requested' with nothing to act on doesn't satisfy
        STORY-008's 'the system logs the request' criterion -- and is
        stored in the audit entry's error_category column, the same
        general-purpose free-text detail slot field mapping (STORY-004)
        and every AI-generation route already reuse for non-error detail,
        not a new column.
        """
        if not feedback:
            raise ValueError("feedback is required to request changes")
        return self._transition(
            request_id,
            analyst_id,
            new_status="changes_requested",
            event="changes_requested",
            detail=feedback,
        )

    def _transition(
        self, request_id: str, analyst_id: str, new_status: str, event: str, detail: str | None = None
    ) -> dict:
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
                if new_status not in TRANSITIONS.get(current_status, ()):
                    raise InvalidTransitionError(
                        f"Cannot transition from {current_status!r} to {new_status!r}"
                    )

                conn.execute(
                    "UPDATE requests SET status = ? WHERE request_id = ?",
                    (new_status, request_id),
                )
                self._audit.append(conn, request_id, analyst_id, event, timestamp, detail)
        finally:
            conn.close()
        return self.get_request(request_id)
