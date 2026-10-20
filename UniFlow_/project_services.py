from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import (
    _get_engine,
    _required_text,
    _transaction,
    _validate_user_id,
)
from UniFlow_.utils.files import (
    MAX_FILES,
    MAX_FILE_BYTES,
    MIME_TYPES,
    ValidatedFile,
    _safe_filename,
    _validate_signature,
)


class SponsorProject(TypedDict):
    id: int
    title: str
    status: str
    submitted_date: str
    submitted_at: str


def list_sponsor_projects(sponsor_id: int) -> list[SponsorProject]:
    """Read only this sponsor's projects, newest first; never change the schema."""
    _validate_user_id(sponsor_id)
    with _get_engine().connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, title, status, created_at FROM public.projects "
                "WHERE sponsor_id = :sponsor_id "
                "ORDER BY created_at DESC, id DESC"
            ),
            {"sponsor_id": sponsor_id},
        ).all()
    return [
        SponsorProject(
            id=int(row.id),
            title=str(row.title),
            status=str(row.status).replace("_", " ").title(),
            submitted_date=row.created_at.strftime("%b %d, %Y"),
            submitted_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


def submit_project(
    sponsor_id: int, title: str, description: str, files: list[ValidatedFile]
) -> int:
    """Save one submission and all attachments in the existing transaction."""
    _validate_user_id(sponsor_id)
    title = _required_text(title, "Title")
    description = _required_text(description, "Description")
    if len(files) > MAX_FILES:
        raise ValueError("Choose at most 3 attachments. Nothing was saved.")
    for file in files:
        filename = _safe_filename(file["filename"])
        extension = filename.rsplit(".", 1)[-1].lower()
        if (
            not isinstance(file["data"], bytes)
            or not 0 < len(file["data"]) <= MAX_FILE_BYTES
        ):
            raise ValueError(
                "Each attachment must be non-empty and 10 MB or smaller."
            )
        if (
            file["size_bytes"] != len(file["data"])
            or file["content_type"] != MIME_TYPES[f".{extension}"]
        ):
            raise ValueError(
                "An attachment has invalid metadata. Please select it again."
            )
        _validate_signature(file["data"], f".{extension}")
    with _transaction() as session:
        sponsor = session.execute(
            text(
                "SELECT role, status, must_change_password FROM public.users WHERE id = :id FOR UPDATE"
            ),
            {"id": sponsor_id},
        ).first()
        if (
            sponsor is None
            or sponsor.role != "sponsor"
            or sponsor.status != "active"
            or sponsor.must_change_password
        ):
            raise PermissionError(
                "Only active sponsors who have set their password may submit projects."
            )
        project_id = int(
            session.execute(
                text(
                    "INSERT INTO public.projects (sponsor_id, title, description, status) VALUES (:sponsor_id, :title, :description, :status) RETURNING id"
                ),
                {
                    "sponsor_id": sponsor_id,
                    "title": title,
                    "description": description,
                    "status": "submitted",
                },
            ).scalar_one()
        )
        if files:
            session.execute(
                text(
                    "INSERT INTO public.project_files (project_id, filename, content_type, size_bytes, data) VALUES (:project_id, :filename, :content_type, :size_bytes, :data)"
                ),
                [{"project_id": project_id, **file} for file in files],
            )
    return project_id
