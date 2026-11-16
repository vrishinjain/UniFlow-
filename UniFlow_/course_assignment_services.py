import reflex as rx

import csv
import io
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from UniFlow_.courses_services import _owned_course, parse_course_id
from UniFlow_.user_services import _transaction, _validate_user_id


class AssignmentCourseContext(TypedDict):
    name: str
    code: str
    term: str


def _require_course_access(
    session: Session, actor_id: int, course_id: int
) -> AssignmentCourseContext:
    _validate_user_id(actor_id)
    course_id = parse_course_id(course_id)
    account = session.execute(
        text(
            "SELECT role, status, must_change_password FROM public.users "
            "WHERE id = :actor_id FOR SHARE"
        ),
        {"actor_id": actor_id},
    ).first()
    if (
        account is None
        or account.status != "active"
        or account.must_change_password
        or account.role not in {"faculty", "system_admin"}
    ):
        raise PermissionError("Course assignment access denied.")
    if account.role == "faculty":
        try:
            course = _owned_course(session, actor_id, course_id)
        except ValueError as exc:
            raise PermissionError("Course assignment access denied.") from exc
    else:
        course = session.execute(
            text(
                "SELECT name, code, term FROM public.courses "
                "WHERE id = :course_id FOR UPDATE"
            ),
            {"course_id": course_id},
        ).first()
        if course is None:
            raise PermissionError("Course assignment access denied.")
    return AssignmentCourseContext(
        name=str(course.name), code=str(course.code), term=str(course.term)
    )


def get_assignment_course_context(
    actor_id: int, course_id: int
) -> AssignmentCourseContext:
    """Return fresh course labels only after checking live account and course access."""
    _validate_user_id(actor_id)
    course_id = parse_course_id(course_id)
    with _transaction() as session:
        return _require_course_access(session, actor_id, course_id)


def export_course_preferences_csv(faculty_id: int, course_id: int) -> str:
    """Export currently enrolled submitters for an owning faculty member or admin."""
    _validate_user_id(faculty_id)
    course_id = parse_course_id(course_id)
    with _transaction() as session:
        _require_course_access(session, faculty_id, course_id)
        rows = (
            session.execute(
                text(
                    "SELECT u.email AS student, "
                    "MAX(CASE WHEN sp.rank = 1 THEN p.title END) AS choice_1, "
                    "MAX(CASE WHEN sp.rank = 2 THEN p.title END) AS choice_2, "
                    "MAX(CASE WHEN sp.rank = 3 THEN p.title END) AS choice_3 "
                    "FROM public.course_enrollments e "
                    "JOIN public.users u ON u.id = e.student_id "
                    "JOIN public.student_preference sp "
                    "ON sp.student = e.student_id AND sp.course = e.course_id "
                    "LEFT JOIN public.projects p ON p.id = sp.project "
                    "WHERE e.course_id = :course_id "
                    "GROUP BY u.id, u.email ORDER BY u.email"
                ),
                {"course_id": course_id},
            )
            .mappings()
            .all()
        )
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["student", "choice_1", "choice_2", "choice_3"])
        for row in rows:
            writer.writerow(
                [
                    row["student"],
                    row["choice_1"],
                    row["choice_2"],
                    row["choice_3"],
                ]
            )
        return output.getvalue()


ASSIGNMENT_MAX_BYTES = 1_048_576


class AssignmentTextLine(TypedDict):
    line: int
    text: str
    email: str
    title: str
    reason: str


class SkippedAssignmentLine(TypedDict):
    line: int
    text: str
    reason: str


class ValidAssignment(TypedDict):
    student: int
    project: int


class AssignmentPreview(TypedDict):
    valid: list[ValidAssignment]
    skipped: list[SkippedAssignmentLine]


class AssignmentImportResult(TypedDict):
    saved: int
    skipped: list[SkippedAssignmentLine]
    confirmation_required: bool
    existing_count: int
    snapshot: str
    message: str


def decode_assignment_file(filename: str, data: bytes) -> str:
    """Validate one bounded UTF-8 text file without database access."""
    if not isinstance(filename, str) or Path(filename).suffix.lower() != ".txt":
        raise ValueError("Choose one UTF-8 .txt file.")
    if not isinstance(data, bytes):
        raise ValueError("The file must contain UTF-8 bytes.")
    if len(data) > ASSIGNMENT_MAX_BYTES:
        raise ValueError("The file exceeds 1 MB. Nothing was changed.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The file must use UTF-8 encoding. Nothing was changed."
        ) from exc


