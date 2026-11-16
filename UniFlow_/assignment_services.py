import reflex as rx

import logging
from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import _get_engine, _validate_user_id


class Teammate(TypedDict):
    full_name: str
    email: str


class AssignedProject(TypedDict):
    project_id: str
    title: str
    description: str
    sponsor_name: str
    course_label: str
    teammates: list[Teammate]


def get_assignments_for_student(student_id: int) -> list[AssignedProject]:
    """Read the projects this student is assigned to (one per course),
    each with the other students on the same project in the same course."""
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
                    "Only active students can view their assigned project."
                )

            projects = (
                connection.execute(
                    text("""
                    SELECT pa.project, pa.course,
                           p.title, p.description,
                           s.full_name AS sponsor_name,
                           c.code, c.name AS course_name, c.term
                    FROM public.project_assignment AS pa
                    JOIN public.projects AS p ON p.id = pa.project
                    JOIN public.users AS s ON s.id = p.sponsor_id
                    JOIN public.courses AS c ON c.id = pa.course
                    WHERE pa.student = :student_id
                    ORDER BY c.term DESC, c.code, c.id
                """),
                    {"student_id": student_id},
                )
                .mappings()
                .all()
            )

            teammate_rows = (
                connection.execute(
                    text("""
                    SELECT mate.project, mate.course, u.full_name, u.email
                    FROM public.project_assignment AS me
                    JOIN public.project_assignment AS mate
                      ON mate.project = me.project
                     AND mate.course = me.course
                     AND mate.student <> me.student
                    JOIN public.users AS u ON u.id = mate.student
                    WHERE me.student = :student_id
                    ORDER BY u.full_name, u.id
                """),
                    {"student_id": student_id},
                )
                .mappings()
                .all()
            )

        teammates: dict[tuple[int, int], list[Teammate]] = {}
        for row in teammate_rows:
            teammates.setdefault((int(row["project"]), int(row["course"])), []).append(
                Teammate(full_name=str(row["full_name"]), email=str(row["email"]))
            )

        return [
            AssignedProject(
                project_id=str(row["project"]),
                title=str(row["title"]),
                description=str(row["description"] or ""),
                sponsor_name=str(row["sponsor_name"] or ""),
                course_label=f"{row['code']} · {row['course_name']} ({row['term']})",
                teammates=teammates.get(
                    (int(row["project"]), int(row["course"])), []
                ),
            )
            for row in projects
        ]
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise
