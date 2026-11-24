"""Lists of project workspaces for faculty and system admins.

Only accepted projects with at least one assigned student are listed, since
other projects have no team and an empty workspace.
  faculty       projects with students assigned through one of *their* courses
                (the same rule authorize_workspace uses to let faculty in)
  system_admin  every accepted project with assigned students
"""

from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import _get_engine, _validate_user_id


class WorkspaceListing(TypedDict):
    project_id: str
    title: str
    sponsor_name: str
    courses: str
    student_count: int
    href: str


SQL_ACTOR = """
    SELECT role FROM public.users
    WHERE id = :actor_id AND status = 'active' AND must_change_password = FALSE
"""

_LISTING = """
    SELECT p.id, p.title,
           COALESCE(s.full_name, 'Unknown sponsor') AS sponsor_name,
           string_agg(DISTINCT c.code || ' · ' || c.term, ', ') AS courses,
           count(DISTINCT pa.student) AS student_count
    FROM public.projects AS p
    JOIN public.project_assignment AS pa ON pa.project = p.id
    JOIN public.courses AS c ON c.id = pa.course
    LEFT JOIN public.users AS s ON s.id = p.sponsor_id
    WHERE p.status = 'accepted' {scope}
    GROUP BY p.id, p.title, s.full_name
    ORDER BY lower(p.title), p.id
"""

SQL_ADMIN_WORKSPACES = _LISTING.format(scope="")

SQL_FACULTY_WORKSPACES = _LISTING.format(scope="AND c.faculty_id = :actor_id")


def list_workspaces(actor_id: int) -> list[WorkspaceListing]:
    """Workspaces the signed-in faculty member or admin can open.

    Raises PermissionError for any other role or an inactive account.
    """
    _validate_user_id(actor_id)
    with _get_engine().connect() as connection:
        role = connection.execute(
            text(SQL_ACTOR), {"actor_id": actor_id}
        ).scalar_one_or_none()
        if role == "system_admin":
            sql = SQL_ADMIN_WORKSPACES
        elif role == "faculty":
            sql = SQL_FACULTY_WORKSPACES
        else:
            raise PermissionError("Access denied")
        rows = (
            connection.execute(text(sql), {"actor_id": actor_id})
            .mappings()
            .all()
        )
    return [
        WorkspaceListing(
            project_id=str(row["id"]),
            title=str(row["title"]),
            sponsor_name=str(row["sponsor_name"]),
            courses=str(row["courses"] or ""),
            student_count=int(row["student_count"]),
            href=f"/project/{row['id']}/workspace",
        )
        for row in rows
    ]
