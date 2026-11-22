"""Team chat services.

Every public function authorizes the signed-in actor on the same database
connection that reads or writes chat data. Never trust a role, membership,
sender or permission submitted by the browser.

Channels have a scope:
  project          one chat per project; members are exactly the workspace
                   members (authorize_workspace).
  course_projects  faculty/admin-created chat for selected projects in a course
                   (projects listed in chat_channel_project).
  course           faculty/admin-created chat for everyone enrolled in a course.
Only project channels are created by the app today; the course scopes are
authorized here so course chats can be added without touching message code.
"""

import os
from datetime import datetime, timezone
from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.engine import Connection

from UniFlow_.user_services import _get_engine, _validate_user_id
from UniFlow_.workspace_services import (
    ROLE_LABELS,
    authorize_workspace,
    validate_ticket_id,
)

try:
    from zoneinfo import ZoneInfo

    _DISPLAY_TZ = ZoneInfo("America/New_York")
except Exception:  # Windows without the tzdata package
    _DISPLAY_TZ = timezone.utc


MAX_MESSAGE_LENGTH = 2000
PAGE_SIZE = 50
POLL_LIMIT = 200
RATE_LIMIT_MESSAGES = 20
RATE_LIMIT_SECONDS = 60
CHANNEL_SCOPES = ("project", "course_projects", "course")
MODERATOR_ROLES = ("faculty", "system_admin")


class ChatActor(TypedDict):
    id: int
    role: str
    channel_id: int
    scope: str
    can_moderate: bool
    archived: bool


class ChatMessage(TypedDict):
    id: str
    sender_id: str
    sender_name: str
    sender_role_label: str
    body: str
    time_label: str
    deleted: bool
    is_own: bool
    can_delete: bool


class ChatPage(TypedDict):
    channel_id: str
    messages: list[ChatMessage]
    has_older: bool
    server_time: str


class ChatPoll(TypedDict):
    messages: list[ChatMessage]
    deleted_ids: list[str]
    server_time: str
    truncated: bool


# --- SQL -------------------------------------------------------------------
# Kept as module constants so scripts/test_chat_sql.sh can run them against a
# scratch Postgres. Only fixed text is ever interpolated; values are bound.

SQL_CHANNEL = """
    SELECT id, scope, course, project, archived_at
    FROM public.chat_channel WHERE id = :channel_id
"""

SQL_ENSURE_PROJECT_CHANNEL = """
    INSERT INTO public.chat_channel (scope, project)
    VALUES ('project', :project_id)
    ON CONFLICT (project) WHERE scope = 'project' DO NOTHING
"""

SQL_PROJECT_CHANNEL_ID = """
    SELECT id FROM public.chat_channel
    WHERE scope = 'project' AND project = :project_id
"""

_COURSE_ACTOR_BASE = """
    SELECT u.id, u.role FROM public.users AS u
    WHERE u.id = :actor_id
      AND u.status = 'active' AND u.must_change_password = FALSE
      AND (
        u.role = 'system_admin'
        OR (u.role = 'faculty' AND EXISTS (
            SELECT 1 FROM public.courses AS c
            WHERE c.id = :course_id AND c.faculty_id = u.id
        ))
        OR (u.role = 'student' AND {student_rule})
      )
"""

SQL_COURSE_ACTOR = _COURSE_ACTOR_BASE.format(
    student_rule="""EXISTS (
            SELECT 1 FROM public.course_enrollments AS e
            WHERE e.course_id = :course_id AND e.student_id = u.id
        )"""
)

SQL_COURSE_PROJECTS_ACTOR = _COURSE_ACTOR_BASE.format(
    student_rule="""EXISTS (
            SELECT 1 FROM public.project_assignment AS pa
            JOIN public.chat_channel_project AS cp
              ON cp.project = pa.project AND cp.channel = :channel_id
            WHERE pa.student = u.id AND pa.course = :course_id
        )"""
)

_MESSAGE_SELECT = """
    SELECT m.id, m.sender, u.full_name, u.role,
           CASE WHEN m.deleted_at IS NULL THEN m.body ELSE '' END AS body,
           m.created_at, m.deleted_at IS NOT NULL AS deleted
    FROM public.chat_message AS m
    JOIN public.users AS u ON u.id = m.sender
"""

