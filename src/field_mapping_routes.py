"""
field_mapping_routes.py

Registers the field-mapping HTTP endpoint on the Flask app. Kept out of
app.py (which was already at 197 of this repo's 200-line cap -- see
CLAUDE.md) rather than adding the route inline; STORY-003 hit the same
limit in request_intake.py and split audit_trail.py out for the same reason.

Mirrors app.py's submit_excel_request(): validate presence, reject an
unsupported extension before creating any request record, then create the
request and only mark it failed if the saved file itself turns out corrupt.
"""

import os
import tempfile

from flask import Flask, jsonify, request

from src.field_mapping import (
    CorruptReportFileError,
    UnsupportedReportFormatError,
    map_fields,
    read_report_headers,
)
from src.request_intake import RequestIntake

_MAPPING_FAILURE_CATEGORIES = {
    CorruptReportFileError: "corrupt_report",
}


def register_field_mapping_routes(app: Flask) -> None:
    @app.post("/requests/field-mapping")
    def submit_field_mapping_request():
        analyst_id = request.form.get("analyst_id")
        uploaded_file = request.files.get("file")

        if not analyst_id or not uploaded_file or not uploaded_file.filename:
            return jsonify({"error": "file and analyst_id are required"}), 400

        filename = uploaded_file.filename
        if not filename.lower().endswith((".xlsx", ".xlsm", ".csv")):
            return jsonify({"error": f"Unsupported file format: {filename}"}), 400

        store: RequestIntake = app.config["REQUEST_STORE"]
        record = store.submit_request(text=filename, source_type="excel", analyst_id=analyst_id)

        suffix = os.path.splitext(filename)[1]
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            uploaded_file.save(tmp_path)
            headers = read_report_headers(tmp_path)
        except (CorruptReportFileError, UnsupportedReportFormatError) as exc:
            error_category = _MAPPING_FAILURE_CATEGORIES.get(type(exc), "corrupt_report")
            store.record_clarification(
                request_id=record["request_id"],
                analyst_id=analyst_id,
                event="field_mapping_failed",
                error_category=error_category,
            )
            return jsonify({"error": error_category, "request_id": record["request_id"]}), 400
        finally:
            os.remove(tmp_path)

        mapping = map_fields(headers)
        mapped = {header: column for header, column in mapping.items() if column is not None}
        flagged = [header for header, column in mapping.items() if column is None]

        store.record_clarification(
            request_id=record["request_id"], analyst_id=analyst_id, event="field_mapping_completed"
        )

        return jsonify({"request_id": record["request_id"], "mapped": mapped, "flagged": flagged}), 201
