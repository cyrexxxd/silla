"""Render a fully self-contained local dashboard.html — no Claude, no subscription, no
network calls except the (optional) Google Fonts stylesheet. Just Python + a browser.
"""
import json

from . import config, state_store

TEMPLATE_PATH = config.PROJECT_ROOT / "templates" / "dashboard_template.html"
OUTPUT_PATH = config.PROJECT_ROOT / "dashboard.html"


def _group_files_by_course(files: list[dict]) -> dict:
    grouped: dict[str, dict] = {}
    for f in files:
        cid = str(f["course_id"])
        entry = grouped.setdefault(cid, {"course_name": f["course_name"], "files": []})
        entry["files"].append(
            {
                "filename": f["filename"],
                "size_bytes": f["size_bytes"],
                "folder_path": f["folder_path"],
                "canvas_url": f["canvas_url"],
            }
        )
    return grouped


def build_payload(conn) -> dict:
    courses = [
        {
            "id": c["canvas_course_id"],
            "name": c["name"],
            "current_score_pct": c["current_score_pct"],
            "assignment_group_breakdown": c["assignment_group_breakdown"],
            "last_synced_at": c["last_synced_at"],
        }
        for c in state_store.all_courses(conn)
    ]
    raw_meta = state_store.latest_sync_meta(conn)
    meta = {
        "last_sync_at": raw_meta.get("finished_at") or raw_meta.get("started_at"),
        "courses_synced": raw_meta.get("courses_synced"),
        "assignments_synced": raw_meta.get("assignments_synced"),
        "files_downloaded": raw_meta.get("files_downloaded"),
        "errors": raw_meta.get("errors") or [],
    }
    return {
        "courses": courses,
        "events": state_store.all_calendar_events(conn),
        "filesByCourse": _group_files_by_course(state_store.all_files(conn)),
        "meta": meta,
    }


def write_dashboard(conn):
    payload = build_payload(conn)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</script>", "<\\/script>")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = template.replace("__DASHBOARD_DATA__", data_json)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    return OUTPUT_PATH
