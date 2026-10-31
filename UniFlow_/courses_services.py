import reflex as rx

import logging
from pathlib import Path
from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import (
    _get_engine,
    _transaction,
    _validate_user_id,
    CourseEmailEntry,
    BulkEmailParse,
    _validate_bulk_addresses,
    parse_bulk_email_file,
)
from sqlalchemy.orm import Session
import re


class CourseRow(TypedDict):
    id: int
    name: str
    code: str
    term: str
    faculty_id: int
    created_at: str


def _course_text(value: str, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f"{label} must be {maximum} characters or fewer.")
    if "\x00" in value:
        raise ValueError(f"{label} must not contain null characters.")
    return value


def list_faculty_courses(faculty_id: int) -> list[CourseRow]:
    """Return only this faculty member's courses, newest first."""
    _validate_user_id(faculty_id)
    try:
        with _get_engine().connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, name, code, term, faculty_id, created_at "
                    "FROM public.courses WHERE faculty_id = :faculty_id "
                    "AND EXISTS (SELECT 1 FROM public.users "
                    "WHERE users.id = :faculty_id AND role = 'faculty' AND status = 'active') "
                    "ORDER BY created_at DESC, id DESC"
                ),
                {"faculty_id": faculty_id},
            ).all()
        return [
            CourseRow(
                id=int(row.id),
                name=str(row.name).strip(),
                code=str(row.code).strip(),
                term=str(row.term).strip(),
                faculty_id=int(row.faculty_id),
                created_at=row.created_at.strftime("%b %d, %Y"),
            )
            for row in rows
        ]
    except Exception as e:
        logging.exception(f"Error: {e}")
        raise


def create_course(faculty_id: int, name: str, code: str, term: str) -> int:
    """Create under an active faculty account's row lock, without changing schema."""
    _validate_user_id(faculty_id)
    name = _course_text(name, "Course name", 200)
    code = _course_text(code, "Course code", 50)
    term = _course_text(term, "Term", 100)
    with _transaction() as session:
        faculty = session.execute(
            text(
                "SELECT id, role, status FROM public.users "
                "WHERE id = :faculty_id FOR UPDATE"
            ),
            {"faculty_id": faculty_id},
        ).first()
        if (
            faculty is None
            or faculty.role != "faculty"
            or faculty.status != "active"
        ):
            raise PermissionError(
                "Only active faculty members may create courses."
            )
        parameters = {
            "faculty_id": faculty_id,
            "name": name,
            "code": code,
            "term": term,
        }
        existing = session.execute(
            text(
                "SELECT id FROM public.courses WHERE faculty_id = :faculty_id "
                "AND lower(btrim(code)) = lower(btrim(:code)) "
                "AND lower(btrim(term)) = lower(btrim(:term)) LIMIT 1"
            ),
            {"faculty_id": faculty_id, "code": code, "term": term},
        ).first()
        if existing is not None:
            raise ValueError("You already have this course for this term.")
        course_id = session.execute(
            text(
                "INSERT INTO public.courses (name, code, term, faculty_id) "
                "VALUES (:name, :code, :term, :faculty_id) RETURNING id"
            ),
            parameters,
        ).scalar_one()
    return int(course_id)


class EnrolledStudent(TypedDict):
    id: int
    full_name: str
    email: str


class CourseDetail(TypedDict):
    name: str
    code: str
    term: str
    students: list[EnrolledStudent]


class EnrollmentSummary(TypedDict):
    added: list[CourseEmailEntry]
    already_enrolled: list[CourseEmailEntry]
    no_account: list[CourseEmailEntry]
    not_student: list[CourseEmailEntry]
    not_approved: list[CourseEmailEntry]
    invalid_lines: list[CourseEmailEntry]


def parse_course_id(value: str | int) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Invalid course ID.")
    if not re.fullmatch(r"[0-9]{1,19}", str(value)):
        raise ValueError("Invalid course ID.")
    course_id = int(value)
    if not 0 < course_id <= 9223372036854775807:
        raise ValueError("Invalid course ID.")
    return course_id


_COURSE_SCOPE = (
    "c.id = :course_id AND c.faculty_id = :authenticated_faculty_id "
    "AND EXISTS (SELECT 1 FROM public.users f "
    "WHERE f.id = :authenticated_faculty_id AND f.role = 'faculty' "
    "AND f.status = 'active')"
)


def _owned_course(session: Session, faculty_id: int, course_id: int):
    parameters = {
        "authenticated_faculty_id": faculty_id,
        "course_id": course_id,
    }
    faculty = session.execute(
        text(
            "SELECT role, status FROM public.users WHERE id = :authenticated_faculty_id FOR SHARE"
        ),
        parameters,
    ).first()
    if (
        faculty is None
        or faculty.role != "faculty"
        or faculty.status != "active"
    ):
        raise PermissionError("Faculty access was lost.")
    course = session.execute(
        text(
            f"SELECT c.name, c.code, c.term FROM public.courses c WHERE {_COURSE_SCOPE} FOR UPDATE OF c"
        ),
        parameters,
    ).first()
    if course is None:
        raise ValueError("Course not found or unavailable to your account.")
    return course


