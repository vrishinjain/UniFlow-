"""T-65: Faculty review of sponsor projects (accept / request revision / reject).

Every decision is a single conditional UPDATE that only succeeds while the
project is still 'pending', so a project can never be reviewed twice, even if
two faculty members click at the same moment. The status change and its
history row are written in the same transaction: either both are saved or
neither is.
"""

import logging
from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import _transaction, _validate_user_id


NOTES_MAX_CHARS = 2000

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


def review_project(
    faculty_id: int,
    project_id: int,
    action: str,
    notes: str | None = "",
) -> str:
    """Apply one review decision and return the project's new status.

    Raises PermissionError if the caller is not an active faculty member, and
    ValueError for bad input or a project that is no longer pending.
    Nothing is saved when an error is raised.
    """
    _validate_user_id(faculty_id)
    _validate_project_id(project_id)

    if action not in REVIEW_ACTIONS:
        raise ValueError("Choose a valid review decision.")

    new_status, _ = REVIEW_ACTIONS[action]
    cleaned_notes = _clean_notes(notes, action)

    with _transaction() as session:
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
            raise PermissionError("Only active faculty can review projects.")

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
