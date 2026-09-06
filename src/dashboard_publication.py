"""
dashboard_publication.py

STORY-010: publishes a validated (finalized) draft solution to
stakeholders (REQ-015). Shares the requests table and audit log with
StakeholderReview and DataValidation -- same request_schema
ensure_schema()/fetch_request() reuse, same _transition() shape
(status-legality check + update + one audit entry in a single atomic
write), since this is another lifecycle transition gated by
human-reviewed state, not a new persistence model.

There is no Power BI/SharePoint credential available in this
environment, so publishing isn't implemented against a real service.
`publisher` is a required extension point: an object with a
`.publish(draft_solution) -> dict` method returning at least a
`dashboard_url`. No publisher configured is itself a legitimate,
testable failure -- "publication client is not configured" -- rather
than silently faking a successful publish, consistent with the rule
that a production dashboard is never published without a real,
authorized publish target.
"""

import sqlite3
from datetime import datetime, timezone

from src.audit_trail import AuditTrail
from src.lifecycle import TRANSITIONS, InvalidTransitionError
from src.request_schema import ensure_schema, fetch_request

__all__ = ["DashboardPublication", "PublicationError"]


class PublicationError(Exception):
    """Raised when a dashboard can't be published, or the published
    result isn't confirmed available -- distinct from an illegal
    lifecycle transition."""


class DashboardPublication:
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

    def publish(self, request_id: str, analyst_id: str, publisher=None) -> dict:
        """Publishes the request's stored draft_solution. Status becomes
        'published' on success (audit event 'dashboard_published', detail
        carries the dashboard URL) or 'publication_failed' on failure
        (audit event 'dashboard_publication_failed', detail carries the
        error) -- so a failed publish is visible on the request and in
        the audit trail without a separate notification channel.
        """
        request = self.get_request(request_id)
        if request is None:
            raise KeyError(f"Unknown request_id: {request_id}")

        current_status = request["status"]
        if "published" not in TRANSITIONS.get(current_status, ()):
            raise InvalidTransitionError(f"Cannot publish from status {current_status!r}")

        try:
            result = self._do_publish(request["draft_solution"], publisher)
        except PublicationError as exc:
            return self._transition(
                request_id,
                analyst_id,
                current_status=current_status,
                new_status="publication_failed",
                event="dashboard_publication_failed",
                detail=str(exc),
            )

        return self._transition(
            request_id,
            analyst_id,
            current_status=current_status,
            new_status="published",
            event="dashboard_published",
            detail=result["dashboard_url"],
        )

    def _do_publish(self, draft_solution: dict, publisher) -> dict:
        if publisher is None:
            raise PublicationError("publication client is not configured")

        try:
            result = publisher.publish(draft_solution)
        except PublicationError:
            raise
        except Exception as exc:
            raise PublicationError(f"publish request failed: {exc}") from exc

        if not isinstance(result, dict) or not result.get("dashboard_url"):
            raise PublicationError("dashboard is not available after publishing")

        return result

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
