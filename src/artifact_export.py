"""Render local SQLite state into the exact JSON shape the Artifact DB collections expect.

Only derived, non-secret data goes in here: names, dates, percentages, filenames, local
paths. The Canvas API token must never appear in this file.
"""
import json

from . import config, state_store


def build_payload(conn) -> dict:
    raw_meta = state_store.latest_sync_meta(conn)
    sync_meta = {
        "last_sync_at": raw_meta.get("finished_at") or raw_meta.get("started_at"),
        "courses_synced": raw_meta.get("courses_synced"),
        "assignments_synced": raw_meta.get("assignments_synced"),
        "files_downloaded": raw_meta.get("files_downloaded"),
        "errors": raw_meta.get("errors") or [],
    }
    return {
        "courses": state_store.all_courses(conn),
        "calendar_events": state_store.all_calendar_events(conn),
        "files": state_store.all_files(conn),
        "sync_meta": sync_meta,
    }


def write_payload(conn):
    payload = build_payload(conn)
    config.ARTIFACT_PAYLOAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.ARTIFACT_PAYLOAD_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )
    return payload
