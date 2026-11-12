"""Migration artifact for removing the ``program_admin`` role constraint.

The database constraint replacement removes ``program_admin`` and changes no
account records. This change was ALREADY APPLIED to the current connected
database; do not run it again there.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

UPGRADE_SQL = """BEGIN;
LOCK TABLE public.users IN ACCESS EXCLUSIVE MODE;
ALTER TABLE public.users DROP CONSTRAINT users_role_check;
ALTER TABLE public.users ADD CONSTRAINT users_role_check CHECK (role IN ('system_admin', 'faculty', 'student', 'sponsor'));
COMMIT;"""


def upgrade(connection: Connection) -> None:
    """Apply the upgrade using a caller-provided idle connection."""
    statements = UPGRADE_SQL.strip().split(";")
    with connection.begin():
        for statement in statements[1:-2]:
            connection.execute(text(statement.strip()))
