import sqlite3

from src.request_schema import ensure_schema, fetch_request, row_to_request


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_ensure_schema_creates_requests_table_with_draft_solution_column(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)

    with conn:
        ensure_schema(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(requests)")}
    conn.close()

    assert "draft_solution" in columns
    assert "status" in columns


def test_ensure_schema_migrates_an_existing_table_missing_draft_solution(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)

    with conn:
        conn.executescript(
            """
            CREATE TABLE requests (
                request_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                source_type TEXT NOT NULL,
                analyst_id TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL,
                analysis TEXT
            );
            """
        )
        conn.execute(
            "INSERT INTO requests "
            "(request_id, text, source_type, analyst_id, submitted_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("req-1", "Need a report", "email", "analyst-1", "2026-01-01T00:00:00+00:00", "analyzed"),
        )

    with conn:
        ensure_schema(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(requests)")}
    row = conn.execute("SELECT * FROM requests WHERE request_id = ?", ("req-1",)).fetchone()
    conn.close()

    assert "draft_solution" in columns
    assert row["draft_solution"] is None
    assert row["text"] == "Need a report"


def test_ensure_schema_is_idempotent_when_called_twice(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)

    with conn:
        ensure_schema(conn)
        ensure_schema(conn)
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(requests)")]
    conn.close()

    assert columns.count("draft_solution") == 1


def test_row_to_request_omits_analysis_and_draft_solution_when_absent(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)

    with conn:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO requests "
            "(request_id, text, source_type, analyst_id, submitted_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("req-1", "Need a report", "email", "analyst-1", "2026-01-01T00:00:00+00:00", "intake"),
        )
    row = conn.execute("SELECT * FROM requests WHERE request_id = ?", ("req-1",)).fetchone()
    conn.close()

    record = row_to_request(row)

    assert record["request_id"] == "req-1"
    assert "analysis" not in record
    assert "draft_solution" not in record


def test_row_to_request_decodes_analysis_and_draft_solution_json_when_present(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)

    with conn:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO requests "
            "(request_id, text, source_type, analyst_id, submitted_at, status, analysis, draft_solution) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "req-1",
                "Need a report",
                "email",
                "analyst-1",
                "2026-01-01T00:00:00+00:00",
                "in_review",
                '{"kpis": ["Revenue"]}',
                '{"pages": []}',
            ),
        )
    row = conn.execute("SELECT * FROM requests WHERE request_id = ?", ("req-1",)).fetchone()
    conn.close()

    record = row_to_request(row)

    assert record["analysis"] == {"kpis": ["Revenue"]}
    assert record["draft_solution"] == {"pages": []}


def test_fetch_request_returns_none_for_unknown_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)
    with conn:
        ensure_schema(conn)
    conn.close()

    assert fetch_request(db_path, "does-not-exist") is None


def test_fetch_request_returns_decoded_record_for_known_request_id(tmp_path):
    db_path = str(tmp_path / "requests.db")
    conn = _connect(db_path)
    with conn:
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO requests "
            "(request_id, text, source_type, analyst_id, submitted_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("req-1", "Need a report", "email", "analyst-1", "2026-01-01T00:00:00+00:00", "intake"),
        )
    conn.close()

    record = fetch_request(db_path, "req-1")

    assert record["request_id"] == "req-1"
    assert record["status"] == "intake"
