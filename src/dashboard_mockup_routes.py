"""
dashboard_mockup_routes.py

Registers the dashboard-mockup HTTP endpoint on the Flask app. Kept out of
app.py (at this repo's 200-line cap -- see CLAUDE.md) and out of
dashboard_mockup.py itself (that module owns the AI call and validation,
not HTTP wiring) -- same split rationale as design_recommendation_routes.py.

The design recommendation a mockup is built from isn't persisted on the
request record -- design_recommendation_routes.py doesn't store it either,
only returns it in the response -- so it's supplied directly in the
request payload here, not fetched from the stored record.

Every outcome -- missing data, a mockup generated, a template mismatch, or
the model failing/returning garbage -- writes one audit entry via
RequestIntake.record_clarification(), the same audit-only "record what
happened" pattern used by every AI-assisted step in this pipeline so far
(requirement clarification, field mapping, design recommendations).

If that audit write itself fails (e.g. the SQLite file is locked or
unwritable), the outcome is unrecorded and this system's traceability
guardrail is violated -- so this route returns a controlled 500
(audit_log_unavailable) instead of the outcome's normal response, rather
than silently returning success/failure for something that was never
logged, or letting the raw database exception crash the request.
"""

import sqlite3

from flask import Flask, jsonify, request

from src.dashboard_mockup import (
    DashboardMockupError,
    IncompleteRecommendationError,
    generate_dashboard_mockup,
)
from src.dashboard_mockup_template import (
    InvalidDashboardMockupResponseError,
    MockupTemplateMismatchError,
)
from src.request_intake import RequestIntake

DASHBOARD_MOCKUP_MISSING_DATA = "dashboard_mockup_missing_data"
DASHBOARD_MOCKUP_GENERATED = "dashboard_mockup_generated"
DASHBOARD_MOCKUP_TEMPLATE_MISMATCH = "dashboard_mockup_template_mismatch"
DASHBOARD_MOCKUP_FAILED = "dashboard_mockup_failed"


def _record_audit_event(store: RequestIntake, request_id: str, analyst_id: str, event: str, error_category: str | None = None):
    """Writes one audit entry; returns a controlled error response tuple if the
    write itself fails, or None on success."""
    try:
        store.record_clarification(
            request_id=request_id, analyst_id=analyst_id, event=event, error_category=error_category
        )
        return None
    except sqlite3.Error:
        return jsonify({"error": "audit_log_unavailable"}), 500


def register_dashboard_mockup_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/dashboard-mockup")
    def submit_dashboard_mockup_request(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")
        recommendation = payload.get("recommendation")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400
        if not isinstance(recommendation, dict):
            return jsonify({"error": "recommendation is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.get_request(request_id)
        if record is None:
            return jsonify({"error": "request_not_found"}), 404

        client = app.config.get("DASHBOARD_MOCKUP_CLIENT")
        try:
            mockup = generate_dashboard_mockup(recommendation, client=client)
        except IncompleteRecommendationError as exc:
            audit_error = _record_audit_event(
                store,
                request_id,
                analyst_id,
                DASHBOARD_MOCKUP_MISSING_DATA,
                error_category=",".join(exc.missing_fields),
            )
            if audit_error:
                return audit_error
            return (
                jsonify(
                    {"error": "incomplete_recommendation", "missing_fields": exc.missing_fields}
                ),
                400,
            )
        except MockupTemplateMismatchError as exc:
            audit_error = _record_audit_event(
                store,
                request_id,
                analyst_id,
                DASHBOARD_MOCKUP_TEMPLATE_MISMATCH,
                error_category="; ".join(exc.violations),
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "template_mismatch", "violations": exc.violations}), 400
        except InvalidDashboardMockupResponseError:
            audit_error = _record_audit_event(
                store, request_id, analyst_id, DASHBOARD_MOCKUP_FAILED, error_category="invalid_model_response"
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "invalid_model_response"}), 400
        except DashboardMockupError:
            audit_error = _record_audit_event(
                store,
                request_id,
                analyst_id,
                DASHBOARD_MOCKUP_FAILED,
                error_category="dashboard_mockup_unavailable",
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "dashboard_mockup_unavailable"}), 400

        audit_error = _record_audit_event(store, request_id, analyst_id, DASHBOARD_MOCKUP_GENERATED)
        if audit_error:
            return audit_error
        return jsonify({"request_id": request_id, "mockup": mockup}), 201
