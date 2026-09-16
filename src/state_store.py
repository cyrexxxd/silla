"""Durable local state: idempotent upserts so re-running sync never duplicates data."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    canvas_course_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    local_folder_name TEXT NOT NULL,
    current_score_pct REAL,
    assignment_group_breakdown TEXT,
    last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    course_id INTEGER NOT NULL,
    course_name TEXT NOT NULL,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    due_at TEXT,
    points_possible REAL,
    submitted INTEGER,
    html_url TEXT
);

CREATE TABLE IF NOT EXISTS files (
    canvas_file_id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    course_name TEXT NOT NULL,
    filename TEXT NOT NULL,
    canvas_updated_at TEXT,
    size_bytes INTEGER,
    folder_path TEXT,
    local_path TEXT,
    canvas_url TEXT,
    preview_path TEXT
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    courses_synced INTEGER,
    assignments_synced INTEGER,
    files_downloaded INTEGER,
    errors TEXT
);
"""


@contextmanager
def connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_course(conn, *, canvas_course_id, name, local_folder_name,
                   current_score_pct, assignment_group_breakdown):
    conn.execute(
        """
        INSERT INTO courses (canvas_course_id, name, local_folder_name,
                              current_score_pct, assignment_group_breakdown, last_synced_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(canvas_course_id) DO UPDATE SET
            name=excluded.name,
            local_folder_name=excluded.local_folder_name,
            current_score_pct=excluded.current_score_pct,
            assignment_group_breakdown=excluded.assignment_group_breakdown,
            last_synced_at=excluded.last_synced_at
        """,
        (
            canvas_course_id,
            name,
            local_folder_name,
            current_score_pct,
            json.dumps(assignment_group_breakdown),
            now_iso(),
        ),
    )


def upsert_calendar_event(conn, *, event_id, course_id, course_name, title,
                           type_, due_at, points_possible, submitted, html_url):
    conn.execute(
        """
        INSERT INTO calendar_events (id, course_id, course_name, title, type,
                                      due_at, points_possible, submitted, html_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            course_name=excluded.course_name,
            title=excluded.title,
            type=excluded.type,
            due_at=excluded.due_at,
            points_possible=excluded.points_possible,
            submitted=excluded.submitted,
            html_url=excluded.html_url
        """,
        (
            event_id, course_id, course_name, title, type_,
            due_at, points_possible, int(bool(submitted)), html_url,
        ),
    )


def upsert_file(conn, *, canvas_file_id, course_id, course_name, filename,
                 canvas_updated_at, size_bytes, folder_path, local_path, canvas_url,
                 preview_path=None):
    conn.execute(
        """
        INSERT INTO files (canvas_file_id, course_id, course_name, filename,
                            canvas_updated_at, size_bytes, folder_path, local_path, canvas_url,
                            preview_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(canvas_file_id) DO UPDATE SET
            course_name=excluded.course_name,
            filename=excluded.filename,
            canvas_updated_at=excluded.canvas_updated_at,
            size_bytes=excluded.size_bytes,
            folder_path=excluded.folder_path,
            local_path=excluded.local_path,
            canvas_url=excluded.canvas_url,
            preview_path=excluded.preview_path
        """,
        (
            canvas_file_id, course_id, course_name, filename,
            canvas_updated_at, size_bytes, folder_path, local_path, canvas_url,
            preview_path,
        ),
    )


def get_known_file(conn, canvas_file_id) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM files WHERE canvas_file_id = ?", (canvas_file_id,)
    ).fetchone()


def start_sync_log(conn) -> int:
    cur = conn.execute(
        "INSERT INTO sync_log (started_at) VALUES (?)", (now_iso(),)
    )
    return cur.lastrowid


def finish_sync_log(conn, log_id, *, courses_synced, assignments_synced,
                     files_downloaded, errors):
    conn.execute(
        """
        UPDATE sync_log SET finished_at=?, courses_synced=?, assignments_synced=?,
                             files_downloaded=?, errors=?
        WHERE id=?
        """,
        (
            now_iso(), courses_synced, assignments_synced, files_downloaded,
            json.dumps(errors), log_id,
        ),
    )


def all_courses(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM courses ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["assignment_group_breakdown"] = json.loads(d["assignment_group_breakdown"] or "[]")
        out.append(d)
    return out


def all_calendar_events(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM calendar_events ORDER BY due_at IS NULL, due_at"
    ).fetchall()
    return [dict(r) for r in rows]


def all_files(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM files ORDER BY course_name, folder_path, filename"
    ).fetchall()
    return [dict(r) for r in rows]


def latest_sync_meta(conn) -> dict:
    row = conn.execute(
        "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return {}
    d = dict(row)
    d["errors"] = json.loads(d["errors"] or "[]")
    return d
