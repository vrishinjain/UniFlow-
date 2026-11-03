import reflex as rx

import logging
from typing import TypedDict

from sqlalchemy import text

from UniFlow_.review_services import STATUS_LABELS
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
    status: str  # display label, e.g. "Changes requested"
    status_key: str  # raw value, e.g. "revision_requested"
    submitted_date: str
    submitted_at: str


def list_sponsor_projects(sponsor_id: int) -> list[SponsorProject]:
    """Read display-ready projects belonging to the authenticated sponsor."""
    _validate_user_id(sponsor_id)

    try:
        with _get_engine().connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id,title,status,created_at FROM public.projects "
                    "WHERE sponsor_id = :sponsor_id "
                    "ORDER BY created_at DESC, id DESC"
                ),
                {"sponsor_id": sponsor_id},
            ).all()

        return [
            SponsorProject(
                id=int(row.id),
                title=str(row.title),
                status=STATUS_LABELS.get(str(row.status), "Unknown"),
                status_key=str(row.status),
                submitted_date=row.created_at.strftime("%b %d, %Y"),
                submitted_at=row.created_at.isoformat(),
            )
            for row in rows
        ]

    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


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
                    "status": "pending",
                },
            ).scalar_one()
        )

        if files:
            session.execute(
                text(
                    "INSERT INTO public.project_files "
                    "(project_id, filename, content_type, size_bytes, data) "
                    "VALUES (:project_id, :filename, :content_type, "
                    ":size_bytes, :data)"
                ),
                [{"project_id": project_id, **file} for file in files],
            )

    return project_id


def get_faculty_projects() -> list[dict]:
    """Get projects for the faculty dashboard."""

    with _transaction() as session:
        rows = (
            session.execute(
                text("""
                SELECT
                    p.id,
                    p.title,
                    u.full_name AS sponsor_name,
                    p.created_at,
                    p.status
                FROM public.projects AS p
                JOIN public.users AS u
                    ON p.sponsor_id = u.id
                ORDER BY
                    (p.status = 'pending') DESC,
                    p.created_at DESC,
                    p.id DESC
            """)
            )
            .mappings()
            .all()
        )

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "sponsor_name": row["sponsor_name"],
                "created_at": row["created_at"].strftime("%Y-%m-%d"),
                "status": row["status"],
            }
            for row in rows
        ]


# --------------------------------------------------
# T-8: Faculty Project Details and Attachment List
# --------------------------------------------------


def get_faculty_project_details(project_id: int) -> dict | None:
    """Get project information and attachment metadata.

    This function returns attachment names and sizes,
    but does not load the actual file contents.
    """

    if project_id <= 0:
        return None

    with _transaction() as session:
        project = (
            session.execute(
                text("""
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
            """),
                {"project_id": project_id},
            )
            .mappings()
            .first()
        )

        if project is None:
            return None

        attachments = (
            session.execute(
                text("""
                SELECT
                    id,
                    filename,
                    size_bytes
                FROM public.project_files
                WHERE project_id = :project_id
                ORDER BY id
            """),
                {"project_id": project_id},
            )
            .mappings()
            .all()
        )

        return {
            "id": str(project["id"]),
            "title": str(project["title"]),
            "description": str(project["description"] or ""),
            "status": str(project["status"]),
            "created_at": project["created_at"].strftime("%Y-%m-%d"),
            "sponsor_name": str(project["sponsor_name"]),
            "files": [
                {
                    "id": str(file["id"]),
                    "filename": str(file["filename"]),
                    "size_bytes": int(file["size_bytes"]),
                }
                for file in attachments
            ],
        }


# --------------------------------------------------
# T-8: Faculty Attachment Download
# --------------------------------------------------


def get_faculty_project_file(
    file_id: int,
    project_id: int,
) -> dict | None:
    """Retrieve the original attachment belonging to a project.

    The calling state must verify faculty authorization.
    """

    if file_id <= 0 or project_id <= 0:
        return None

    with _transaction() as session:
        attachment = (
            session.execute(
                text("""
                SELECT
                    filename,
                    content_type,
                    data
                FROM public.project_files
                WHERE id = :file_id
                  AND project_id = :project_id
            """),
                {
                    "file_id": file_id,
                    "project_id": project_id,
                },
            )
            .mappings()
            .first()
        )

        if attachment is None:
            return None

        return {
            "filename": str(attachment["filename"]),
            "content_type": str(attachment["content_type"]),
            "data": bytes(attachment["data"]),
        }


