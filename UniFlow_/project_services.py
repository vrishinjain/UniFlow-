
import reflex as rx

from sqlalchemy import text

from UniFlow_.user_services import (
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


def submit_project(
    sponsor_id: int,
    title: str,
    description: str,
    files: list[ValidatedFile],
) -> int:
    """Save one submission and all attachments in the existing transaction."""

    _validate_user_id(sponsor_id)

    title = _required_text(title, "Title")
    description = _required_text(description, "Description")

    if len(files) > MAX_FILES:
        raise ValueError(
            "Choose at most 3 attachments. Nothing was saved."
        )

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
                "SELECT role, status, must_change_password "
                "FROM public.users "
                "WHERE id = :id FOR UPDATE"
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
                "Only active sponsors who have set their password "
                "may submit projects."
            )

        project_id = int(
            session.execute(
                text(
                    "INSERT INTO public.projects "
                    "(sponsor_id, title, description, status) "
                    "VALUES (:sponsor_id, :title, :description, :status) "
                    "RETURNING id"
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
                    "INSERT INTO public.project_files "
                    "(project_id, filename, content_type, size_bytes, data) "
                    "VALUES "
                    "(:project_id, :filename, :content_type, "
                    ":size_bytes, :data)"
                ),
                [
                    {"project_id": project_id, **file}
                    for file in files
                ],
            )

    return project_id


def get_faculty_projects() -> list[dict]:
    """Get all submitted projects with sponsor names, newest first."""

    with _transaction() as session:
        rows = session.execute(
            text(
                """
                SELECT
                    p.id,
                    p.title,
                    u.full_name AS sponsor_name,
                    p.created_at,
                    p.status
                FROM public.projects AS p
                JOIN public.users AS u
                    ON p.sponsor_id = u.id
                ORDER BY p.created_at DESC, p.id DESC
                """
            )
        ).mappings().all()

    return [
        {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "sponsor_name": str(row["sponsor_name"]),
            "created_at": (
                str(row["created_at"])
                if row["created_at"] is not None
                else ""
            ),
            "status": str(row["status"]),
        }
        for row in rows
    ]
    
def get_faculty_project_details(project_id: int) -> dict | None:
    """Get project details and attachment metadata without file contents."""

    with _transaction() as session:
        project = session.execute(
            text(
                """
                SELECT
                    p.id,
                    p.title,
                    p.description,
                    p.status,
                    p.created_at,
                    u.full_name AS sponsor_name
                FROM public.projects AS p
                JOIN public.users AS u
                    ON p.sponsor_id = u.id
                WHERE p.id = :project_id
                """
            ),
            {"project_id": project_id},
        ).mappings().first()

        if project is None:
            return None

        files = session.execute(
            text(
                """
                SELECT
                    id,
                    filename,
                    size_bytes
                FROM public.project_files
                WHERE project_id = :project_id
                ORDER BY id
                """
            ),
            {"project_id": project_id},
        ).mappings().all()

    return {
        "id": str(project["id"]),
        "title": str(project["title"]),
        "description": str(project["description"]),
        "sponsor_name": str(project["sponsor_name"]),
        "status": str(project["status"]),
        "created_at": (
            project["created_at"].strftime("%Y-%m-%d")
            if project["created_at"] is not None
            else ""
        ),
        "files": [
            {
                "id": str(file["id"]),
                "filename": str(file["filename"]),
                "size_bytes": int(file["size_bytes"]),
            }
            for file in files
        ],
    }

