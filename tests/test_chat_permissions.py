"""Team chat permission tests (PR #124).

Runs against TEST_DATABASE_URL only (see conftest.py). Every test builds its own
throwaway users, course, projects and assignments inside the db_session
transaction, which conftest rolls back afterwards, so nothing is left behind.

The test database needs the current schema plus db/migrations/chatdev.sql.
It does NOT need seed data.
"""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from UniFlow_.chat_services import (
    RATE_LIMIT_MESSAGES,
    _delete_message,
    _load_older_messages,
    _open_project_chat,
    _poll_messages,
    _post_message,
    authorize_channel,
)


# --- helpers ----------------------------------------------------------------


def _insert(conn, sql: str, **params) -> int:
    return int(conn.execute(text(sql + " RETURNING id"), params).scalar_one())


def _user(conn, role: str, *, status: str = "active", must_change: bool = False) -> int:
    return _insert(
        conn,
        """INSERT INTO public.users
               (full_name, email, password_hash, role, status, must_change_password)
           VALUES (:name, :email, 'test-only-not-a-real-hash', :role, :status, :must_change)""",
        name=f"Chat Test {role}",
        email=f"chat-test-{uuid.uuid4().hex}@example.com",
        role=role,
        status=status,
        must_change=must_change,
    )


def _system_admin(conn) -> int:
    """The database allows only one system_admin (one_system_admin), so reuse it.

    It is made active with no forced password change for the test; conftest
    rolls that back. A new one is created only on an empty database.
    """
    existing = conn.execute(
        text("SELECT id FROM public.users WHERE role = 'system_admin' LIMIT 1")
    ).scalar()
    if existing is None:
        return _user(conn, "system_admin")
    conn.execute(
        text(
            """UPDATE public.users SET status = 'active', must_change_password = false
               WHERE id = :id"""
        ),
        {"id": existing},
    )
    return int(existing)


def _assign(conn, student: int, project: int, course: int, by: int) -> None:
    conn.execute(
        text(
            """INSERT INTO public.project_assignment (student, project, course, assigned_by)
               VALUES (:student, :project, :course, :by)"""
        ),
        {"student": student, "project": project, "course": course, "by": by},
    )


def _enroll(conn, student: int, course: int) -> None:
    conn.execute(
        text(
            "INSERT INTO public.course_enrollments (course_id, student_id) VALUES (:c, :s)"
        ),
        {"c": course, "s": student},
    )


def _channel_count(conn, project: int) -> int:
    return int(
        conn.execute(
            text("SELECT count(*) FROM public.chat_channel WHERE project = :p"),
            {"p": project},
        ).scalar_one()
    )


# --- fixtures ---------------------------------------------------------------


@pytest.fixture
def conn(db_session):
    """The rolled-back connection from conftest's db_session."""
    return db_session.connection()


@pytest.fixture
def world(conn):
    """One course, two accepted projects, a team on each, and every kind of outsider."""
    w = SimpleNamespace()
    w.admin = _system_admin(conn)
    w.faculty = _user(conn, "faculty")  # owns the course
    w.other_faculty = _user(conn, "faculty")  # owns nothing here
    w.sponsor = _user(conn, "sponsor")
    w.alice = _user(conn, "student")  # project 1
    w.bob = _user(conn, "student")  # project 1
    w.carol = _user(conn, "student")  # project 2
    w.enrolled_only = _user(conn, "student")  # in the course, no project
    w.pending = _user(conn, "student", status="pending")  # assigned, not approved
    w.must_change = _user(conn, "student", must_change=True)  # assigned, no password yet

    w.course = _insert(
        conn,
        """INSERT INTO public.courses (name, code, term, faculty_id)
           VALUES ('Chat Test Course', 'CT999', 'Test Term', :f)""",
        f=w.faculty,
    )
    w.project1 = _insert(
        conn,
        """INSERT INTO public.projects (sponsor_id, title, description, status)
           VALUES (:s, 'Chat Test Project 1', 'Throwaway project for chat tests.', 'accepted')""",
        s=w.sponsor,
    )
    w.project2 = _insert(
        conn,
        """INSERT INTO public.projects (sponsor_id, title, description, status)
           VALUES (:s, 'Chat Test Project 2', 'Throwaway project for chat tests.', 'accepted')""",
        s=w.sponsor,
    )
    for student in (w.alice, w.bob, w.carol, w.enrolled_only, w.pending, w.must_change):
        _enroll(conn, student, w.course)
    for student in (w.alice, w.bob, w.pending, w.must_change):
        _assign(conn, student, w.project1, w.course, w.faculty)
    _assign(conn, w.carol, w.project2, w.course, w.faculty)
    return w


