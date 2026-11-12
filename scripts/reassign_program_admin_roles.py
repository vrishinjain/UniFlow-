"""Fixed role reassignment for IDs 18, 19, 20, and 32.

Mapping: 18 and 19 to faculty; 20 and 32 to system_admin. Only roles change;
account statuses remain untouched. Signed-in users may need to sign out and in.
Run intentionally later with: python scripts/reassign_program_admin_roles.py
"""

import os
import sys
from pathlib import Path

repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import logging


ROLE_ASSIGNMENTS: dict[int, str] = {
    18: "faculty",
    19: "faculty",
    20: "system_admin",
    32: "system_admin",
}


class ReassignmentError(ValueError):
    """Safe-to-display validation or consistency failure."""


def main() -> int:
    if not os.environ.get("REFLEX_DB_URL"):
        print("Error: REFLEX_DB_URL is not configured.", file=sys.stderr)
        return 1

    try:
        from UniFlow_.user_services import _get_engine

        user_ids = list(ROLE_ASSIGNMENTS)
        parameters = {
            f"id_{index}": user_id for index, user_id in enumerate(user_ids)
        }
        with Session(_get_engine()) as session:
            with session.begin():
                rows = session.execute(
                    text(
                        "SELECT id,role FROM public.users "
                        "WHERE id IN (:id_0,:id_1,:id_2,:id_3) "
                        "ORDER BY id FOR UPDATE"
                    ),
                    parameters,
                ).all()
                current_roles = {int(row.id): str(row.role) for row in rows}
                if (
                    len(rows) != len(ROLE_ASSIGNMENTS)
                    or set(current_roles) != set(ROLE_ASSIGNMENTS)
                    or any(
                        current_roles.get(user_id) != "program_admin"
                        for user_id in ROLE_ASSIGNMENTS
                    )
                ):
                    raise ReassignmentError(
                        "Expected users are missing or no longer have the "
                        "program_admin role; no changes were applied."
                    )

                for user_id, role in ROLE_ASSIGNMENTS.items():
                    updated_ids = (
                        session.execute(
                            text(
                                "UPDATE public.users SET role=:role "
                                "WHERE id=:id AND role='program_admin' RETURNING id"
                            ),
                            {"role": role, "id": user_id},
                        )
                        .scalars()
                        .all()
                    )
                    if updated_ids != [user_id]:
                        raise ReassignmentError(
                            "A user could not be updated exactly as expected; "
                            "the transaction was rolled back."
                        )
    except ReassignmentError as error:
        logging.exception("Unexpected error")
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        logging.exception("Unexpected error")
        print(
            "Error: Database operation failed; no success was reported.",
            file=sys.stderr,
        )
        return 1
    except Exception:
        logging.exception("Unexpected error")
        print(
            "Error: Reassignment could not be completed safely.",
            file=sys.stderr,
        )
        return 1

    for user_id, role in ROLE_ASSIGNMENTS.items():
        print(f"ID {user_id}: {role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