def get_faculty_course_detail(
    authenticated_faculty_id: int, course_id: str | int
) -> CourseDetail:
    _validate_user_id(authenticated_faculty_id)
    course_id = parse_course_id(course_id)
    parameters = {
        "authenticated_faculty_id": authenticated_faculty_id,
        "course_id": course_id,
    }
    with _transaction() as session:
        course = _owned_course(session, authenticated_faculty_id, course_id)
        rows = session.execute(
            text(
                "SELECT u.id, u.full_name, u.email FROM public.course_enrollments e "
                "JOIN public.users u ON u.id = e.student_id "
                "JOIN public.courses c ON c.id = e.course_id "
                f"WHERE {_COURSE_SCOPE} ORDER BY lower(u.full_name), lower(u.email), u.id"
            ),
            parameters,
        ).all()
        return CourseDetail(
            name=str(course.name),
            code=str(course.code),
            term=str(course.term),
            students=[
                EnrolledStudent(
                    id=int(row.id),
                    full_name=str(row.full_name),
                    email=str(row.email),
                )
                for row in rows
            ],
        )


def _enroll_course_addresses(
    faculty_id: int, course_id: str | int, parsed: BulkEmailParse
) -> EnrollmentSummary:
    _validate_user_id(faculty_id)
    course_id = parse_course_id(course_id)
    summary = EnrollmentSummary(
        added=[],
        already_enrolled=[],
        no_account=[],
        not_student=[],
        not_approved=[],
        invalid_lines=parsed["invalid_lines"],
    )
    entries = parsed["addresses"]
    raw_addresses = [entry["email"] for entry in entries]
    emails = (
        _validate_bulk_addresses(raw_addresses)
        if entries or not parsed["invalid_lines"]
        else []
    )
    first_entries: dict[str, CourseEmailEntry] = {}
    for entry in entries:
        address = entry["email"].strip().lower()
        first_entries.setdefault(
            address,
            CourseEmailEntry(
                email=address, line=entry["line"], reason=entry["reason"]
            ),
        )
    entries = [first_entries[email] for email in emails]
    parameters = {
        "authenticated_faculty_id": faculty_id,
        "course_id": course_id,
        "emails": emails,
    }
    with _transaction() as session:
        _owned_course(session, faculty_id, course_id)
        if not entries:
            return summary
        rows = session.execute(
            text(
                "SELECT u.id, lower(btrim(u.email)) AS email, u.role, u.status FROM public.users u "
                "WHERE lower(btrim(u.email)) = ANY(:emails) "
                f"AND EXISTS (SELECT 1 FROM public.courses c WHERE {_COURSE_SCOPE}) "
                "FOR SHARE OF u"
            ),
            parameters,
        ).all()
        accounts: dict[str, list[tuple[int, str, str]]] = {}
        for row in rows:
            accounts.setdefault(str(row.email).strip().lower(), []).append(
                (int(row.id), str(row.role), str(row.status))
            )
        eligible: dict[int, CourseEmailEntry] = {}
        for entry in entries:
            matches = accounts.get(entry["email"], [])
            if not matches:
                summary["no_account"].append(entry)
            elif len(matches) != 1:
                summary["not_student"].append(
                    CourseEmailEntry(
                        **{
                            **entry,
                            "reason": "Ambiguous email matches multiple accounts; enrollment skipped",
                        }
                    )
                )
            elif matches[0][1] != "student":
                summary["not_student"].append(entry)
            elif matches[0][2] != "active":
                summary["not_approved"].append(entry)
            else:
                eligible[matches[0][0]] = entry
        if eligible:
            inserted = session.execute(
                text(
                    "INSERT INTO public.course_enrollments (course_id, student_id) "
                    "SELECT c.id, u.id FROM public.courses c "
                    "JOIN public.users u ON u.id = ANY(:student_ids) "
                    "AND u.role = 'student' AND u.status = 'active' "
                    f"WHERE {_COURSE_SCOPE} "
                    "ON CONFLICT (course_id, student_id) DO NOTHING RETURNING student_id"
                ),
                {**parameters, "student_ids": list(eligible)},
            ).all()
            added_ids = {int(row.student_id) for row in inserted}
            for student_id, entry in eligible.items():
                category = (
                    "added" if student_id in added_ids else "already_enrolled"
                )
                summary[category].append(entry)
    return summary


def enroll_course_student(
    authenticated_faculty_id: int, course_id: str | int, email: str
) -> EnrollmentSummary:
    address = _validate_bulk_addresses([email])[0]
    return _enroll_course_addresses(
        authenticated_faculty_id,
        course_id,
        BulkEmailParse(
            addresses=[CourseEmailEntry(email=address, line=1, reason="")],
            invalid_lines=[],
        ),
    )


def bulk_enroll_course_students(
    authenticated_faculty_id: int,
    course_id: str | int,
    filename: str,
    data: bytes,
) -> EnrollmentSummary:
    if not isinstance(filename, str) or Path(filename).suffix.lower() != ".txt":
        raise ValueError("Choose one UTF-8 .txt file.")
    parsed = parse_bulk_email_file(filename, data)
    return _enroll_course_addresses(authenticated_faculty_id, course_id, parsed)


def remove_course_student(
    authenticated_faculty_id: int, course_id: str | int, student_id: int
) -> bool:
    _validate_user_id(authenticated_faculty_id)
    _validate_user_id(student_id)
    course_id = parse_course_id(course_id)
    with _transaction() as session:
        _owned_course(session, authenticated_faculty_id, course_id)
        removed = session.execute(
            text(
                "DELETE FROM public.course_enrollments e USING public.courses c "
                f"WHERE e.course_id = c.id AND {_COURSE_SCOPE} "
                "AND e.student_id = :student_id RETURNING e.student_id"
            ),
            {
                "authenticated_faculty_id": authenticated_faculty_id,
                "course_id": course_id,
                "student_id": student_id,
            },
        ).first()
    return removed is not None