@pytest.fixture
def channel1(conn, world) -> int:
    """Project 1's chat, opened by a team member."""
    return int(_open_project_chat(conn, world.alice, world.project1)["channel_id"])


# --- project chat: who can open it -------------------------------------------


def test_team_faculty_and_admin_share_one_project_chat(conn, world, channel1):
    for member in (world.bob, world.faculty, world.admin):
        page = _open_project_chat(conn, member, world.project1)
        assert int(page["channel_id"]) == channel1
    assert _channel_count(conn, world.project1) == 1


@pytest.mark.parametrize(
    "who",
    ["carol", "other_faculty", "sponsor", "enrolled_only", "pending", "must_change"],
)
def test_outsiders_cannot_open_project_chat(conn, world, who):
    with pytest.raises(PermissionError):
        _open_project_chat(conn, getattr(world, who), world.project1)


def test_denied_open_creates_no_channel(conn, world):
    with pytest.raises(PermissionError):
        _open_project_chat(conn, world.carol, world.project1)
    assert _channel_count(conn, world.project1) == 0


def test_student_cannot_use_another_teams_channel_id(conn, world, channel1):
    channel2 = int(_open_project_chat(conn, world.carol, world.project2)["channel_id"])
    with pytest.raises(PermissionError):
        authorize_channel(conn, world.alice, channel2)
    with pytest.raises(PermissionError):
        _post_message(conn, world.carol, channel1, "Wrong team")


def test_unknown_channel_is_denied(conn, world):
    with pytest.raises(PermissionError):
        authorize_channel(conn, world.admin, 9_000_000_000_000)


# --- reading and posting -----------------------------------------------------


@pytest.mark.parametrize("who", ["carol", "other_faculty", "sponsor", "enrolled_only"])
def test_outsiders_cannot_post_poll_or_page(conn, world, channel1, who):
    actor = getattr(world, who)
    with pytest.raises(PermissionError):
        _post_message(conn, actor, channel1, "Hello?")
    with pytest.raises(PermissionError):
        _poll_messages(conn, actor, channel1, 0, "2026-01-01T00:00:00+00:00")
    with pytest.raises(PermissionError):
        _load_older_messages(conn, actor, channel1, 1)


def test_members_post_and_see_each_others_messages(conn, world, channel1):
    first = _post_message(conn, world.alice, channel1, "Pushed the board fix.")
    second = _post_message(conn, world.faculty, channel1, "Thanks, looks good.")
    assert first["is_own"] and first["sender_role_label"] == "Student"
    assert second["sender_role_label"] == "Faculty"

    page = _open_project_chat(conn, world.bob, world.project1)
    bodies = [m["body"] for m in page["messages"]]
    assert bodies == ["Pushed the board fix.", "Thanks, looks good."]
    assert not any(m["is_own"] for m in page["messages"])


def test_sender_is_the_signed_in_user(conn, world, channel1):
    message = _post_message(conn, world.bob, channel1, "From Bob")
    assert int(message["sender_id"]) == world.bob


def test_rate_limit_blocks_flooding(conn, world, channel1):
    for n in range(RATE_LIMIT_MESSAGES):
        _post_message(conn, world.alice, channel1, f"Message {n}")
    with pytest.raises(ValueError, match="too quickly"):
        _post_message(conn, world.alice, channel1, "One too many")
    # Limits are per sender: a teammate can still post.
    _post_message(conn, world.bob, channel1, "Still works for me")


# --- deleting ----------------------------------------------------------------


def test_student_can_delete_own_message(conn, world, channel1):
    message = _post_message(conn, world.alice, channel1, "Oops, wrong link")
    deleted = _delete_message(conn, world.alice, channel1, int(message["id"]))
    assert deleted["deleted"] and deleted["body"] == ""


def test_student_cannot_delete_teammates_message(conn, world, channel1):
    message = _post_message(conn, world.alice, channel1, "Alice's message")
    with pytest.raises(ValueError, match="your own"):
        _delete_message(conn, world.bob, channel1, int(message["id"]))
    page = _open_project_chat(conn, world.bob, world.project1)
    assert page["messages"][-1]["can_delete"] is False


@pytest.mark.parametrize("moderator", ["faculty", "admin"])
def test_faculty_and_admin_can_delete_any_message(conn, world, channel1, moderator):
    message = _post_message(conn, world.alice, channel1, "Needs moderating")
    deleted = _delete_message(conn, getattr(world, moderator), channel1, int(message["id"]))
    assert deleted["deleted"]


def test_unrelated_faculty_cannot_delete(conn, world, channel1):
    message = _post_message(conn, world.alice, channel1, "Not yours")
    with pytest.raises(PermissionError):
        _delete_message(conn, world.other_faculty, channel1, int(message["id"]))


def test_deleted_text_is_hidden_but_kept_for_moderation(conn, world, channel1):
    message = _post_message(conn, world.alice, channel1, "Secret typo")
    _delete_message(conn, world.faculty, channel1, int(message["id"]))

    page = _open_project_chat(conn, world.bob, world.project1)
    shown = next(m for m in page["messages"] if m["id"] == message["id"])
    assert shown["deleted"] and shown["body"] == ""

    stored = conn.execute(
        text("SELECT body, deleted_by FROM public.chat_message WHERE id = :id"),
        {"id": int(message["id"])},
    ).one()
    assert stored.body == "Secret typo" and stored.deleted_by == world.faculty


def test_message_from_another_channel_is_not_found(conn, world, channel1):
    channel2 = int(_open_project_chat(conn, world.carol, world.project2)["channel_id"])
    other = _post_message(conn, world.carol, channel2, "Project 2 message")
    with pytest.raises(ValueError, match="not found"):
        _delete_message(conn, world.faculty, channel1, int(other["id"]))


# --- course-wide chats (rules exist ahead of the feature) --------------------


def _course_channel(conn, world, scope: str, projects=()) -> int:
    channel = _insert(
        conn,
        """INSERT INTO public.chat_channel (scope, course, name, created_by)
           VALUES (:scope, :course, 'Test course chat', :by)""",
        scope=scope,
        course=world.course,
        by=world.faculty,
    )
    for project in projects:
        conn.execute(
            text("INSERT INTO public.chat_channel_project (channel, project) VALUES (:c, :p)"),
            {"c": channel, "p": project},
        )
    return channel


def test_course_chat_is_for_enrolled_students_and_course_faculty(conn, world):
    channel = _course_channel(conn, world, "course")
    for allowed in (world.enrolled_only, world.carol, world.faculty, world.admin):
        authorize_channel(conn, allowed, channel)
    for denied in (world.other_faculty, world.sponsor, world.pending, world.must_change):
        with pytest.raises(PermissionError):
            authorize_channel(conn, denied, channel)


def test_course_projects_chat_is_for_listed_teams_only(conn, world):
    channel = _course_channel(conn, world, "course_projects", projects=[world.project2])
    authorize_channel(conn, world.carol, channel)
    authorize_channel(conn, world.faculty, channel)
    for denied in (world.alice, world.enrolled_only, world.other_faculty):
        with pytest.raises(PermissionError):
            authorize_channel(conn, denied, channel)


def test_archived_chat_refuses_new_messages(conn, world, channel1):
    conn.execute(
        text("UPDATE public.chat_channel SET archived_at = now() WHERE id = :id"),
        {"id": channel1},
    )
    with pytest.raises(ValueError, match="archived"):
        _post_message(conn, world.alice, channel1, "Too late")
