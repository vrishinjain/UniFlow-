import reflex as rx

import os
from contextlib import nullcontext
from datetime import date
from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.engine import Connection

from UniFlow_.user_services import _get_engine, _validate_user_id


ROLE_LABELS = {
    "student": "Student",
    "faculty": "Faculty",
    "system_admin": "System admin",
}


class WorkspaceActor(TypedDict):
    id: int
    role: str
    can_edit_milestones: bool


class WorkspaceMember(TypedDict):
    id: str
    full_name: str
    role: str
    role_label: str
    option_label: str


class WorkspaceTicket(TypedDict):
    id: str
    title: str
    description: str
    status: str
    priority: str
    assignee: str
    assignee_label: str
    milestone: str
    milestone_label: str


class WorkspaceMilestone(TypedDict):
    id: str
    title: str
    description: str
    due_date: str
    done_count: int
    total_count: int


class WorkspaceSnapshot(TypedDict):
    id: str
    title: str
    team: list[WorkspaceMember]
    tickets: list[WorkspaceTicket]
    milestones: list[WorkspaceMilestone]
    can_edit_milestones: bool
    actor_role: str


_ASSOCIATED_FACULTY = """
    EXISTS (
        SELECT 1 FROM public.courses AS c
        WHERE c.faculty_id = u.id
          AND (
            EXISTS (
                SELECT 1 FROM public.project_course_visibility AS v
                WHERE v.course_id = c.id AND v.project_id = :project_id
            )
            OR EXISTS (
                SELECT 1 FROM public.project_assignment AS pa
                WHERE pa.course = c.id AND pa.project = :project_id
            )
          )
    )
"""

_ELIGIBLE_MEMBER = f"""
    u.status = 'active' AND u.must_change_password = FALSE
    AND (
        u.role = 'system_admin'
        OR (u.role = 'student' AND EXISTS (
            SELECT 1 FROM public.project_assignment AS pa
            WHERE pa.student = u.id AND pa.project = :project_id
        ))
        OR (u.role = 'faculty' AND {_ASSOCIATED_FACULTY})
    )
"""


def authorize_workspace(
    connection: Connection, actor_id: int, project_id: int
) -> WorkspaceActor:
    """Authorize current persisted identity before any private project reads.

    Reuse on the mutation's own connection in subsequent phases; never trust
    a role, membership, or permission submitted by the browser.
    """
    _validate_user_id(actor_id)
    _validate_user_id(project_id)
    actor = (
        connection.execute(
            text(f"""
            SELECT u.id, u.role FROM public.users AS u
            WHERE u.id = :actor_id AND {_ELIGIBLE_MEMBER}
              AND EXISTS (SELECT 1 FROM public.projects WHERE id = :project_id)
        """),
            {"actor_id": actor_id, "project_id": project_id},
        )
        .mappings()
        .first()
    )
    if actor is None:
        raise PermissionError("Access denied")
    role = str(actor["role"])
    return WorkspaceActor(
        id=int(actor["id"]), role=role, can_edit_milestones=role == "faculty"
    )


def get_workspace_team(
    connection: Connection, actor_id: int, project_id: int
) -> list[WorkspaceMember]:
    """Authorize, then read the deduplicated project-wide eligible assignee union."""
    authorize_workspace(connection, actor_id, project_id)
    rows = (
        connection.execute(
            text(f"""
            SELECT u.id, u.full_name, u.role FROM public.users AS u
            WHERE {_ELIGIBLE_MEMBER}
            ORDER BY lower(u.full_name), u.role, u.id
        """),
            {"project_id": project_id},
        )
        .mappings()
        .all()
    )
    return [
        WorkspaceMember(
            id=str(row["id"]),
            full_name=str(row["full_name"] or "Unnamed member"),
            role=str(row["role"]),
            role_label=ROLE_LABELS[str(row["role"])],
            option_label=(
                f"{row['full_name'] or 'Unnamed member'} · "
                f"{ROLE_LABELS[str(row['role'])]} · #{row['id']}"
            ),
        )
        for row in rows
    ]


def get_workspace(actor_id: int, project_id: int) -> WorkspaceSnapshot:
    _validate_user_id(actor_id)
    _validate_user_id(project_id)
    _require_database()
    with _get_engine().connect() as connection:
        return _read_workspace(connection, actor_id, project_id)


