"""Orchestrator: python -m src.sync

Idempotent — safe to re-run any number of times per day. Talks to Canvas, computes
grades/calendar, downloads files, writes state/canvas.sqlite3 and artifact_payload/latest.json.
"""
import sys

from . import artifact_export, calendar_build, canvas_client, config, files_sync, grades, html_export, state_store


def sync_course(conn, canvas, course, window_end, errors: list) -> tuple[int, int]:
    """Returns (assignments_synced, files_downloaded) for one course."""
    assignments_synced = 0
    files_downloaded = 0

    try:
        breakdown = grades.assignment_group_breakdown(canvas_client.with_retry, course)
    except Exception as exc:
        errors.append(f"course {course.id} ({course.name}): assignment_groups failed: {exc!r}")
        breakdown = []

    current_score = grades.course_current_score(course)
    folder_name = files_sync.local_folder_for_course(course.id, course.name)
    state_store.upsert_course(
        conn,
        canvas_course_id=course.id,
        name=course.name,
        local_folder_name=folder_name,
        current_score_pct=current_score,
        assignment_group_breakdown=breakdown,
    )

    try:
        assignments = list(
            canvas_client.with_retry(course.get_assignments, order_by="due_at", per_page=100)
        )
    except Exception as exc:
        errors.append(f"course {course.id} ({course.name}): assignments failed: {exc!r}")
        assignments = []

    for event in calendar_build.build_events_from_assignments(course, assignments, window_end):
        state_store.upsert_calendar_event(conn, **_event_kwargs(event))
        assignments_synced += 1

    try:
        from datetime import datetime, timezone
        import itertools

        cal_events = list(
            itertools.islice(
                canvas_client.with_retry(
                    canvas.get_calendar_events,
                    context_codes=[f"course_{course.id}"],
                    start_date=datetime.now(timezone.utc).date().isoformat(),
                    end_date=window_end.date().isoformat(),
                    per_page=100,
                ),
                500,  # safety cap: never let an unbounded/misbehaving query hang the sync
            )
        )
    except Exception as exc:
        errors.append(f"course {course.id} ({course.name}): calendar_events failed: {exc!r}")
        cal_events = []

    for event in calendar_build.build_events_from_calendar(course, cal_events):
        state_store.upsert_calendar_event(conn, **_event_kwargs(event))

    try:
        synced_root, _ = files_sync.synced_root_for_course(course.id, course.name)
        files_downloaded = files_sync.sync_course_files(
            canvas_client.with_retry, conn, course, synced_root, errors
        )
    except Exception as exc:
        errors.append(f"course {course.id} ({course.name}): files failed: {exc!r}")

    return assignments_synced, files_downloaded


def _event_kwargs(event: dict) -> dict:
    return {
        "event_id": event["event_id"],
        "course_id": event["course_id"],
        "course_name": event["course_name"],
        "title": event["title"],
        "type_": event["type"],
        "due_at": event["due_at"],
        "points_possible": event["points_possible"],
        "submitted": event["submitted"],
        "html_url": event["html_url"],
    }


def main():
    canvas = canvas_client.get_canvas()
    window_end = calendar_build.sync_window_end(config.SYNC_WINDOW_DAYS)
    errors: list[str] = []

    with state_store.connect(config.STATE_DB_PATH) as conn:
        log_id = state_store.start_sync_log(conn)

        courses = canvas_client.active_courses(canvas)

        total_assignments = 0
        total_files = 0
        for course in courses:
            a_count, f_count = sync_course(conn, canvas, course, window_end, errors)
            total_assignments += a_count
            total_files += f_count
            print(f"[{course.id}] {course.name}: {a_count} calendar items, {f_count} files downloaded")

        state_store.finish_sync_log(
            conn,
            log_id,
            courses_synced=len(courses),
            assignments_synced=total_assignments,
            files_downloaded=total_files,
            errors=errors,
        )

        artifact_export.write_payload(conn)
        dashboard_path = html_export.write_dashboard(conn)

    print(f"\nSynced {len(courses)} courses, {total_assignments} calendar items, {total_files} files downloaded.")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    print(f"\nDashboard: {dashboard_path}")
    print(f"(raw data for the optional Claude/Artifact flow: {config.ARTIFACT_PAYLOAD_PATH})")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
