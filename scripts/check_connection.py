"""Milestone 1: confirm Canvas auth + course/assignment fetch works. No storage yet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import canvas_client, config


def main():
    print(f"Base URL: {config.CANVAS_BASE_URL}")
    canvas = canvas_client.get_canvas()

    try:
        user = canvas_client.with_retry(canvas.get_current_user)
        print(f"Authenticated as: {user}")
    except Exception as exc:
        print(f"AUTH FAILED: {exc!r}")
        sys.exit(1)

    courses = canvas_client.active_courses(canvas)
    print(f"\nActive courses: {len(courses)}")
    for course in courses:
        name = getattr(course, "name", "?")
        course_id = getattr(course, "id", "?")
        score = getattr(course, "enrollments", None)
        current_score = None
        if score:
            current_score = score[0].get("computed_current_score")
        print(f"  [{course_id}] {name} — current score: {current_score}")

        try:
            assignments = list(
                canvas_client.with_retry(
                    course.get_assignments, order_by="due_at", per_page=100
                )
            )
        except Exception as exc:
            print(f"      could not fetch assignments: {exc!r}")
            continue

        print(f"      assignments: {len(assignments)}")
        quiz_types = set()
        for a in assignments[:5]:
            due = getattr(a, "due_at", None)
            subs = getattr(a, "submission_types", [])
            quiz_types.update(subs)
            print(f"      - {a.name!r} due={due} types={subs}")
        if quiz_types:
            print(f"      submission_types seen (first 5): {sorted(quiz_types)}")


if __name__ == "__main__":
    main()
