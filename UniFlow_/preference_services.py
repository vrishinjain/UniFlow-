import reflex as rx

import logging
from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from UniFlow_.courses_services import (
    EnrolledStudent,
    _owned_course,
    parse_course_id,
)
from UniFlow_.user_services import _get_engine, _transaction, _validate_user_id

# How many projects each student ranks per course (1st, 2nd, 3rd choice).
PREFERENCE_SLOTS = 3


# ---------------------------------------------------------------- faculty --


class CoursePreferenceStatus(TypedDict):
    preferences_open: bool
    enrolled: int
    submitted: int
    missing: list[EnrolledStudent]


def get_course_preference_status(
    faculty_id: int, course_id: str | int
) -> CoursePreferenceStatus:
    """Open/closed flag plus who has not submitted, for the faculty's own course."""
    _validate_user_id(faculty_id)
    course_id = parse_course_id(course_id)
    with _transaction() as session:
        _owned_course(session, faculty_id, course_id)
        is_open = session.execute(
            text("SELECT preferences_open FROM public.courses WHERE id = :course_id"),
            {"course_id": course_id},
        ).scalar_one()
        rows = session.execute(
            text("""
                SELECT u.id, u.full_name, u.email,
                       EXISTS (
                           SELECT 1 FROM public.student_preference sp
                           WHERE sp.student = u.id AND sp.course = e.course_id
                       ) AS submitted
                FROM public.course_enrollments e
                JOIN public.users u ON u.id = e.student_id
                WHERE e.course_id = :course_id
                ORDER BY lower(u.full_name), lower(u.email), u.id
            """),
            {"course_id": course_id},
        ).all()
    missing = [
        EnrolledStudent(id=int(r.id), full_name=str(r.full_name), email=str(r.email))
        for r in rows
        if not r.submitted
    ]
    return CoursePreferenceStatus(
        preferences_open=bool(is_open),
        enrolled=len(rows),
        submitted=len(rows) - len(missing),
        missing=missing,
    )


def set_course_preferences_open(
    faculty_id: int, course_id: str | int, is_open: bool
) -> None:
    """Open or close preference submission for one of the faculty's courses."""
    _validate_user_id(faculty_id)
    course_id = parse_course_id(course_id)
    if not isinstance(is_open, bool):
        raise ValueError("Invalid preferences setting.")
    with _transaction() as session:
        _owned_course(session, faculty_id, course_id)
        session.execute(
            text(
                "UPDATE public.courses SET preferences_open = :is_open "
                "WHERE id = :course_id"
            ),
            {"is_open": is_open, "course_id": course_id},
        )


# ---------------------------------------------------------------- student --


class ProjectOption(TypedDict):
    id: str
    title: str


class PreferenceSlot(TypedDict):
    rank: int
    label: str
    selected: str  # project id as text, "" when empty
    selected_title: str


class CoursePreferenceForm(TypedDict):
    course_id: str
    course_label: str
    preferences_open: bool
    slot_count: int
    options: list[ProjectOption]
    slots: list[PreferenceSlot]
    submitted: bool


_RANK_LABELS = {1: "1st choice", 2: "2nd choice", 3: "3rd choice"}


def _require_active_student(connection, student_id: int) -> None:
    student = connection.execute(
        text(
            "SELECT id FROM public.users WHERE id = :student_id "
            "AND role = 'student' AND status = 'active' "
            "AND must_change_password = FALSE"
        ),
        {"student_id": student_id},
    ).first()
    if student is None:
        raise PermissionError("Only active students can rank projects.")


_VISIBLE_IN_COURSE = """
    SELECT p.id, p.title
    FROM public.projects p
    WHERE p.status = 'accepted'
      AND EXISTS (
          SELECT 1 FROM public.project_course_visibility v
          WHERE v.project_id = p.id AND v.course_id = :course_id
      )
    ORDER BY lower(p.title), p.id
"""


