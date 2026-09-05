"""
powerbi_solution_routes.py

Registers the draft-Power-BI-solution HTTP endpoint on the Flask app. Kept
out of app.py (at this repo's 200-line cap -- see CLAUDE.md) and out of
powerbi_solution.py itself (that module owns the AI call and validation,
not HTTP wiring) -- same split rationale as dashboard_mockup_routes.py.

The dashboard mockup a draft solution is built from isn't persisted on the
request record -- dashboard_mockup_routes.py doesn't store it either, only
returns it in the response -- so it's supplied directly in the request
payload here, not fetched from the stored record.

Every outcome -- an invalid mockup, a solution generated, a mockup
mismatch, or the model failing/returning garbage -- writes one audit entry
via RequestIntake.record_clarification(), the same audit-only "record what
happened" pattern used by every AI-assisted step in this pipeline so far.
This is what satisfies REQ-007's "logs draft generation in the audit
trail" trust criterion.

If that audit write itself fails (e.g. the SQLite file is locked or
unwritable), the outcome is unrecorded and this system's traceability
guardrail is violated -- so this route returns a controlled 500
(audit_log_unavailable) instead of the outcome's normal response, same
guard as dashboard_mockup_routes.py.
"""

import sqlite3

from flask import Flask, jsonify, request

from src.powerbi_solution import (
    InvalidMockupInputError,
    PowerBiSolutionError,
    generate_draft_powerbi_solution,
)
from src.powerbi_solution_template import DraftMockupMismatchError, InvalidDraftSolutionResponseError
from src.request_intake import RequestIntake

POWERBI_SOLUTION_INVALID_MOCKUP = "powerbi_solution_invalid_mockup"
POWERBI_SOLUTION_GENERATED = "powerbi_solution_generated"
POWERBI_SOLUTION_MOCKUP_MISMATCH = "powerbi_solution_mockup_mismatch"
POWERBI_SOLUTION_FAILED = "powerbi_solution_failed"


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


def register_powerbi_solution_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/powerbi-solution")
    def submit_powerbi_solution_request(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")
        mockup = payload.get("mockup")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400
        if not isinstance(mockup, dict):
            return jsonify({"error": "mockup is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.get_request(request_id)
        if record is None:
            return jsonify({"error": "request_not_found"}), 404

        client = app.config.get("POWERBI_SOLUTION_CLIENT")
        try:
            solution = generate_draft_powerbi_solution(mockup, client=client)
        except InvalidMockupInputError as exc:
            audit_error = _record_audit_event(
                store, request_id, analyst_id, POWERBI_SOLUTION_INVALID_MOCKUP, error_category=str(exc)
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "invalid_mockup", "detail": str(exc)}), 400
        except DraftMockupMismatchError as exc:
            audit_error = _record_audit_event(
                store,
                request_id,
                analyst_id,
                POWERBI_SOLUTION_MOCKUP_MISMATCH,
                error_category="; ".join(exc.violations),
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "mockup_mismatch", "violations": exc.violations}), 400
        except InvalidDraftSolutionResponseError:
            audit_error = _record_audit_event(
                store, request_id, analyst_id, POWERBI_SOLUTION_FAILED, error_category="invalid_model_response"
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "invalid_model_response"}), 400
        except PowerBiSolutionError:
            audit_error = _record_audit_event(
                store,
                request_id,
                analyst_id,
                POWERBI_SOLUTION_FAILED,
                error_category="powerbi_solution_unavailable",
            )
            if audit_error:
                return audit_error
            return jsonify({"error": "powerbi_solution_unavailable"}), 400

        audit_error = _record_audit_event(store, request_id, analyst_id, POWERBI_SOLUTION_GENERATED)
        if audit_error:
            return audit_error
        return jsonify({"request_id": request_id, "solution": solution}), 201
