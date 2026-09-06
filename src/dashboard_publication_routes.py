"""
dashboard_publication_routes.py

Registers the STORY-010 publication HTTP endpoint on the Flask app.
Kept out of app.py (at this repo's 200-line cap -- see CLAUDE.md) and out
of dashboard_publication.py itself (that module owns the
transition/persistence logic, not HTTP wiring) -- same split rationale as
every other *_routes.py module in this pipeline.

One endpoint: POST /requests/<id>/publish. It has no request body beyond
analyst_id -- it publishes whatever draft_solution is already stored on
the request record, the same "operate on already-persisted state"
pattern validate_request_data() uses.

DashboardPublication.publish() already writes the status update and the
audit entry atomically in one transaction (see _transition() in
dashboard_publication.py), and it converts a failed publish into a
handled 'publication_failed' status rather than raising -- so the only
exception this route needs to guard against is a sqlite3.Error raised
inside that atomic write itself (the "audit trail logging fails" case),
which is turned into a controlled 500 (audit_log_unavailable) instead of
an unhandled exception, same as data_validation_routes.py. A handled
publish failure (status stays/moves to publication_failed) is reported
as HTTP 502 rather than 200, so a caller can tell success from failure
without inspecting the response body -- that is this endpoint's "alert
the designer" signal.
"""

import sqlite3

from flask import Flask, jsonify, request

from src.dashboard_publication import DashboardPublication
from src.lifecycle import InvalidTransitionError
from src.request_intake import RequestIntake


def register_dashboard_publication_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/publish")
    def publish_dashboard_request(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        if store.get_request(request_id) is None:
            return jsonify({"error": "request_not_found"}), 404

        publication: DashboardPublication = app.config["DASHBOARD_PUBLICATION"]
        publisher = app.config.get("PUBLICATION_CLIENT")
        try:
            updated = publication.publish(
                request_id=request_id, analyst_id=analyst_id, publisher=publisher
            )
        except InvalidTransitionError as exc:
            return jsonify({"error": "invalid_transition", "detail": str(exc)}), 409
        except sqlite3.Error:
            return jsonify({"error": "audit_log_unavailable"}), 500

        status_code = 200 if updated["status"] == "published" else 502
        return jsonify({"request": updated}), status_code
