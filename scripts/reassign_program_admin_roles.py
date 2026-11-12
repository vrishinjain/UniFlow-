"""Safely reassign four program-admin accounts to faculty and system-admin roles.

Usage (dry-run by default):
    python scripts/reassign_program_admin_roles.py \\
        --faculty-ids FACULTY_ID_1 FACULTY_ID_2 \\
        --system-admin-ids SYSTEM_ADMIN_ID_1 SYSTEM_ADMIN_ID_2

Review the dry-run output, then add --apply to perform the reassignment.
Changed users may need to sign out and back in. Their account status remains unchanged.
"""

import argparse
import logging
import os
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from UniFlow_.user_services import _get_engine


MAX_BIGINT = 9223372036854775807


class ReassignmentError(ValueError):
    """Safe-to-display validation or consistency failure."""


def _validate_ids(values: Iterable[int]) -> list[int]:
    ids = list(values)
    if len(ids) != 2:
        raise ReassignmentError("Exactly two IDs are required for each role.")
    for user_id in ids:
        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or user_id <= 0
            or user_id > MAX_BIGINT
        ):
            raise ReassignmentError(
                "Every ID must be a positive integer within the bigint range."
            )
    return ids


def build_assignments(
    faculty_ids: Iterable[int], system_admin_ids: Iterable[int]
) -> dict[int, str]:
    """Build ID-to-role assignments after validating exactly four unique IDs."""
    faculty = _validate_ids(faculty_ids)
    system_admin = _validate_ids(system_admin_ids)
    assignments = {
        **dict.fromkeys(faculty, "faculty"),
        **dict.fromkeys(system_admin, "system_admin"),
    }
    if len(assignments) != 4:
        raise ReassignmentError("All four user IDs must be distinct.")
    return assignments


def validate_current_users(
    assignments: Mapping[int, str], rows: Iterable[object]
) -> None:
    """Raise unless every requested existing row is still a program_admin."""
    current: dict[int, str] = {}
    for row in rows:
        try:
            if isinstance(row, Mapping):
                user_id = int(row["id"])
                role = str(row["role"])
            else:
                user_id = int(row.id)
                role = str(row.role)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise ReassignmentError(
                "Could not validate the selected user rows."
            ) from error
        current[user_id] = role

    missing = set(assignments) - set(current)
    stale = {
        user_id
        for user_id in assignments
        if current.get(user_id) != "program_admin"
    }
    if missing or stale:
        raise ReassignmentError(
            "One or more selected IDs are missing or no longer have the program_admin role. "
            "No changes were applied."
        )


def _fetch_rows(session: Session, ids: list[int], lock: bool) -> list[object]:
    statement = (
        "SELECT id, role, status FROM public.users "
        "WHERE id IN (:id_0, :id_1, :id_2, :id_3) ORDER BY id"
    )
    if lock:
        statement += " FOR UPDATE"
    parameters = {f"id_{index}": user_id for index, user_id in enumerate(ids)}
    return list(session.execute(text(statement), parameters).all())


def _display_plan(
    assignments: Mapping[int, str], rows: Iterable[object]
) -> None:
    by_id = {int(row.id): row for row in rows}
    print("Planned role reassignment:")
    for user_id in sorted(assignments):
        row = by_id[user_id]
        print(
            f"ID {user_id}: {row.role} -> {assignments[user_id]} "
            f"(status: {row.status}; unchanged)"
        )


def _run_dry_run(assignments: Mapping[int, str]) -> None:
    ids = list(assignments)
    with Session(_get_engine()) as session:
        rows = _fetch_rows(session, ids, lock=False)
    validate_current_users(assignments, rows)
    _display_plan(assignments, rows)
    print("Dry run only; no changes were applied.")


def _run_apply(assignments: Mapping[int, str]) -> None:
    ids = list(assignments)
    with Session(_get_engine()) as session:
        with session.begin():
            rows = _fetch_rows(session, ids, lock=True)
            validate_current_users(assignments, rows)
            for user_id, role in assignments.items():
                updated_id = session.execute(
                    text(
                        "UPDATE public.users SET role = :role "
                        "WHERE id = :id AND role = 'program_admin' RETURNING id"
                    ),
                    {"role": role, "id": user_id},
                ).scalar_one_or_none()
                if updated_id != user_id:
                    raise ReassignmentError(
                        "A selected user changed during reassignment. "
                        "The transaction was rolled back."
                    )
    print("Role reassignment completed. Account statuses were unchanged.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reassign four existing program_admin accounts; dry-run by default."
    )
    parser.add_argument(
        "--faculty-ids",
        nargs=2,
        required=True,
        type=int,
        metavar=("FACULTY_ID_1", "FACULTY_ID_2"),
    )
    parser.add_argument(
        "--system-admin-ids",
        nargs=2,
        required=True,
        type=int,
        metavar=("SYSTEM_ADMIN_ID_1", "SYSTEM_ADMIN_ID_2"),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes after review; default is dry-run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        assignments = build_assignments(args.faculty_ids, args.system_admin_ids)
        if not os.environ.get("REFLEX_DB_URL"):
            raise ReassignmentError(
                "REFLEX_DB_URL is not configured; no changes were applied."
            )
        if args.apply:
            _run_apply(assignments)
        else:
            _run_dry_run(assignments)
    except (ReassignmentError, RuntimeError) as error:
        logging.exception("Unexpected error")
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        logging.exception(f"Error: {error}")
        print(
            "Error: Database operation failed; no changes were applied.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