def _read_workspace(
    connection: Connection, actor_id: int, project_id: int
) -> WorkspaceSnapshot:
    """Read only existing records; denied/invalid IDs never return private data.

    Missing database configuration raises RuntimeError; SQLAlchemy errors are
    propagated to the caller for readable UI feedback and retry.
    """
    _validate_user_id(actor_id)
    _validate_user_id(project_id)
    if not os.environ.get("REFLEX_DB_URL"):
        raise RuntimeError("Workspace services are temporarily unavailable.")
    with nullcontext(connection):
        actor = authorize_workspace(connection, actor_id, project_id)
        project = (
            connection.execute(
                text(
                    "SELECT id, title FROM public.projects WHERE id = :project_id"
                ),
                {"project_id": project_id},
            )
            .mappings()
            .first()
        )
        if project is None:
            raise PermissionError("Access denied")
        team = get_workspace_team(connection, actor_id, project_id)
        authorize_workspace(connection, actor_id, project_id)
        milestone_rows = (
            connection.execute(
                text("""
                SELECT id, title, description, due_date FROM public.milestone
                WHERE project = :project_id ORDER BY due_date NULLS LAST, id
            """),
                {"project_id": project_id},
            )
            .mappings()
            .all()
        )
        authorize_workspace(connection, actor_id, project_id)
        ticket_rows = (
            connection.execute(
                text("""
                SELECT t.id, t.title, t.description, t.status, t.priority,
                       t.assignee, m.id AS milestone, m.title AS milestone_title
                FROM public.ticket AS t
                LEFT JOIN public.milestone AS m
                  ON m.id = t.milestone AND m.project = t.project
                WHERE t.project = :project_id
                ORDER BY t.created_at, t.id
            """),
                {"project_id": project_id},
            )
            .mappings()
            .all()
        )
        actor = authorize_workspace(connection, actor_id, project_id)
    counts: dict[str, list[int]] = {}
    for row in ticket_rows:
        if row["milestone"] is not None:
            count = counts.setdefault(str(row["milestone"]), [0, 0])
            count[1] += 1
            if row["status"] == "Done":
                count[0] += 1
    members = {member["id"]: member for member in team}
    tickets: list[WorkspaceTicket] = []
    for row in ticket_rows:
        assignee = str(row["assignee"]) if row["assignee"] is not None else ""
        member = members.get(assignee)
        label = "Unassigned"
        if member is not None:
            label = member["option_label"]
        elif assignee:
            label = "Assignee no longer eligible"
        tickets.append(
            WorkspaceTicket(
                id=str(row["id"]),
                title=str(row["title"]),
                description=str(row["description"] or ""),
                status=str(row["status"]),
                priority=str(row["priority"] or "Not set"),
                assignee=assignee,
                assignee_label=label,
                milestone=str(row["milestone"])
                if row["milestone"] is not None
                else "",
                milestone_label=str(row["milestone_title"] or "No milestone"),
            )
        )
    return WorkspaceSnapshot(
        id=str(project["id"]),
        title=str(project["title"]),
        team=team,
        tickets=tickets,
        milestones=[
            WorkspaceMilestone(
                id=str(row["id"]),
                title=str(row["title"]),
                description=str(row["description"] or ""),
                due_date=row["due_date"].isoformat()
                if row["due_date"] is not None
                else "",
                done_count=counts.get(str(row["id"]), [0, 0])[0],
                total_count=counts.get(str(row["id"]), [0, 0])[1],
            )
            for row in milestone_rows
        ],
        can_edit_milestones=actor["can_edit_milestones"],
        actor_role=actor["role"],
    )


TICKET_PRIORITIES = ("Low", "Medium", "High", "Urgent")
TICKET_STATUSES = ("To Do", "In Progress", "Review", "Done")


class TicketFields(TypedDict):
    title: str
    description: str
    priority: str
    assignee: int | None
    milestone: int | None


def validate_ticket_id(
    value: object, label: str = "Ticket", optional: bool = False
) -> int | None:
    """Pure bigint parsing; rejects booleans, floats, Unicode digits and overflow."""
    if optional and (value is None or value == ""):
        return None
    if type(value) is int:
        parsed = value
    elif (
        isinstance(value, str)
        and value.isascii()
        and value.isdecimal()
        and len(value) <= 19
    ):
        parsed = int(value)
    else:
        raise ValueError(f"Invalid {label.lower()} ID.")
    if not 0 < parsed <= 9223372036854775807:
        raise ValueError(f"Invalid {label.lower()} ID.")
    return parsed


