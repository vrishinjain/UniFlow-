"""Safely preview or explicitly delete one seeded project assignment.

Use the assignment ID printed by the seed script (replace the illustrative
ASSIGNMENT_ID placeholder below):

    python scripts/delete_project_assignment.py --assignment-id ASSIGNMENT_ID
    python scripts/delete_project_assignment.py --assignment-id ASSIGNMENT_ID --confirm-delete

Only undo a row that scripts/seed_project_assignment.py reported as CREATED,
not one it reported as SKIPPED. An ID and matching assignment mapping cannot
independently prove that the seed created the row. Seeding and deleting restores
this one assignment's absence only if it was newly created and remains
unchanged; it does not restore database sequence ID consumption or audit logs,
and cannot undo effects of others using the assignment between operations.
This is not a full database reset.
"""

import argparse
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


_SELECT_ASSIGNMENT = text(
    "SELECT id, student, course, project, assigned_by "
    "FROM public.project_assignment WHERE id = :assignment_id"
)
_SELECT_LOCKED_ASSIGNMENT = text(
    "SELECT id, student, course, project, assigned_by "
    "FROM public.project_assignment WHERE id = :assignment_id FOR UPDATE"
)
_SELECT_SIDE_EFFECTS = text(
    "SELECT "
    "EXISTS ("
    "SELECT 1 FROM pg_constraint "
    "WHERE confrelid = 'public.project_assignment'::regclass AND contype = 'f'"
    ") AS has_inbound_foreign_keys, "
    "EXISTS ("
    "SELECT 1 FROM pg_trigger "
    "WHERE tgrelid = 'public.project_assignment'::regclass AND NOT tgisinternal"
    ") AS has_custom_triggers"
)
_DELETE_ASSIGNMENT = text(
    "DELETE FROM public.project_assignment "
    "WHERE id = :assignment_id AND student = :student_id "
    "AND course = :course_id AND project = :project_id "
    "AND assigned_by = :assigned_by_id "
    "RETURNING id, student, course, project, assigned_by"
)


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "must be a positive integer"
        ) from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _mapping_parameters(assignment_id: int) -> dict[str, int]:
    return {
        "assignment_id": assignment_id,
        "student_id": STUDENT_ID,
        "course_id": COURSE_ID,
        "project_id": PROJECT_ID,
        "assigned_by_id": ASSIGNED_BY_ID,
    }


def _validate_assignment(row: dict[str, int], assignment_id: int) -> None:
    expected = {
        "student": STUDENT_ID,
        "course": COURSE_ID,
        "project": PROJECT_ID,
        "assigned_by": ASSIGNED_BY_ID,
    }
    mismatches = [
        f"{field}={row[field]} (expected {value})"
        for field, value in expected.items()
        if row[field] != value
    ]
    if mismatches:
        raise ValueError(
            f"Assignment id={assignment_id} does not match the fixed mapping: "
            f"{', '.join(mismatches)}. No changes were made."
        )


def _require_database_url() -> None:
    if not os.environ.get("REFLEX_DB_URL"):
        raise RuntimeError("REFLEX_DB_URL is not configured.")


def preview_assignment(assignment_id: int) -> dict[str, int] | None:
    """Read and validate the requested assignment without changing the database."""
    _require_database_url()
    with _get_engine().connect() as connection:
        result = (
            connection.execute(
                _SELECT_ASSIGNMENT, {"assignment_id": assignment_id}
            )
            .mappings()
            .first()
        )
    if result is None:
        return None
    row = dict(result)
    _validate_assignment(row, assignment_id)
    return row


def delete_assignment(assignment_id: int) -> dict[str, int] | None:
    """Delete the exact mapped row in one transaction, or return if it is absent."""
    _require_database_url()
    with _get_engine().begin() as connection:
        result = (
            connection.execute(
                _SELECT_LOCKED_ASSIGNMENT, {"assignment_id": assignment_id}
            )
            .mappings()
            .first()
        )
        if result is None:
            return None

        row = dict(result)
        _validate_assignment(row, assignment_id)

        side_effects = connection.execute(_SELECT_SIDE_EFFECTS).mappings().one()
        if side_effects["has_inbound_foreign_keys"]:
            raise RuntimeError(
                "Deletion refused: public.project_assignment has inbound foreign "
                "key constraints requiring review. No changes were made."
            )
        if side_effects["has_custom_triggers"]:
            raise RuntimeError(
                "Deletion refused: public.project_assignment has custom triggers "
                "requiring review. No changes were made."
            )

        deleted_rows = (
            connection.execute(
                _DELETE_ASSIGNMENT, _mapping_parameters(assignment_id)
            )
            .mappings()
            .all()
        )
        if len(deleted_rows) != 1:
            raise RuntimeError(
                "Deletion did not return exactly one matching row; transaction "
                "rolled back."
            )
        deleted = dict(deleted_rows[0])
        _validate_assignment(deleted, assignment_id)

    return deleted


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preview one fixed project assignment; deletion requires the explicit "
            "--confirm-delete option."
        )
    )
    parser.add_argument(
        "--assignment-id",
        required=True,
        type=_positive_integer,
        help="the generated row ID printed by the seed script",
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="perform the exact-match deletion instead of a read-only preview",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.confirm_delete:
            deleted = delete_assignment(args.assignment_id)
            if deleted is None:
                print(
                    f"No matching project assignment id={args.assignment_id}; "
                    "no changes were made."
                )
                return 0
            print(
                f"Deleted project assignment id={deleted['id']} "
                f"(student={deleted['student']}, course={deleted['course']}, "
                f"project={deleted['project']}, "
                f"assigned_by={deleted['assigned_by']})."
            )
            return 0

        row = preview_assignment(args.assignment_id)
        if row is None:
            print(
                f"No matching project assignment id={args.assignment_id}; "
                "no changes were made."
            )
            return 0
        print(
            f"Target project assignment id={row['id']} "
            f"(student={row['student']}, course={row['course']}, "
            f"project={row['project']}, assigned_by={row['assigned_by']})."
        )
        print("Read-only preview; no changes were made.")
        print(
            "Use --confirm-delete to request deletion after verifying the seed reported CREATED."
        )
        return 0
    except (RuntimeError, ValueError) as error:
        print(f"Project assignment deletion failed: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print(
            "Project assignment operation failed: database operation failed; "
            "no success was reported.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