SQL_LATEST_PAGE = (
    _MESSAGE_SELECT
    + """
    WHERE m.channel = :channel_id
    ORDER BY m.id DESC LIMIT :limit
"""
)

SQL_OLDER_PAGE = (
    _MESSAGE_SELECT
    + """
    WHERE m.channel = :channel_id AND m.id < :before_id
    ORDER BY m.id DESC LIMIT :limit
"""
)

# New messages since the last poll. The created_at overlap catches a message
# whose id was allocated before, but committed after, the previous poll; the
# client de-duplicates by id.
SQL_POLL_MESSAGES = (
    _MESSAGE_SELECT
    + """
    WHERE m.channel = :channel_id
      AND (m.id > :after_id
           OR m.created_at >= CAST(:since AS TIMESTAMPTZ) - INTERVAL '30 seconds')
    ORDER BY m.id LIMIT :limit
"""
)

SQL_POLL_DELETED = """
    SELECT id FROM public.chat_message
    WHERE channel = :channel_id AND deleted_at IS NOT NULL
      AND deleted_at >= CAST(:since AS TIMESTAMPTZ) - INTERVAL '30 seconds'
"""

SQL_SERVER_TIME = "SELECT clock_timestamp()"

SQL_RECENT_SENDS = """
    SELECT count(*) FROM public.chat_message
    WHERE sender = :actor_id
      AND created_at > now() - INTERVAL '1 second' * :window_seconds
"""

SQL_INSERT_MESSAGE = """
    INSERT INTO public.chat_message (channel, sender, body)
    VALUES (:channel_id, :actor_id, :body)
    RETURNING id
"""

SQL_ONE_MESSAGE = (
    _MESSAGE_SELECT
    + """
    WHERE m.channel = :channel_id AND m.id = :message_id
"""
)

SQL_LOCK_MESSAGE = """
    SELECT id, sender, deleted_at FROM public.chat_message
    WHERE id = :message_id AND channel = :channel_id
    FOR UPDATE
"""

SQL_DELETE_MESSAGE = """
    UPDATE public.chat_message
    SET deleted_at = now(), deleted_by = :actor_id
    WHERE id = :message_id AND channel = :channel_id AND deleted_at IS NULL
"""


# --- Validation (pure, no database) ---------------------------------------


def validate_chat_id(value: object, label: str = "Message") -> int:
    parsed = validate_ticket_id(value, label)
    assert parsed is not None
    return parsed


def validate_message_body(body: object) -> str:
    """Normalize line endings, trim, and reject empty, oversized or control text."""
    if not isinstance(body, str):
        raise ValueError("Write a message before sending.")
    cleaned = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        raise ValueError("Write a message before sending.")
    if len(cleaned) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Messages can be at most {MAX_MESSAGE_LENGTH:,} characters."
        )
    if any(
        (ord(char) < 32 and char not in "\n\t") or ord(char) == 127
        for char in cleaned
    ):
        raise ValueError("Messages cannot contain control characters.")
    return cleaned


def validate_since(value: object) -> str:
    """Accept only an ISO timestamp this module produced."""
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Invalid chat cursor.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid chat cursor.") from exc
    if parsed.tzinfo is None:
        raise ValueError("Invalid chat cursor.")
    return parsed.isoformat()


def _require_database() -> None:
    if not os.environ.get("REFLEX_DB_URL"):
        raise RuntimeError("Chat is temporarily unavailable.")


# --- Formatting -------------------------------------------------------------


def format_time_label(created_at: datetime) -> str:
    """'Nov 20, 6:31 PM' in Eastern time, portable across Linux/macOS/Windows."""
    local = created_at.astimezone(_DISPLAY_TZ)
    hour = local.hour % 12 or 12
    return f"{local:%b} {local.day}, {hour}:{local:%M} {local:%p}"


def _to_message(row, actor: ChatActor) -> ChatMessage:
    deleted = bool(row["deleted"])
    sender_id = int(row["sender"])
    is_own = sender_id == actor["id"]
    role = str(row["role"])
    return ChatMessage(
        id=str(row["id"]),
        sender_id=str(sender_id),
        sender_name=str(row["full_name"] or "Unnamed member"),
        sender_role_label=ROLE_LABELS.get(role, role.replace("_", " ").title()),
        body="" if deleted else str(row["body"]),
        time_label=format_time_label(row["created_at"]),
        deleted=deleted,
        is_own=is_own,
        can_delete=(not deleted)
        and (is_own or actor["can_moderate"])
        and not actor["archived"],
    )