def validate_ticket_fields(
    title: object,
    description: object,
    priority: object,
    assignee: object = None,
    milestone: object = None,
) -> TicketFields:
    """Pure field validation, with no connection or writes."""
    if (
        not isinstance(title, str)
        or not title.strip()
        or len(title.strip()) > 200
        or "\x00" in title
    ):
        raise ValueError(
            "Title is required and must be at most 200 characters."
        )
    if (
        not isinstance(description, str)
        or not description.strip()
        or len(description.strip()) > 20000
        or "\x00" in description
    ):
        raise ValueError(
            "Description is required and must be at most 20,000 characters."
        )
    if not isinstance(priority, str) or priority not in TICKET_PRIORITIES:
        raise ValueError("Choose Low, Medium, High or Urgent priority.")
    return TicketFields(
        title=title.strip(),
        description=description.strip(),
        priority=priority,
        assignee=validate_ticket_id(assignee, "Assignee", optional=True),
        milestone=validate_ticket_id(milestone, "Milestone", optional=True),
    )


class MilestoneFields(TypedDict):
    title: str
    description: str
    due_date: date


def validate_milestone_fields(
    title: object, description: object, due_date: object
) -> MilestoneFields:
    """Pure validation using the current server day; ISO YYYY-MM-DD is required."""
    fields = validate_ticket_fields(title, description, "Medium")
    if not isinstance(due_date, str) or len(due_date) != 10:
        raise ValueError("Choose a valid due date in YYYY-MM-DD format.")
    try:
        parsed = date.fromisoformat(due_date)
    except ValueError:
        raise ValueError(
            "Choose a valid due date in YYYY-MM-DD format."
        ) from None
    if parsed.isoformat() != due_date:
        raise ValueError("Choose a valid due date in YYYY-MM-DD format.")
    if parsed < date.today():
        raise ValueError("Due date must be today or later.")
    return MilestoneFields(
        title=fields["title"],
        description=fields["description"],
        due_date=parsed,
    )


def _validate_milestone_ticket_ids(ticket_ids: object) -> list[int]:
    if not isinstance(ticket_ids, (list, tuple)):
        raise ValueError("Choose tickets from this project.")
    return list(
        dict.fromkeys(validate_ticket_id(value) for value in ticket_ids)
    )


def _authorize_milestone_editor(
    connection: Connection, actor_id: int, project_id: int
) -> None:
    actor = authorize_workspace(connection, actor_id, project_id)
    if actor["role"] != "faculty":
        raise PermissionError("Access denied")


def _validate_milestone_selection(
    connection: Connection, project_id: int, ticket_ids: list[int]
) -> None:
    rows = (
        connection.execute(
            text(
                "SELECT id FROM public.ticket WHERE project = :project_id FOR UPDATE"
            ),
            {"project_id": project_id},
        )
        .scalars()
        .all()
    )
    if not set(ticket_ids).issubset(set(rows)):
        raise ValueError(
            "Choose tickets from this project; a selected ticket is unavailable."
        )


def _save_milestone_links(
    connection: Connection,
    project_id: int,
    milestone_id: int,
    ticket_ids: list[int],
) -> None:
    connection.execute(
        text("""
            UPDATE public.ticket
            SET milestone = CASE WHEN id = ANY(CAST(:ticket_ids AS bigint[]))
                                 THEN :milestone_id ELSE NULL END,
                updated_at = now()
            WHERE project = :project_id AND (
                (id = ANY(CAST(:ticket_ids AS bigint[]))
                 AND milestone IS DISTINCT FROM :milestone_id)
                OR (milestone = :milestone_id
                    AND NOT (id = ANY(CAST(:ticket_ids AS bigint[]))))
            )
        """),
        {
            "project_id": project_id,
            "milestone_id": milestone_id,
            "ticket_ids": ticket_ids,
        },
    )


