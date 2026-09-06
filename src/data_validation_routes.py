"""
data_validation_routes.py

Registers the STORY-009 data-validation HTTP endpoint on the Flask app.
Kept out of app.py (at this repo's 200-line cap -- see CLAUDE.md) and out
of data_validation.py itself (that module owns the transition/persistence
logic, not HTTP wiring) -- same split rationale as every other *_routes.py
module in this pipeline.

One endpoint: POST /requests/<id>/validate. It has no request body of its
own -- it validates whatever analysis/draft_solution is already stored on
the request record, the same "operate on already-persisted state" pattern
review_draft() uses for approve/request_changes.

DataValidation.validate() already writes the status update and the audit
entry atomically in one transaction (see _transition() in
data_validation.py), so unlike the AI-generation routes there's no
separate audit-write step to wrap -- but this story's failure list
explicitly names "audit trail logging fails" as a case to handle, so a
sqlite3.Error raised inside that atomic write (and re-raised after the
transaction rolls back) is caught here and turned into a controlled 500
(audit_log_unavailable) instead of an unhandled exception.
"""

import sqlite3

from flask import Flask, jsonify, request

from src.data_validation import DataValidation, MissingValidationDataError
from src.lifecycle import InvalidTransitionError
from src.request_intake import RequestIntake


def register_data_validation_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/validate")
    def validate_request_data(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        if store.get_request(request_id) is None:
            return jsonify({"error": "request_not_found"}), 404

        validation: DataValidation = app.config["DATA_VALIDATION"]
        try:
            updated, violations = validation.validate(request_id=request_id, analyst_id=analyst_id)
        except InvalidTransitionError as exc:
            return jsonify({"error": "invalid_transition", "detail": str(exc)}), 409
        except MissingValidationDataError as exc:
            return jsonify({"error": "missing_validation_data", "detail": str(exc)}), 400
        except sqlite3.Error:
            return jsonify({"error": "audit_log_unavailable"}), 500

        return jsonify({"request": updated, "violations": violations}), 200
