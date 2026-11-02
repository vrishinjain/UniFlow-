"""T-67: Sponsor side of the review flow.

A sponsor can see the review status of each of their projects and the
faculty's latest feedback. When faculty requested changes, the sponsor can
edit the title and description and resubmit, which puts the project back to
'pending' for faculty to review again.

Rules (all checked on the server):
- a sponsor only ever sees or changes their own projects;
- resubmitting only works while the project is 'revision_requested';
- the status change and its history row are saved together or not at all.
"""

import logging
from typing import TypedDict

from sqlalchemy import text

from UniFlow_.review_services import STATUS_LABELS, _validate_project_id
from UniFlow_.user_services import (
    _required_text,
    _transaction,
    _validate_user_id,
)


TITLE_MAX_CHARS = 200
DESCRIPTION_MAX_CHARS = 10000


class SponsorProjectDetail(TypedDict):
    id: str
    title: str
    description: str
    status: str
    status_label: str
    feedback: str
    can_resubmit: bool


def _clean_field(value: str, label: str, maximum: int) -> str:
    value = _required_text(value, label)
    if len(value) > maximum:
        raise ValueError(f"{label} must be {maximum} characters or fewer.")
    return value


def get_sponsor_project(
    sponsor_id: int, project_id: int
) -> SponsorProjectDetail | None:
    """Return one of the sponsor's own projects, or None if it isn't theirs."""
    _validate_user_id(sponsor_id)
    _validate_project_id(project_id)

    try:
        with _transaction() as session:
            project = session.execute(
                text(
                    "SELECT id, title, description, status "
                    "FROM public.projects "
                    "WHERE id = :project_id AND sponsor_id = :sponsor_id"
                ),
                {"project_id": project_id, "sponsor_id": sponsor_id},
            ).mappings().first()

            if project is None:
                return None

            # The latest faculty decision explains the current status.
            latest = session.execute(
                text(
                    "SELECT notes FROM public.project_reviews "
                    "WHERE project_id = :project_id "
                    "AND action IN ('accepted', 'revision_requested', 'rejected') "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"project_id": project_id},
            ).mappings().first()

        status = str(project["status"])
        return SponsorProjectDetail(
            id=str(project["id"]),
            title=str(project["title"]),
            description=str(project["description"] or ""),
            status=status,
            status_label=STATUS_LABELS.get(status, status),
            feedback=str((latest or {}).get("notes") or "")
            if status != "pending"
            else "",
            can_resubmit=status == "revision_requested",
        )

    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


def resubmit_project(
    sponsor_id: int, project_id: int, title: str, description: str
) -> None:
    """Save the sponsor's edits and send the project back to faculty review.

    Existing attachments stay attached. Raises PermissionError if the caller
    is not an active sponsor, and ValueError for bad input or a project that
    isn't theirs or isn't waiting for changes. Nothing is saved on error.
    """
    _validate_user_id(sponsor_id)
    _validate_project_id(project_id)
    title = _clean_field(title, "Title", TITLE_MAX_CHARS)
    description = _clean_field(description, "Description", DESCRIPTION_MAX_CHARS)

    with _transaction() as session:
        sponsor = session.execute(
            text(
                "SELECT role, status, must_change_password "
                "FROM public.users WHERE id = :id FOR UPDATE"
            ),
            {"id": sponsor_id},
        ).first()

        if (
            sponsor is None
            or sponsor.role != "sponsor"
            or sponsor.status != "active"
            or sponsor.must_change_password
        ):
            raise PermissionError("Only active sponsors can resubmit projects.")

        updated = session.execute(
            text(
                "UPDATE public.projects "
                "SET title = :title, description = :description, "
                "status = 'pending' "
                "WHERE id = :project_id AND sponsor_id = :sponsor_id "
                "AND status = 'revision_requested' "
                "RETURNING id"
            ),
            {
                "title": title,
                "description": description,
                "project_id": project_id,
                "sponsor_id": sponsor_id,
            },
        ).first()

        if updated is None:
            raise ValueError(
                "This project can't be resubmitted. You can only resubmit "
                "your own project while changes are requested."
            )

        session.execute(
            text(
                "INSERT INTO public.project_reviews "
                "(project_id, actor_id, action, notes) "
                "VALUES (:project_id, :actor_id, 'resubmitted', NULL)"
            ),
            {"project_id": project_id, "actor_id": sponsor_id},
        )
