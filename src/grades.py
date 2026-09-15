"""Assignment-group weighted grade calculations (the syllabus percentage breakdown)."""


def course_current_score(course) -> float | None:
    """Canvas's own computed current-grade % for the logged-in user, if available."""
    enrollments = getattr(course, "enrollments", None)
    if not enrollments:
        return None
    return enrollments[0].get("computed_current_score")


def _group_earned_and_possible(assignments) -> tuple[float, float]:
    earned = 0.0
    possible = 0.0
    for a in assignments:
        points_possible = getattr(a, "points_possible", None) or 0
        submission = getattr(a, "submission", None)
        score = submission.get("score") if submission else None
        if score is None:
            continue
        earned += score
        possible += points_possible
    return earned, possible


def assignment_group_breakdown(canvas_client_with_retry, course) -> list[dict]:
    """Reconstruct the weighted per-group breakdown (e.g. Quizzes 20%, Homework 30%...)."""
    groups = list(
        canvas_client_with_retry(
            course.get_assignment_groups,
            include=["assignments", "submission"],
        )
    )
    breakdown = []
    for group in groups:
        weight = getattr(group, "group_weight", None)
        assignments = getattr(group, "assignments", []) or []
        earned, possible = _group_earned_and_possible(assignments)
        group_score_pct = round(100 * earned / possible, 1) if possible else None
        breakdown.append(
            {
                "group_name": group.name,
                "weight_pct": weight,
                "group_score_pct": group_score_pct,
                "graded_assignment_count": sum(
                    1
                    for a in assignments
                    if (getattr(a, "submission", None) or {}).get("score") is not None
                ),
                "total_assignment_count": len(assignments),
            }
        )
    return breakdown
