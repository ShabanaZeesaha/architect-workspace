"""
data_validation.py

STORY-009: validates data accuracy on an approved draft solution before
finalization (REQ-014). Shares the requests table and audit log with
StakeholderReview -- same request_schema.ensure_schema()/fetch_request()
reuse, same _transition() shape (status-legality check + update + one
audit entry in a single atomic write), since this is another lifecycle
transition gated by human-reviewed state, not a new persistence model.
"""

import sqlite3
from datetime import datetime, timezone

from src.audit_trail import AuditTrail
from src.data_validation_rules import find_data_accuracy_violations
from src.lifecycle import TRANSITIONS, InvalidTransitionError
from src.request_schema import ensure_schema, fetch_request

__all__ = ["DataValidation", "MissingValidationDataError"]


class MissingValidationDataError(ValueError):
    """Raised when a request has no analysis and/or no draft_solution to
    validate -- distinct from an illegal lifecycle transition."""


class DataValidation:
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

    def validate(self, request_id: str, analyst_id: str) -> tuple[dict, list[str]]:
        """Validates the request's stored draft_solution against its
        analysis. Returns (updated_request, violations) -- violations is
        empty on success (status becomes 'validated'); non-empty means the
        draft was flagged for correction (status becomes
        'changes_requested', reusing STORY-008's existing loop) and the
        violations are stored as the audit entry's detail.
        """
        request = self.get_request(request_id)
        if request is None:
            raise KeyError(f"Unknown request_id: {request_id}")

        analysis = request.get("analysis")
        draft_solution = request.get("draft_solution")
        if not analysis or not draft_solution:
            raise MissingValidationDataError(
                "request has no analysis and/or draft_solution to validate"
            )

        violations = find_data_accuracy_violations(analysis, draft_solution)
        if violations:
            updated = self._transition(
                request_id,
                analyst_id,
                current_status=request["status"],
                new_status="changes_requested",
                event="data_validation_failed",
                detail="; ".join(violations),
            )
        else:
            updated = self._transition(
                request_id,
                analyst_id,
                current_status=request["status"],
                new_status="validated",
                event="data_validation_passed",
            )
        return updated, violations

    def _transition(
        self,
        request_id: str,
        analyst_id: str,
        current_status: str,
        new_status: str,
        event: str,
        detail: str | None = None,
    ) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            with conn:
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
