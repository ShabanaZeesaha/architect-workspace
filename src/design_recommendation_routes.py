"""
design_recommendation_routes.py

Registers the design-recommendation HTTP endpoint on the Flask app. Kept
out of app.py (at this repo's 200-line cap -- see CLAUDE.md) and out of
design_recommendation.py itself (that module owns the AI call and
validation, not HTTP wiring) -- same split rationale as
field_mapping_routes.py and requirement_clarification_routes.py.

Every outcome -- missing data flagged, recommendations generated, or the
model failing/returning garbage -- writes one audit entry via
RequestIntake.record_clarification(), the same audit-only "record what
happened" pattern used by requirement clarification (STORY-003) and field
mapping (STORY-004), not a lifecycle status transition.
"""

from flask import Flask, jsonify, request

from src.design_recommendation import (
    DesignRecommendationError,
    IncompleteRequirementsError,
    InvalidDesignRecommendationResponseError,
    generate_design_recommendations,
)
from src.request_intake import RequestIntake

DESIGN_RECOMMENDATIONS_MISSING_DATA = "design_recommendations_missing_data"
DESIGN_RECOMMENDATIONS_GENERATED = "design_recommendations_generated"
DESIGN_RECOMMENDATIONS_FAILED = "design_recommendations_failed"


def register_design_recommendation_routes(app: Flask) -> None:
    @app.post("/requests/<request_id>/design-recommendations")
    def submit_design_recommendation_request(request_id):
        payload = request.get_json(silent=True) or {}
        analyst_id = payload.get("analyst_id")
        field_mapping = payload.get("field_mapping")

        if not analyst_id:
            return jsonify({"error": "analyst_id is required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.get_request(request_id)
        if record is None:
            return jsonify({"error": "request_not_found"}), 404

        analysis = record.get("analysis")
        if analysis is None:
            return jsonify({"error": "no_analysis_available"}), 400

        client = app.config.get("DESIGN_RECOMMENDATION_CLIENT")
        try:
            recommendations = generate_design_recommendations(
                analysis, field_mapping=field_mapping, client=client
            )
        except IncompleteRequirementsError as exc:
            store.record_clarification(
                request_id=request_id,
                analyst_id=analyst_id,
                event=DESIGN_RECOMMENDATIONS_MISSING_DATA,
                error_category=",".join(exc.missing_fields),
            )
            return (
                jsonify({"error": "incomplete_requirements", "missing_fields": exc.missing_fields}),
                400,
            )
        except InvalidDesignRecommendationResponseError:
            store.record_clarification(
                request_id=request_id,
                analyst_id=analyst_id,
                event=DESIGN_RECOMMENDATIONS_FAILED,
                error_category="invalid_model_response",
            )
            return jsonify({"error": "invalid_model_response"}), 400
        except DesignRecommendationError:
            store.record_clarification(
                request_id=request_id,
                analyst_id=analyst_id,
                event=DESIGN_RECOMMENDATIONS_FAILED,
                error_category="design_recommendation_unavailable",
            )
            return jsonify({"error": "design_recommendation_unavailable"}), 400

        store.record_clarification(
            request_id=request_id, analyst_id=analyst_id, event=DESIGN_RECOMMENDATIONS_GENERATED
        )
        return jsonify({"request_id": request_id, "recommendations": recommendations}), 201
