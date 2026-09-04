"""
requirement_clarification_routes.py

Registers the requirement-clarification HTTP endpoint on the Flask app.
Split out of app.py (at this repo's 200-line cap -- see CLAUDE.md) to make
room for STORY-005's design-recommendation route wiring; STORY-004 hit the
same limit and split field_mapping_routes.py out for the same reason.
Behavior is unchanged from the original inline route in app.py.
"""

from flask import Flask, jsonify, request

from src.request_intake import RequestIntake
from src.requirement_clarification import (
    CLARIFICATION_NOT_NEEDED,
    CLARIFICATION_QUESTIONS_GENERATED,
    RequirementClarificationError,
    generate_followup_questions,
)


def register_requirement_clarification_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/clarify")
    def clarify_request(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.get_request(request_id)
        if record is None:
            return jsonify({"error": "request_not_found"}), 404

        analysis = record.get("analysis")
        if analysis is None:
            return jsonify({"error": "no_analysis_available"}), 400

        try:
            questions = generate_followup_questions(analysis)
        except RequirementClarificationError:
            return jsonify({"error": "invalid_analysis"}), 400

        event = CLARIFICATION_QUESTIONS_GENERATED if questions else CLARIFICATION_NOT_NEEDED
        store.record_clarification(request_id=request_id, analyst_id=analyst_id, event=event)

        return jsonify({"request_id": request_id, "questions": questions}), 200
