"""Explicitly seed one project assignment after validating its prerequisites.

Fixed mapping: project_assignment.student=17, course=1, project=6,
assigned_by=14. The database column order differs from this ID list, so the
INSERT names every column explicitly. This script writes to the database
configured by REFLEX_DB_URL only when run; it has not been executed.

Run later with: python scripts/seed_project_assignment.py

This script does not create users, courses, enrollments, visibility links, or
student preferences.
"""

import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from UniFlow_.user_services import _get_engine


STUDENT_ID = 17
COURSE_ID = 1
PROJECT_ID = 6
ASSIGNED_BY_ID = 14


def seed_project_assignment() -> tuple[str, int]:
    """Create the fixed assignment, or skip an identical existing assignment."""
    if not os.environ.get("REFLEX_DB_URL"):
        raise RuntimeError("REFLEX_DB_URL is not configured.")

    with _get_engine().begin() as connection:
        prerequisites = (
            connection.execute(
                text(
                    "SELECT s.role AS student_role, s.status AS student_status, "
                    "s.must_change_password AS student_must_change_password, "
                    "c.faculty_id AS course_faculty_id, "
                    "f.role AS faculty_role, f.status AS faculty_status, "
                    "f.must_change_password AS faculty_must_change_password, "
                    "p.status AS project_status "
                    "FROM public.users AS s "
                    "JOIN public.course_enrollments AS e "
                    "ON e.student_id = s.id AND e.course_id = :course_id "
                    "JOIN public.courses AS c ON c.id = e.course_id "
                    "JOIN public.users AS f ON f.id = :assigned_by_id "
                    "JOIN public.projects AS p ON p.id = :project_id "
                    "JOIN public.project_course_visibility AS v "
                    "ON v.project_id = p.id AND v.course_id = c.id "
                    "AND v.shared_by = :assigned_by_id "
                    "WHERE s.id = :student_id "
                    "FOR SHARE OF s, e, c, f, p, v"
                ),
                {
                    "student_id": STUDENT_ID,
                    "course_id": COURSE_ID,
                    "project_id": PROJECT_ID,
                    "assigned_by_id": ASSIGNED_BY_ID,
                },
            )
            .mappings()
            .first()
        )

        if prerequisites is None:
            raise ValueError("Assignment prerequisites are not satisfied.")
        if (
            prerequisites["student_role"] != "student"
            or prerequisites["student_status"] != "active"
            or prerequisites["student_must_change_password"]
            or prerequisites["course_faculty_id"] != ASSIGNED_BY_ID
            or prerequisites["faculty_role"] != "faculty"
            or prerequisites["faculty_status"] != "active"
            or prerequisites["faculty_must_change_password"]
            or prerequisites["project_status"] != "accepted"
        ):
            raise ValueError("Assignment prerequisites are not satisfied.")

        inserted_id = connection.execute(
            text(
                "INSERT INTO public.project_assignment "
                "(student, course, project, assigned_by) "
                "VALUES (:student_id, :course_id, :project_id, :assigned_by_id) "
                "ON CONFLICT (student, course) DO NOTHING "
                "RETURNING id"
            ),
            {
                "student_id": STUDENT_ID,
                "course_id": COURSE_ID,
                "project_id": PROJECT_ID,
                "assigned_by_id": ASSIGNED_BY_ID,
            },
        ).scalar_one_or_none()

        if inserted_id is not None:
            result = ("created", int(inserted_id))
        else:
            existing = (
                connection.execute(
                    text(
                        "SELECT id, project, assigned_by "
                        "FROM public.project_assignment "
                        "WHERE student = :student_id AND course = :course_id "
                        "FOR SHARE"
                    ),
                    {"student_id": STUDENT_ID, "course_id": COURSE_ID},
                )
                .mappings()
                .first()
            )
            if (
                existing is None
                or existing["project"] != PROJECT_ID
                or existing["assigned_by"] != ASSIGNED_BY_ID
            ):
                raise ValueError(
                    "A different assignment already exists for this student and course."
                )
            result = ("skipped", int(existing["id"]))

    return result


def main() -> int:
    try:
        action, assignment_id = seed_project_assignment()
    except (RuntimeError, ValueError) as error:
        print(f"Assignment seed failed: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print(
            "Assignment seed failed: database operation failed; transaction rolled back.",
            file=sys.stderr,
        )
        return 1

    print(
        f"{action.capitalize()} project assignment id={assignment_id} "
        f"(student={STUDENT_ID}, course={COURSE_ID}, project={PROJECT_ID}, "
        f"assigned_by={ASSIGNED_BY_ID})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