class SharedStudentProject(TypedDict):
    id: str
    title: str
    description: str


class StudentProjectFile(TypedDict):
    id: str
    filename: str
    uploaded_at: str


class StudentProjectDetail(SharedStudentProject):
    files: list[StudentProjectFile]


class StudentProjectDownload(TypedDict):
    filename: str
    data: bytes


_STUDENT_PROJECT_VISIBILITY = """
    p.status = 'accepted'
    AND EXISTS (
        SELECT 1 FROM public.users AS u
        WHERE u.id = :student_id
          AND u.role = 'student'
          AND u.status = 'active'
          AND u.must_change_password = FALSE
    )
    AND EXISTS (
        SELECT 1 FROM public.project_course_visibility AS v
        JOIN public.course_enrollments AS e ON e.course_id = v.course_id
        WHERE v.project_id = p.id AND e.student_id = :student_id
    )
"""


def list_shared_projects_for_student(
    student_id: int,
) -> list[SharedStudentProject]:
    """Read unique accepted projects visible through current course enrollment."""
    _validate_user_id(student_id)
    try:
        with _get_engine().connect() as connection:
            student = connection.execute(
                text(
                    "SELECT id FROM public.users WHERE id = :student_id "
                    "AND role = 'student' AND status = 'active' "
                    "AND must_change_password = FALSE"
                ),
                {"student_id": student_id},
            ).first()
            if student is None:
                raise PermissionError(
                    "Only active students can view shared projects."
                )
            rows = (
                connection.execute(
                    text(f"""
                    SELECT p.id, p.title, p.description
                    FROM public.projects AS p
                    WHERE {_STUDENT_PROJECT_VISIBILITY}
                    ORDER BY p.created_at DESC, p.id DESC
                """),
                    {"student_id": student_id},
                )
                .mappings()
                .all()
            )
        return [
            SharedStudentProject(
                id=str(row["id"]),
                title=str(row["title"]),
                description=str(row["description"] or ""),
            )
            for row in rows
        ]
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


def get_shared_project_for_student(
    student_id: int, project_id: int
) -> StudentProjectDetail | None:
    """Read one currently visible project and metadata, never attachment bytes."""
    from UniFlow_.review_services import _validate_project_id

    _validate_user_id(student_id)
    _validate_project_id(project_id)
    try:
        with _get_engine().connect() as connection:
            rows = (
                connection.execute(
                    text(f"""
                    SELECT p.id, p.title, p.description,
                           f.id AS file_id, f.filename, f.uploaded_at
                    FROM public.projects AS p
                    LEFT JOIN public.project_files AS f ON f.project_id = p.id
                    WHERE p.id = :project_id AND {_STUDENT_PROJECT_VISIBILITY}
                    ORDER BY f.uploaded_at, f.id
                """),
                    {"student_id": student_id, "project_id": project_id},
                )
                .mappings()
                .all()
            )
        if not rows:
            return None
        project = rows[0]
        return StudentProjectDetail(
            id=str(project["id"]),
            title=str(project["title"]),
            description=str(project["description"] or ""),
            files=[
                StudentProjectFile(
                    id=str(row["file_id"]),
                    filename=str(row["filename"]),
                    uploaded_at=(
                        row["uploaded_at"].strftime("%b %d, %Y %I:%M %p %Z")
                        if row["uploaded_at"] is not None
                        else "Upload date unavailable"
                    ),
                )
                for row in rows
                if row["file_id"] is not None
            ],
        )
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


def get_shared_project_file_for_student(
    student_id: int, project_id: int, file_id: int
) -> StudentProjectDownload | None:
    """Recheck current account, enrollment and acceptance before reading bytes."""
    from UniFlow_.review_services import _validate_project_id

    _validate_user_id(student_id)
    _validate_project_id(project_id)
    _validate_project_id(file_id)
    try:
        with _get_engine().connect() as connection:
            attachment = (
                connection.execute(
                    text(f"""
                    SELECT f.filename, f.data
                    FROM public.project_files AS f
                    JOIN public.projects AS p ON p.id = f.project_id
                    WHERE f.id = :file_id AND f.project_id = :project_id
                      AND {_STUDENT_PROJECT_VISIBILITY}
                """),
                    {
                        "student_id": student_id,
                        "project_id": project_id,
                        "file_id": file_id,
                    },
                )
                .mappings()
                .first()
            )
        if attachment is None:
            return None
        return StudentProjectDownload(
            filename=str(attachment["filename"]), data=bytes(attachment["data"])
        )
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise
