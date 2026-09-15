"""Merge assignments + calendar_events into one deduplicated upcoming list."""
from datetime import datetime, timedelta, timezone


def assignment_type(assignment) -> str:
    submission_types = getattr(assignment, "submission_types", []) or []
    name = (getattr(assignment, "name", "") or "").lower()
    if "quiz" in submission_types or "quiz" in name:
        return "quiz"
    if "external_tool" in submission_types and "quiz" in name:
        return "quiz"
    return "assignment"


def sync_window_end(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def build_events_from_assignments(course, assignments, window_end) -> list[dict]:
    events = []
    for a in assignments:
        due_at = getattr(a, "due_at", None)
        if due_at:
            due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if due_dt > window_end:
                continue
        submission = getattr(a, "submission", None)
        submitted = bool(submission and submission.get("workflow_state") not in (None, "unsubmitted"))
        events.append(
            {
                "event_id": f"assignment_{a.id}",
                "course_id": course.id,
                "course_name": course.name,
                "title": a.name,
                "type": assignment_type(a),
                "due_at": due_at,
                "points_possible": getattr(a, "points_possible", None),
                "submitted": submitted,
                "html_url": getattr(a, "html_url", None),
            }
        )
    return events


def build_events_from_calendar(course, calendar_events) -> list[dict]:
    events = []
    for e in calendar_events:
        events.append(
            {
                "event_id": f"calendar_{e.id}",
                "course_id": course.id,
                "course_name": course.name,
                "title": e.title,
                "type": "event",
                "due_at": getattr(e, "start_at", None),
                "points_possible": None,
                "submitted": False,
                "html_url": getattr(e, "html_url", None),
            }
        )
    return events
