"""
stakeholder_review_routes.py

Registers the STORY-008 stakeholder-review HTTP endpoints on the Flask app.
Kept out of app.py (at this repo's 200-line cap -- see CLAUDE.md) and out of
stakeholder_review.py itself (that module owns transition/persistence
logic, not HTTP wiring) -- same split rationale as every other *_routes.py
module in this pipeline.

Two endpoints:
- POST /requests/<id>/submit-for-review -- persists a draft solution and
  moves the request to in_review. Together with GET /requests/<id>
  (src/app.py), which already returns the full record -- including
  draft_solution once this endpoint has stored it -- this satisfies
  REQ-013's "stakeholders can access it" criterion. No separate read
  endpoint is needed.
- POST /requests/<id>/review -- the stakeholder's decision:
  action=approve or action=request_changes. This is the only path in this
  system that can set status to approved -- REQ-012 requires a human in
  this loop, and no AI-calling code in this pipeline ever reaches this
  endpoint on its own. request_changes requires non-empty feedback,
  logged in the audit trail (STORY-008's second criterion); approve logs
  the approver's ID and timestamp via the normal audit entry fields (the
  trust criterion).

Every outcome writes one audit entry via StakeholderReview's own methods,
which already call AuditTrail.append() internally -- no separate
_record_audit_event() wrapper is needed here the way the AI-generation
routes need one: there's no AI call whose success/failure needs a
distinct audit path, and an illegal transition here is a controlled 409,
not a "model failed" case.
"""

from flask import Flask, jsonify, request

from src.lifecycle import InvalidTransitionError
from src.request_intake import RequestIntake
from src.stakeholder_review import StakeholderReview

_VALID_ACTIONS = ("approve", "request_changes")


def register_stakeholder_review_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/submit-for-review")
    def submit_for_review(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")
        draft_solution = payload.get("draft_solution")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400
        if not isinstance(draft_solution, dict):
            return jsonify({"error": "draft_solution is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        if store.get_request(request_id) is None:
            return jsonify({"error": "request_not_found"}), 404

        review: StakeholderReview = app.config["STAKEHOLDER_REVIEW"]
        try:
            updated = review.submit_draft_for_review(
                request_id=request_id, analyst_id=analyst_id, draft_solution=draft_solution
            )
        except InvalidTransitionError as exc:
            return jsonify({"error": "invalid_transition", "detail": str(exc)}), 409

        return jsonify(updated), 201

    @app.post("/requests/<request_id>/review")
    def review_draft(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")
        action = payload.get("action")
        feedback = payload.get("feedback")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400
        if action not in _VALID_ACTIONS:
            return jsonify({"error": "action must be one of: approve, request_changes"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        if store.get_request(request_id) is None:
            return jsonify({"error": "request_not_found"}), 404

        review: StakeholderReview = app.config["STAKEHOLDER_REVIEW"]
        try:
            if action == "approve":
                updated = review.approve(request_id=request_id, analyst_id=analyst_id)
            else:
                if not feedback:
                    return jsonify({"error": "feedback is required to request changes"}), 400
                updated = review.request_changes(
                    request_id=request_id, analyst_id=analyst_id, feedback=feedback
                )
        except InvalidTransitionError as exc:
            return jsonify({"error": "invalid_transition", "detail": str(exc)}), 409

        return jsonify(updated), 200