def create_milestone(
    actor_id: int,
    project_id: int,
    title: object,
    description: object,
    due_date: object,
    ticket_ids: object,
) -> WorkspaceSnapshot:
    fields = validate_milestone_fields(title, description, due_date)
    selected = _validate_milestone_ticket_ids(ticket_ids)
    validate_ticket_id(actor_id, "Actor")
    validate_ticket_id(project_id, "Project")
    _require_database()
    with _get_engine().begin() as connection:
        _lock_workspace(connection, actor_id, project_id)
        _authorize_milestone_editor(connection, actor_id, project_id)
        _validate_milestone_selection(connection, project_id, selected)
        fields = validate_milestone_fields(title, description, due_date)
        _authorize_milestone_editor(connection, actor_id, project_id)
        milestone_id = connection.execute(
            text("""
                INSERT INTO public.milestone (project, title, description, due_date, created_by)
                VALUES (:project_id, :title, :description, :due_date, :actor_id)
                RETURNING id
            """),
            {**fields, "project_id": project_id, "actor_id": actor_id},
        ).scalar_one()
        _save_milestone_links(
            connection, project_id, int(milestone_id), selected
        )
        snapshot = _read_workspace(connection, actor_id, project_id)
    return snapshot


def update_milestone(
    actor_id: int,
    project_id: int,
    milestone_id: int,
    title: object,
    description: object,
    due_date: object,
    ticket_ids: object,
) -> WorkspaceSnapshot:
    fields = validate_milestone_fields(title, description, due_date)
    selected = _validate_milestone_ticket_ids(ticket_ids)
    validate_ticket_id(actor_id, "Actor")
    validate_ticket_id(project_id, "Project")
    validate_ticket_id(milestone_id, "Milestone")
    _require_database()
    with _get_engine().begin() as connection:
        _lock_workspace(connection, actor_id, project_id)
        _authorize_milestone_editor(connection, actor_id, project_id)
        target = connection.execute(
            text(
                "SELECT id FROM public.milestone WHERE id = :milestone_id AND project = :project_id FOR UPDATE"
            ),
            {"milestone_id": milestone_id, "project_id": project_id},
        ).scalar_one_or_none()
        if target is None:
            raise ValueError("Milestone not found in this project.")
        _validate_milestone_selection(connection, project_id, selected)
        fields = validate_milestone_fields(title, description, due_date)
        _authorize_milestone_editor(connection, actor_id, project_id)
        connection.execute(
            text("""
                UPDATE public.milestone
                SET title = :title, description = :description, due_date = :due_date
                WHERE id = :milestone_id AND project = :project_id
            """),
            {**fields, "milestone_id": milestone_id, "project_id": project_id},
        )
        _save_milestone_links(connection, project_id, milestone_id, selected)
        snapshot = _read_workspace(connection, actor_id, project_id)
    return snapshot


def _require_database() -> None:
    if not os.environ.get("REFLEX_DB_URL"):
        raise RuntimeError("Workspace services are temporarily unavailable.")


def _lock_workspace(
    connection: Connection, actor_id: int, project_id: int
) -> None:
    authorize_workspace(connection, actor_id, project_id)
    connection.execute(
        text(
            "SELECT id FROM public.projects WHERE id = :project_id FOR UPDATE"
        ),
        {"project_id": project_id},
    ).scalar_one_or_none()
    connection.execute(
        text("SELECT id FROM public.users WHERE id = :actor_id FOR SHARE"),
        {"actor_id": actor_id},
    ).scalar_one_or_none()
    authorize_workspace(connection, actor_id, project_id)


def _validate_ticket_links(
    connection: Connection, project_id: int, fields: TicketFields
) -> None:
    if fields["assignee"] is not None:
        params = {"project_id": project_id, "assignee": fields["assignee"]}
        connection.execute(
            text("SELECT id FROM public.users WHERE id = :assignee FOR SHARE"),
            params,
        ).scalar_one_or_none()
        eligible = connection.execute(
            text(
                f"SELECT u.id FROM public.users u WHERE u.id = :assignee AND {_ELIGIBLE_MEMBER}"
            ),
            params,
        ).scalar_one_or_none()
        if eligible is None:
            raise ValueError(
                "Choose an eligible project team member or Unassigned."
            )
    if fields["milestone"] is not None:
        milestone = connection.execute(
            text(
                "SELECT id FROM public.milestone WHERE id = :milestone AND project = :project_id FOR SHARE"
            ),
            {"milestone": fields["milestone"], "project_id": project_id},
        ).scalar_one_or_none()
        if milestone is None:
            raise ValueError(
                "Choose a milestone from this project or No milestone."
            )


