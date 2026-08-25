import os
import tempfile

from flask import Flask, jsonify, request

from src.email_analysis import (
    EmailAnalysisError,
    InvalidEmailAnalysisResponseError,
    analyze_email,
)
from src.excel_analysis import (
    CorruptExcelFileError,
    UnsupportedExcelFormatError,
    analyze_report,
)
from src.request_intake import RequestIntake

_ANALYSIS_FAILURE_CATEGORIES = {
    CorruptExcelFileError: "corrupt_excel",
    UnsupportedExcelFormatError: "unsupported_format",
}


def create_app(db_path: str | None = None, email_client=None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    if db_path is None:
        db_path = os.path.join(app.instance_path, "powerbi_blueprint.db")

    app.config["REQUEST_STORE"] = RequestIntake(db_path)
    app.config["EMAIL_ANALYSIS_CLIENT"] = email_client

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/version")
    def version():
        return {"version": "0.1.0"}

    @app.post("/requests")
    def submit_request():
        payload = request.get_json(silent=True) or {}
        text = payload.get("text")
        source_type = payload.get("source_type")
        analyst_id = payload.get("analyst_id")

        if not text or not source_type or not analyst_id:
            return jsonify({"error": "text, source_type, and analyst_id are required"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.submit_request(text=text, source_type=source_type, analyst_id=analyst_id)

        if source_type != "email":
            return jsonify(record), 201

        email_client = app.config.get("EMAIL_ANALYSIS_CLIENT")
        try:
            analysis = analyze_email(text, client=email_client)
        except InvalidEmailAnalysisResponseError:
            error_category = "invalid_model_response"
        except EmailAnalysisError:
            error_category = "email_analysis_unavailable"
        else:
            updated = store.complete_analysis(
                request_id=record["request_id"], analyst_id=analyst_id, analysis=analysis
            )
            return jsonify(updated), 201

        store.fail_analysis(
            request_id=record["request_id"], analyst_id=analyst_id, error_category=error_category
        )
        return jsonify({"error": error_category, "request_id": record["request_id"]}), 400

    @app.post("/requests/excel")
    def submit_excel_request():
        analyst_id = request.form.get("analyst_id")
        uploaded_file = request.files.get("file")

        if not analyst_id or not uploaded_file or not uploaded_file.filename:
            return jsonify({"error": "file and analyst_id are required"}), 400

        filename = uploaded_file.filename
        if not filename.lower().endswith((".xlsx", ".xlsm")):
            return jsonify({"error": f"Unsupported file format: {filename}"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.submit_request(text=filename, source_type="excel", analyst_id=analyst_id)

        suffix = os.path.splitext(filename)[1]
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            uploaded_file.save(tmp_path)
            analysis = analyze_report(tmp_path)
        except (CorruptExcelFileError, UnsupportedExcelFormatError) as exc:
            error_category = _ANALYSIS_FAILURE_CATEGORIES[type(exc)]
            store.fail_analysis(
                request_id=record["request_id"], analyst_id=analyst_id, error_category=error_category
            )
            return jsonify({"error": error_category, "request_id": record["request_id"]}), 400
        finally:
            os.remove(tmp_path)

        updated = store.complete_analysis(
            request_id=record["request_id"], analyst_id=analyst_id, analysis=analysis
        )
        return (
            jsonify(
                {
                    "request_id": updated["request_id"],
                    "status": updated["status"],
                    "analysis": updated["analysis"],
                }
            ),
            201,
        )

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