# --- Authorization ----------------------------------------------------------


def authorize_channel(
    connection: Connection, actor_id: int, channel_id: int
) -> ChatActor:
    """Authorize the persisted identity for one channel; PermissionError if not allowed."""
    _validate_user_id(actor_id)
    _validate_user_id(channel_id)
    channel = (
        connection.execute(text(SQL_CHANNEL), {"channel_id": channel_id})
        .mappings()
        .first()
    )
    if channel is None or channel["scope"] not in CHANNEL_SCOPES:
        raise PermissionError("Access denied")
    scope = str(channel["scope"])
    if scope == "project":
        workspace_actor = authorize_workspace(
            connection, actor_id, int(channel["project"])
        )
        role = workspace_actor["role"]
    else:
        query = (
            SQL_COURSE_ACTOR if scope == "course" else SQL_COURSE_PROJECTS_ACTOR
        )
        actor = (
            connection.execute(
                text(query),
                {
                    "actor_id": actor_id,
                    "course_id": int(channel["course"]),
                    "channel_id": channel_id,
                },
            )
            .mappings()
            .first()
        )
        if actor is None:
            raise PermissionError("Access denied")
        role = str(actor["role"])
    return ChatActor(
        id=actor_id,
        role=role,
        channel_id=channel_id,
        scope=scope,
        can_moderate=role in MODERATOR_ROLES,
        archived=channel["archived_at"] is not None,
    )


# --- Reads ------------------------------------------------------------------


def _server_time(connection: Connection) -> str:
    return connection.execute(text(SQL_SERVER_TIME)).scalar_one().isoformat()


def _read_page(
    connection: Connection, actor: ChatActor, before_id: int | None
) -> ChatPage:
    params = {"channel_id": actor["channel_id"], "limit": PAGE_SIZE + 1}
    if before_id is None:
        sql = SQL_LATEST_PAGE
    else:
        sql = SQL_OLDER_PAGE
        params["before_id"] = before_id
    rows = connection.execute(text(sql), params).mappings().all()
    has_older = len(rows) > PAGE_SIZE
    rows = list(rows[:PAGE_SIZE])
    rows.reverse()
    return ChatPage(
        channel_id=str(actor["channel_id"]),
        messages=[_to_message(row, actor) for row in rows],
        has_older=has_older,
        server_time=_server_time(connection),
    )


def _open_project_chat(
    connection: Connection, actor_id: int, project_id: int
) -> ChatPage:
    # Authorize before creating anything, so non-members cannot create channels.
    authorize_workspace(connection, actor_id, project_id)
    connection.execute(
        text(SQL_ENSURE_PROJECT_CHANNEL), {"project_id": project_id}
    )
    channel_id = connection.execute(
        text(SQL_PROJECT_CHANNEL_ID), {"project_id": project_id}
    ).scalar_one()
    actor = authorize_channel(connection, actor_id, int(channel_id))
    return _read_page(connection, actor, None)


def open_project_chat(actor_id: int, project_id: int) -> ChatPage:
    """Authorize as a workspace member, create the project's channel on first
    use, and return the latest page of messages."""
    _validate_user_id(actor_id)
    _validate_user_id(project_id)
    _require_database()
    with _get_engine().begin() as connection:
        return _open_project_chat(connection, actor_id, project_id)


def _load_older_messages(
    connection: Connection, actor_id: int, channel_id: int, before_id: int
) -> ChatPage:
    actor = authorize_channel(connection, actor_id, channel_id)
    return _read_page(connection, actor, before_id)


def load_older_messages(
    actor_id: int, channel_id: int, before_id: int
) -> ChatPage:
    _validate_user_id(actor_id)
    channel_id = validate_chat_id(channel_id, "Channel")
    before_id = validate_chat_id(before_id)
    _require_database()
    with _get_engine().connect() as connection:
        return _load_older_messages(connection, actor_id, channel_id, before_id)