def _require_ticket(
    connection: Connection, project_id: int, ticket_id: int
) -> None:
    target = connection.execute(
        text(
            "SELECT id FROM public.ticket WHERE id = :ticket_id AND project = :project_id FOR UPDATE"
        ),
        {"ticket_id": ticket_id, "project_id": project_id},
    ).scalar_one_or_none()
    if target is None:
        raise ValueError("Ticket not found in this project.")


def create_ticket(
    actor_id: int,
    project_id: int,
    title: object,
    description: object,
    priority: object,
    assignee: object = None,
    milestone: object = None,
) -> WorkspaceSnapshot:
    fields = validate_ticket_fields(
        title, description, priority, assignee, milestone
    )
    validate_ticket_id(actor_id, "Actor")
    validate_ticket_id(project_id, "Project")
    _require_database()
    with _get_engine().begin() as connection:
        _lock_workspace(connection, actor_id, project_id)
        _validate_ticket_links(connection, project_id, fields)
        authorize_workspace(connection, actor_id, project_id)
        connection.execute(
            text("""
                INSERT INTO public.ticket
                    (project, title, description, status, priority, assignee, milestone, created_by)
                VALUES (:project_id, :title, :description, 'To Do', :priority, :assignee, :milestone, :actor_id)
            """),
            {**fields, "actor_id": actor_id, "project_id": project_id},
        )
        snapshot = _read_workspace(connection, actor_id, project_id)
    return snapshot


def update_ticket(
    actor_id: int,
    project_id: int,
    ticket_id: int,
    title: object,
    description: object,
    priority: object,
    assignee: object = None,
    milestone: object = None,
) -> WorkspaceSnapshot:
    fields = validate_ticket_fields(
        title, description, priority, assignee, milestone
    )
    validate_ticket_id(actor_id, "Actor")
    validate_ticket_id(project_id, "Project")
    validate_ticket_id(ticket_id)
    _require_database()
    with _get_engine().begin() as connection:
        _lock_workspace(connection, actor_id, project_id)
        _require_ticket(connection, project_id, ticket_id)
        _validate_ticket_links(connection, project_id, fields)
        authorize_workspace(connection, actor_id, project_id)
        connection.execute(
            text("""
                UPDATE public.ticket SET title = :title, description = :description,
                    priority = :priority, assignee = :assignee, milestone = :milestone,
                    updated_at = now()
                WHERE id = :ticket_id AND project = :project_id
            """),
            {**fields, "project_id": project_id, "ticket_id": ticket_id},
        )
        snapshot = _read_workspace(connection, actor_id, project_id)
    return snapshot


def delete_ticket(
    actor_id: int, project_id: int, ticket_id: int
) -> WorkspaceSnapshot:
    validate_ticket_id(actor_id, "Actor")
    validate_ticket_id(project_id, "Project")
    validate_ticket_id(ticket_id)
    _require_database()
    with _get_engine().begin() as connection:
        _lock_workspace(connection, actor_id, project_id)
        _require_ticket(connection, project_id, ticket_id)
        authorize_workspace(connection, actor_id, project_id)
        connection.execute(
            text(
                "DELETE FROM public.ticket WHERE id = :ticket_id AND project = :project_id"
            ),
            {"ticket_id": ticket_id, "project_id": project_id},
        )
        snapshot = _read_workspace(connection, actor_id, project_id)
    return snapshot


def move_ticket(
    actor_id: int, project_id: int, ticket_id: int, status: str
) -> WorkspaceSnapshot:
    validate_ticket_id(actor_id, "Actor")
    validate_ticket_id(project_id, "Project")
    validate_ticket_id(ticket_id)
    if not isinstance(status, str) or status not in TICKET_STATUSES:
        raise ValueError("Choose a valid ticket status.")
    _require_database()
    with _get_engine().begin() as connection:
        _lock_workspace(connection, actor_id, project_id)
        _require_ticket(connection, project_id, ticket_id)
        authorize_workspace(connection, actor_id, project_id)
        connection.execute(
            text(
                "UPDATE public.ticket SET status = :status, updated_at = now() WHERE id = :ticket_id AND project = :project_id"
            ),
            {
                "ticket_id": ticket_id,
                "project_id": project_id,
                "status": status,
            },
        )
        snapshot = _read_workspace(connection, actor_id, project_id)
    return snapshot
