"""T-65 / T-66: Faculty review of sponsor projects and sharing with courses.

Every decision is a single conditional UPDATE that only succeeds while the
project is still 'pending', so a project can never be reviewed twice, even if
two faculty members click at the same moment. The status change and its
history row are written in the same transaction: either both are saved or
neither is.

T-66: accepting a project requires choosing at least one of the faculty
member's own courses. Students enrolled in those courses can then see it.
Sharing can be changed later, but only for accepted projects and only to
courses the faculty member owns.
"""

import logging
from collections.abc import Mapping
from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import _transaction, _validate_user_id


NOTES_MAX_CHARS = 2000
MAX_SHARED_COURSES = 50

# action -> (new project status, are notes required?)
REVIEW_ACTIONS: dict[str, tuple[str, bool]] = {
    "accept": ("accepted", False),
    "request_revision": ("revision_requested", True),
    "reject": ("rejected", True),
}

_NOTES_REQUIRED_MESSAGES = {
    "request_revision": "Write what the sponsor needs to change.",
    "reject": "A reason is required to reject a project.",
}

STATUS_LABELS = {
    "pending": "Pending review",
    "revision_requested": "Changes requested",
    "accepted": "Accepted",
    "rejected": "Rejected",
}

ACTION_LABELS = {
    "accepted": "Accepted",
    "revision_requested": "Requested changes",
    "rejected": "Rejected",
    "resubmitted": "Resubmitted by sponsor",
}


class SharedCourse(TypedDict):
    id: str
    label: str


class ReviewEntry(TypedDict):
    action: str
    label: str
    notes: str
    reviewer: str
    created_at: str


def _validate_project_id(project_id: int) -> None:
    if (
        isinstance(project_id, bool)
        or not isinstance(project_id, int)
        or not 0 < project_id <= 9223372036854775807
    ):
        raise ValueError("Invalid project.")


def _clean_notes(notes: str | None, action: str) -> str | None:
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ValueError("Notes must be text.")
    if "\x00" in notes:
        raise ValueError("Notes must not contain null characters.")
    notes = notes.strip()
    if not notes and action in _NOTES_REQUIRED_MESSAGES:
        raise ValueError(_NOTES_REQUIRED_MESSAGES[action])
    if len(notes) > NOTES_MAX_CHARS:
        raise ValueError(
            f"Notes must be {NOTES_MAX_CHARS} characters or fewer."
        )
    return notes or None


def _clean_course_ids(course_ids) -> list[int]:
    """Validate the chosen course ids; at least one is required."""
    if course_ids is None or not isinstance(course_ids, (list, tuple)):
        course_ids = []
    cleaned: list[int] = []
    for value in course_ids:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 < value <= 9223372036854775807
        ):
            raise ValueError("Invalid course selection.")
        if value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        raise ValueError("Pick at least one course to share this project with.")
    if len(cleaned) > MAX_SHARED_COURSES:
        raise ValueError(
            f"Share with at most {MAX_SHARED_COURSES} courses at a time."
        )
    return cleaned


def _require_active_faculty(session, faculty_id: int, message: str) -> None:
    reviewer = session.execute(
        text(
            "SELECT role, status, must_change_password "
            "FROM public.users WHERE id = :id FOR UPDATE"
        ),
        {"id": faculty_id},
    ).first()
    if (
        reviewer is None
        or reviewer.role != "faculty"
        or reviewer.status != "active"
        or reviewer.must_change_password
    ):
        raise PermissionError(message)


def _share_with_courses(
    session, faculty_id: int, project_id: int, course_ids: list[int]
) -> None:
    """Replace this faculty member's shares for the project.

    Shares made by other faculty (to their own courses) are left alone.
    """
    owned = {
        int(row.id)
        for row in session.execute(
            text(
                "SELECT id FROM public.courses "
                "WHERE faculty_id = :faculty_id AND id = ANY(:course_ids)"
            ),
            {"faculty_id": faculty_id, "course_ids": course_ids},
        ).all()
    }
    if owned != set(course_ids):
        raise PermissionError("You can only share projects with your own courses.")

    session.execute(
        text(
            "DELETE FROM public.project_course_visibility "
            "WHERE project_id = :project_id AND course_id IN "
            "(SELECT id FROM public.courses WHERE faculty_id = :faculty_id)"
        ),
        {"project_id": project_id, "faculty_id": faculty_id},
    )
    session.execute(
        text(
            "INSERT INTO public.project_course_visibility "
            "(project_id, course_id, shared_by) "
            "VALUES (:project_id, :course_id, :shared_by)"
        ),
        [
            {
                "project_id": project_id,
                "course_id": course_id,
                "shared_by": faculty_id,
            }
            for course_id in course_ids
        ],
    )