def get_student_preference_forms(student_id: int) -> list[CoursePreferenceForm]:
    """One ranking form per course the student is enrolled in."""
    _validate_user_id(student_id)
    try:
        with _get_engine().connect() as connection:
            _require_active_student(connection, student_id)
            courses = connection.execute(
                text("""
                    SELECT c.id, c.code, c.name, c.term, c.preferences_open
                    FROM public.course_enrollments e
                    JOIN public.courses c ON c.id = e.course_id
                    WHERE e.student_id = :student_id
                    ORDER BY c.term DESC, c.code, c.id
                """),
                {"student_id": student_id},
            ).all()
            forms: list[CoursePreferenceForm] = []
            for course in courses:
                projects = connection.execute(
                    text(_VISIBLE_IN_COURSE), {"course_id": int(course.id)}
                ).all()
                saved = {
                    int(r.rank): str(r.project)
                    for r in connection.execute(
                        text(
                            "SELECT rank, project FROM public.student_preference "
                            "WHERE student = :student_id AND course = :course_id"
                        ),
                        {"student_id": student_id, "course_id": int(course.id)},
                    ).all()
                }
                titles = {str(p.id): str(p.title) for p in projects}
                slot_count = min(PREFERENCE_SLOTS, len(projects))
                forms.append(
                    CoursePreferenceForm(
                        course_id=str(course.id),
                        course_label=f"{course.code} · {course.name} ({course.term})",
                        preferences_open=bool(course.preferences_open),
                        slot_count=slot_count,
                        options=[
                            ProjectOption(id=str(p.id), title=str(p.title))
                            for p in projects
                        ],
                        slots=[
                            PreferenceSlot(
                                rank=rank,
                                label=_RANK_LABELS[rank],
                                selected=saved.get(rank, ""),
                                selected_title=titles.get(saved.get(rank, ""), ""),
                            )
                            for rank in range(1, slot_count + 1)
                        ],
                        submitted=bool(saved),
                    )
                )
        return forms
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


def _parse_project_id(value: str) -> int:
    value = str(value).strip()
    if not value.isdigit() or len(value) > 19:
        raise ValueError("Choose a project for every rank.")
    return int(value)


def save_student_preferences(
    student_id: int, course_id: str | int, choices: list[str]
) -> None:
    """Replace this student's ranking for one course.

    Rules: preferences must be open, the student must be enrolled, every rank
    must be filled, no project twice, and every project must be visible to
    the course.
    """
    _validate_user_id(student_id)
    course_id = parse_course_id(course_id)
    project_ids = [_parse_project_id(c) for c in choices]
    if len(set(project_ids)) != len(project_ids):
        raise ValueError("Each project can only be ranked once.")
    try:
        with _transaction() as session:
            _require_active_student(session, student_id)
            course = session.execute(
                text(
                    "SELECT c.preferences_open FROM public.courses c "
                    "JOIN public.course_enrollments e ON e.course_id = c.id "
                    "AND e.student_id = :student_id "
                    "WHERE c.id = :course_id FOR SHARE OF c"
                ),
                {"student_id": student_id, "course_id": course_id},
            ).first()
            if course is None:
                raise PermissionError("You are not enrolled in this course.")
            if not course.preferences_open:
                raise ValueError("Preferences are closed for this course.")
            visible = {
                int(r.id)
                for r in session.execute(
                    text(_VISIBLE_IN_COURSE), {"course_id": course_id}
                ).all()
            }
            expected = min(PREFERENCE_SLOTS, len(visible))
            if len(project_ids) != expected:
                raise ValueError("Choose a project for every rank.")
            if not set(project_ids) <= visible:
                raise ValueError("One of the chosen projects is not available.")
            session.execute(
                text(
                    "DELETE FROM public.student_preference "
                    "WHERE student = :student_id AND course = :course_id"
                ),
                {"student_id": student_id, "course_id": course_id},
            )
            for rank, project_id in enumerate(project_ids, start=1):
                session.execute(
                    text(
                        "INSERT INTO public.student_preference "
                        "(student, project, course, rank) "
                        "VALUES (:student_id, :project_id, :course_id, :rank)"
                    ),
                    {
                        "student_id": student_id,
                        "project_id": project_id,
                        "course_id": course_id,
                        "rank": rank,
                    },
                )
    except IntegrityError as e:
        # The current unique constraints are (student, rank) and
        # (student, project) across ALL courses, so a student who already
        # ranked in another course hits this. See PR notes.
        logging.exception(f"Error: {e}")
        raise ValueError(
            "You already have preferences saved in another course. "
            "Ranking in more than one course isn't supported yet."
        ) from e
