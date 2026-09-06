import json
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    source_type TEXT NOT NULL,
    analyst_id TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL,
    analysis TEXT,
    draft_solution TEXT
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(requests)")}
    if "draft_solution" not in existing_columns:
        conn.execute("ALTER TABLE requests ADD COLUMN draft_solution TEXT")


def row_to_request(row: sqlite3.Row) -> dict:
    record = {
        "request_id": row["request_id"],
        "text": row["text"],
        "source_type": row["source_type"],
        "analyst_id": row["analyst_id"],
        "submitted_at": row["submitted_at"],
        "status": row["status"],
    }
    if row["analysis"] is not None:
        record["analysis"] = json.loads(row["analysis"])
    if row["draft_solution"] is not None:
        record["draft_solution"] = json.loads(row["draft_solution"])
    return record


def fetch_request(db_path: str, request_id: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM requests WHERE request_id = ?", (request_id,)
        ).fetchone()
    finally:
        conn.close()
    return row_to_request(row) if row is not None else None