def parse_assignment_text(content: str) -> list[AssignmentTextLine]:
    """Pure parser; retain source text and split on the LAST literal delimiter."""
    if not isinstance(content, str):
        raise ValueError("Assignments must be UTF-8 text.")
    try:
        size = len(content.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("Assignments must be UTF-8 text.") from exc
    if size > ASSIGNMENT_MAX_BYTES:
        raise ValueError("The file exceeds 1 MB. Nothing was changed.")
    parsed: list[AssignmentTextLine] = []
    for number, original in enumerate(
        content.removeprefix("\ufeff").splitlines(), 1
    ):
        if not original.strip():
            continue
        parts = original.rsplit(" joins ", 1)
        email = parts[0].strip().lower() if len(parts) == 2 else ""
        title = parts[1].strip() if len(parts) == 2 else ""
        reason = ""
        if len(parts) != 2 or "\x00" in original:
            reason = "Line format not recognized"
        parsed.append(
            AssignmentTextLine(
                line=number,
                text=original,
                email=email,
                title=title,
                reason=reason,
            )
        )
    return parsed


def _validate_assignment_text(
    session: Session, course_id: int, content: str
) -> AssignmentPreview:
    entries = parse_assignment_text(content)
    emails = sorted(
        {
            entry["email"]
            for entry in entries
            if entry["email"] and "\x00" not in entry["email"]
        }
    )
    accounts: dict[str, list[tuple[int, str]]] = {}
    if emails:
        users = session.execute(
            text(
                "SELECT id, lower(btrim(email)) AS email, role FROM public.users "
                "WHERE lower(btrim(email)) = ANY(:emails) FOR SHARE"
            ),
            {"emails": emails},
        ).all()
        for user in users:
            accounts.setdefault(str(user.email), []).append(
                (int(user.id), str(user.role))
            )
    enrolled = {
        int(row.student_id)
        for row in session.execute(
            text(
                "SELECT student_id FROM public.course_enrollments "
                "WHERE course_id = :course_id FOR SHARE"
            ),
            {"course_id": course_id},
        ).all()
    }
    projects: dict[str, set[int]] = {}
    for project in session.execute(
        text(
            "SELECT p.id, p.title FROM public.projects p "
            "JOIN public.project_course_visibility v ON v.project_id = p.id "
            "WHERE v.course_id = :course_id AND p.status = 'accepted' FOR SHARE OF p, v"
        ),
        {"course_id": course_id},
    ).all():
        projects.setdefault(str(project.title), set()).add(int(project.id))
    seen: set[int] = set()
    valid: list[ValidAssignment] = []
    skipped: list[SkippedAssignmentLine] = []
    for entry in entries:
        matches = accounts.get(entry["email"], [])
        student_id = matches[0][0] if len(matches) == 1 else 0
        repeated = student_id in seen if student_id else False
        if student_id:
            seen.add(student_id)
        reason = (
            "Student appears more than once in the file"
            if repeated
            else entry["reason"]
        )
        if not reason:
            if not student_id:
                reason = "Unknown student"
            elif student_id not in enrolled:
                reason = "Student not enrolled in this course"
            else:
                project_ids = projects.get(entry["title"], set())
                if not project_ids:
                    reason = "Project not visible to this course"
                elif len(project_ids) > 1:
                    reason = "Project title is ambiguous"
                else:
                    valid.append(
                        ValidAssignment(
                            student=student_id, project=next(iter(project_ids))
                        )
                    )
        if reason:
            skipped.append(
                SkippedAssignmentLine(
                    line=entry["line"], text=entry["text"], reason=reason
                )
            )
    return AssignmentPreview(valid=valid, skipped=skipped)


def preview_course_assignments(
    actor_id: int, course_id: int, content: str
) -> AssignmentPreview:
    """Authorized, read-only validation: SELECTs and locks only, never assignments writes."""
    course_id = parse_course_id(course_id)
    with _transaction() as session:
        _require_course_access(session, actor_id, course_id)
        return _validate_assignment_text(session, course_id, content)


def _assignment_snapshot(session: Session, course_id: int) -> tuple[int, str]:
    rows = session.execute(
        text(
            "SELECT student, project, assigned_by, assigned_at FROM public.project_assignment "
            "WHERE course = :course_id ORDER BY student, project FOR UPDATE"
        ),
        {"course_id": course_id},
    ).all()
    serialized = [
        [
            row.student,
            row.project,
            row.assigned_by,
            row.assigned_at.isoformat()
            if row.assigned_at is not None
            else None,
        ]
        for row in rows
    ]
    digest = hashlib.sha256(
        json.dumps(serialized, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return len(rows), digest


def save_course_assignments(
    actor_id: int,
    course_id: int,
    content: str,
    *,
    replace: bool = False,
    expected_snapshot: str = "",
    context_is_current: Callable[[], bool] | None = None,
) -> AssignmentImportResult:
    """Revalidate original text and atomically save; stale confirmations never overwrite."""
    course_id = parse_course_id(course_id)
    with _transaction() as session:
        _require_course_access(session, actor_id, course_id)
        preview = _validate_assignment_text(session, course_id, content)
        count, snapshot = _assignment_snapshot(session, course_id)
        if context_is_current is not None and not context_is_current():
            raise PermissionError(
                "Assignment import context changed. Nothing was changed."
            )
        result = AssignmentImportResult(
            saved=0,
            skipped=preview["skipped"],
            confirmation_required=False,
            existing_count=count,
            snapshot=snapshot,
            message="No valid rows to import",
        )
        if not preview["valid"]:
            return result
        # Even a now-empty course must be reconfirmed if its approved snapshot changed.
        stale = replace and (
            not expected_snapshot or expected_snapshot != snapshot
        )
        if stale or (count and not replace):
            result["confirmation_required"] = True
            result["message"] = (
                "Assignments changed. Review the updated confirmation."
                if stale
                else ""
            )
            return result
        _require_course_access(session, actor_id, course_id)
        if context_is_current is not None and not context_is_current():
            raise PermissionError(
                "Assignment import context changed. Nothing was changed."
            )
        if replace:
            session.execute(
                text(
                    "DELETE FROM public.project_assignment WHERE course = :course_id"
                ),
                {"course_id": course_id},
            )
        session.execute(
            text(
                "INSERT INTO public.project_assignment (student, project, course, assigned_by) "
                "VALUES (:student, :project, :course_id, :actor_id)"
            ),
            [
                {
                    "student": row["student"],
                    "project": row["project"],
                    "course_id": course_id,
                    "actor_id": actor_id,
                }
                for row in preview["valid"]
            ],
        )
        if context_is_current is not None and not context_is_current():
            raise PermissionError(
                "Assignment import context changed. Nothing was changed."
            )
        result["saved"] = len(preview["valid"])
        result["message"] = (
            f"Saved {result['saved']} assignments. Skipped {len(result['skipped'])} rows."
        )
        return result