def review_project(
    faculty_id: int,
    project_id: int,
    action: str,
    notes: str | None = "",
    course_ids: list[int] | None = None,
) -> str:
    """Apply one review decision and return the project's new status.

    Accepting requires course_ids: at least one of the faculty member's own
    courses to share the project with. Other actions ignore course_ids.

    Raises PermissionError if the caller is not an active faculty member (or
    picks a course they don't own), and ValueError for bad input or a project
    that is no longer pending. Nothing is saved when an error is raised.
    """
    _validate_user_id(faculty_id)
    _validate_project_id(project_id)

    if action not in REVIEW_ACTIONS:
        raise ValueError("Choose a valid review decision.")

    new_status, _ = REVIEW_ACTIONS[action]
    cleaned_notes = _clean_notes(notes, action)
    cleaned_courses = (
        _clean_course_ids(course_ids) if action == "accept" else []
    )

    with _transaction() as session:
        _require_active_faculty(
            session, faculty_id, "Only active faculty can review projects."
        )

        updated = session.execute(
            text(
                "UPDATE public.projects SET status = :new_status "
                "WHERE id = :project_id AND status = 'pending' "
                "RETURNING id"
            ),
            {"new_status": new_status, "project_id": project_id},
        ).first()

        if updated is None:
            raise ValueError(
                "This project is no longer pending review. "
                "Refresh the page to see its current status."
            )

        if cleaned_courses:
            _share_with_courses(session, faculty_id, project_id, cleaned_courses)

        session.execute(
            text(
                "INSERT INTO public.project_reviews "
                "(project_id, actor_id, action, notes) "
                "VALUES (:project_id, :actor_id, :action, :notes)"
            ),
            {
                "project_id": project_id,
                "actor_id": faculty_id,
                "action": new_status,
                "notes": cleaned_notes,
            },
        )

    return new_status


def set_project_courses(
    faculty_id: int, project_id: int, course_ids: list[int]
) -> None:
    """Change which of this faculty member's courses can see an accepted project."""
    _validate_user_id(faculty_id)
    _validate_project_id(project_id)
    cleaned_courses = _clean_course_ids(course_ids)

    with _transaction() as session:
        _require_active_faculty(
            session, faculty_id, "Only active faculty can share projects."
        )
        project = session.execute(
            text(
                "SELECT status FROM public.projects "
                "WHERE id = :project_id FOR UPDATE"
            ),
            {"project_id": project_id},
        ).first()
        if project is None:
            raise ValueError("Project not found.")
        if project.status != "accepted":
            raise ValueError("Only accepted projects can be shared with courses.")

        _share_with_courses(session, faculty_id, project_id, cleaned_courses)


def list_project_courses(project_id: int) -> list[SharedCourse]:
    """Courses an accepted project is shared with, for display."""
    _validate_project_id(project_id)

    try:
        with _transaction() as session:
            rows = session.execute(
                text(
                    "SELECT DISTINCT c.id, c.code, c.name, c.term "
                    "FROM public.project_course_visibility AS v "
                    "JOIN public.courses AS c ON c.id = v.course_id "
                    "WHERE v.project_id = :project_id "
                    "ORDER BY c.code, c.term, c.id"
                ),
                {"project_id": project_id},
            ).mappings().all()

        return [course_option(row) for row in rows]

    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


def course_option(row) -> SharedCourse:
    """Turn a course row (dict or object) into an id + display label."""
    get = (
        (lambda key: row[key])
        if isinstance(row, Mapping)
        else (lambda key: getattr(row, key))
    )
    code = str(get("code")).strip()
    name = str(get("name")).strip()
    term = str(get("term")).strip()
    return SharedCourse(
        id=str(get("id")),
        label=f"{code} · {name} ({term})",
    )


def list_review_history(project_id: int) -> list[ReviewEntry]:
    """Return a project's review history, newest first."""
    _validate_project_id(project_id)

    try:
        with _transaction() as session:
            rows = session.execute(
                text(
                    "SELECT r.action, r.notes, r.created_at, "
                    "u.full_name AS reviewer "
                    "FROM public.project_reviews AS r "
                    "JOIN public.users AS u ON u.id = r.actor_id "
                    "WHERE r.project_id = :project_id "
                    "ORDER BY r.created_at DESC"
                ),
                {"project_id": project_id},
            ).mappings().all()

        return [
            ReviewEntry(
                action=str(row["action"]),
                label=ACTION_LABELS.get(
                    str(row["action"]), str(row["action"])
                ),
                notes=str(row["notes"] or ""),
                reviewer=str(row["reviewer"]),
                created_at=row["created_at"].strftime("%b %d, %Y %I:%M %p"),
            )
            for row in rows
        ]

    except Exception as e:
        logging.exception(f"Error: {e}")
        raise