def _poll_messages(
    connection: Connection,
    actor_id: int,
    channel_id: int,
    after_id: int,
    since: str,
) -> ChatPoll:
    actor = authorize_channel(connection, actor_id, channel_id)
    params = {"channel_id": channel_id, "after_id": after_id, "since": since}
    rows = (
        connection.execute(
            text(SQL_POLL_MESSAGES), {**params, "limit": POLL_LIMIT + 1}
        )
        .mappings()
        .all()
    )
    deleted_rows = connection.execute(
        text(SQL_POLL_DELETED), {"channel_id": channel_id, "since": since}
    ).all()
    server_time = _server_time(connection)
    return ChatPoll(
        messages=[_to_message(row, actor) for row in rows[:POLL_LIMIT]],
        deleted_ids=[str(row[0]) for row in deleted_rows],
        server_time=server_time,
        truncated=len(rows) > POLL_LIMIT,
    )


def poll_messages(
    actor_id: int, channel_id: int, after_id: int, since: str
) -> ChatPoll:
    """New or recently changed messages since the previous poll."""
    _validate_user_id(actor_id)
    channel_id = validate_chat_id(channel_id, "Channel")
    if after_id != 0:
        after_id = validate_chat_id(after_id)
    since = validate_since(since)
    _require_database()
    with _get_engine().connect() as connection:
        return _poll_messages(connection, actor_id, channel_id, after_id, since)


# --- Writes -----------------------------------------------------------------


def _post_message(
    connection: Connection, actor_id: int, channel_id: int, cleaned: str
) -> ChatMessage:
    actor = authorize_channel(connection, actor_id, channel_id)
    if actor["archived"]:
        raise ValueError("This chat is archived and no longer accepts messages.")
    recent = connection.execute(
        text(SQL_RECENT_SENDS),
        {"actor_id": actor_id, "window_seconds": RATE_LIMIT_SECONDS},
    ).scalar_one()
    if int(recent) >= RATE_LIMIT_MESSAGES:
        raise ValueError(
            "You're sending messages too quickly. Wait a moment and try again."
        )
    message_id = connection.execute(
        text(SQL_INSERT_MESSAGE),
        {"channel_id": channel_id, "actor_id": actor_id, "body": cleaned},
    ).scalar_one()
    row = (
        connection.execute(
            text(SQL_ONE_MESSAGE),
            {"channel_id": channel_id, "message_id": int(message_id)},
        )
        .mappings()
        .one()
    )
    return _to_message(row, actor)


def post_message(actor_id: int, channel_id: int, body: object) -> ChatMessage:
    cleaned = validate_message_body(body)
    _validate_user_id(actor_id)
    channel_id = validate_chat_id(channel_id, "Channel")
    _require_database()
    with _get_engine().begin() as connection:
        return _post_message(connection, actor_id, channel_id, cleaned)


def _delete_message(
    connection: Connection, actor_id: int, channel_id: int, message_id: int
) -> ChatMessage:
    actor = authorize_channel(connection, actor_id, channel_id)
    target = (
        connection.execute(
            text(SQL_LOCK_MESSAGE),
            {"channel_id": channel_id, "message_id": message_id},
        )
        .mappings()
        .first()
    )
    if target is None:
        raise ValueError("Message not found in this chat.")
    if target["deleted_at"] is None:
        if int(target["sender"]) != actor_id and not actor["can_moderate"]:
            raise ValueError("You can only delete your own messages.")
        if actor["archived"]:
            raise ValueError("This chat is archived.")
        connection.execute(
            text(SQL_DELETE_MESSAGE),
            {
                "channel_id": channel_id,
                "message_id": message_id,
                "actor_id": actor_id,
            },
        )
    row = (
        connection.execute(
            text(SQL_ONE_MESSAGE),
            {"channel_id": channel_id, "message_id": message_id},
        )
        .mappings()
        .one()
    )
    return _to_message(row, actor)


def delete_message(
    actor_id: int, channel_id: int, message_id: int
) -> ChatMessage:
    """Soft-delete: senders delete their own messages; faculty and admins any.

    The original text stays in the database for moderation but is never
    returned to any client again.
    """
    _validate_user_id(actor_id)
    channel_id = validate_chat_id(channel_id, "Channel")
    message_id = validate_chat_id(message_id)
    _require_database()
    with _get_engine().begin() as connection:
        return _delete_message(connection, actor_id, channel_id, message_id)
