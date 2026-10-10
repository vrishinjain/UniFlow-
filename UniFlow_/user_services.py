import reflex as rx

import csv
import io
import logging
import os
import re
import secrets
import string
from pathlib import Path
from typing import TypedDict
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

import bcrypt
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from UniFlow_.user_model import User


__all__ = [
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "change_pending_user_role",
    "verify_password",
    "list_pending_users",
    "list_active_users",
    "activate_user",
    "reject_user",
    "seed_system_admin",
    "parse_bulk_email_file",
    "bulk_approve_emails",
]

_ALLOWED_ROLES = frozenset(
    {"system_admin", "program_admin", "faculty", "student", "sponsor"}
)
_ADMIN_SEED_LOCK = 6143972381094261


@lru_cache(maxsize=1)
def _get_engine() -> Engine:
    # Engine construction is lazy and never initializes or changes the schema.
    if not os.environ.get("REFLEX_DB_URL"):
        raise RuntimeError("Account services are temporarily unavailable.")
    return create_engine(
        make_url(os.environ["REFLEX_DB_URL"]).set(
            drivername="postgresql+psycopg"
        ),
        pool_pre_ping=True,
        hide_parameters=True,
        isolation_level="READ COMMITTED",
    )


@contextmanager
def _transaction() -> Iterator[Session]:
    """Commit on success, roll back on failure, and always close the session."""
    try:
        with Session(_get_engine(), expire_on_commit=False) as session:
            with session.begin():
                yield session
    except IntegrityError as e:
        logging.exception(f"Error: {e}")
        original = e.orig
        sqlstate = getattr(original, "sqlstate", None)
        diagnostic = getattr(original, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)
        if sqlstate == "23505" and constraint == "users_email_key":
            raise ValueError("A user with that email already exists.") from e
        raise
    except SQLAlchemyError as e:
        logging.exception(f"Error: {e}")
        raise


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required and must be non-empty text.")
    if "\x00" in value:
        raise ValueError(f"{label} must not contain null characters.")
    return value.strip()


def _hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password is required and must be non-empty text.")
    try:
        encoded = password.encode("utf-8")
    except UnicodeError as e:
        logging.exception("Unexpected error")
        raise ValueError("Password must be valid UTF-8 text.") from e
    if len(encoded) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes for bcrypt.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")


def _insert_user(
    session: Session,
    full_name: str,
    email: str,
    password_hash: str,
    role: str,
    status: str,
) -> User:
    if (
        session.scalar(select(User.id).where(User.email == email).limit(1))
        is not None
    ):
        raise ValueError("A user with that email already exists.")
    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash,
        role=role,
        status=status,
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def create_user(full_name: str, email: str, password: str, role: str) -> User:
    """Create a pending user; return a detached, fully loaded User after commit.

    Email matching preserves PostgreSQL's case-sensitive text uniqueness; surrounding
    whitespace is stripped consistently on creation and lookup.
    """
    if not isinstance(role, str) or role not in _ALLOWED_ROLES:
        raise ValueError(
            "Invalid role. Expected system_admin, program_admin, faculty, student, or sponsor."
        )
    name = _required_text(full_name, "Full name")
    address = _required_text(email, "Email")
    password_hash = _hash_password(password)
    with _transaction() as session:
        user = _insert_user(
            session, name, address, password_hash, role, "pending"
        )
    return user


def get_user_by_email(email: str) -> User | None:
    """Return the matching user, or None when no matching email exists."""
    address = _required_text(email, "Email")
    with _transaction() as session:
        user = session.scalar(
            select(User).where(User.email == address).limit(1)
        )
    return user


def _validate_user_id(user_id: int) -> None:
    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or not 0 < user_id <= 9223372036854775807
    ):
        raise ValueError(
            "User ID must be a positive integer within the supported range."
        )


def get_user_by_id(user_id: int) -> User | None:
    """Look up the current account by its server-side session identity."""
    _validate_user_id(user_id)
    with _transaction() as session:
        user = session.scalar(
            select(User).from_statement(
                text(
                    "SELECT id, full_name, email, password_hash, role, status, created_at "
                    "FROM public.users WHERE id = :user_id LIMIT 1"
                )
            ),
            {"user_id": user_id},
        )
    return user


def verify_password(password: str, password_hash: str) -> bool:
    """Check bcrypt credentials; malformed hashes and unsupported inputs return False."""
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    if not password or not password_hash:
        return False
    try:
        encoded = password.encode("utf-8")
        if len(encoded) > 72:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        logging.exception("Unexpected error")
        return False


def list_pending_users() -> list[User]:
    """Return all pending users, oldest first, with deterministic ordering."""
    with _transaction() as session:
        users = list(
            session.scalars(
                select(User)
                .where(User.status == "pending")
                .order_by(User.created_at, User.id)
            ).all()
        )
    return users


def list_active_users() -> list[User]:
    """Return detached active-user records in newest-first order."""
    with _transaction() as session:
        rows = session.execute(
            text(
                "SELECT id, full_name, email, role, status, created_at "
                "FROM public.users WHERE status = :status "
                "ORDER BY created_at DESC, id DESC"
            ),
            {"status": "active"},
        ).all()
    return [
        User(
            id=int(row.id),
            full_name=str(row.full_name),
            email=str(row.email),
            password_hash="",
            role=str(row.role),
            status=str(row.status),
            created_at=row.created_at,
        )
        for row in rows
    ]


def change_pending_user_role(user_id: int, role: str) -> User:
    """Change only a pending request's role; reject invalid or stale requests."""
    _validate_user_id(user_id)
    if not isinstance(role, str) or role not in _ALLOWED_ROLES:
        raise ValueError("Choose a valid account role.")
    with _transaction() as session:
        user = session.scalar(
            update(User)
            .where(User.id == user_id, User.status == "pending")
            .values(role=role)
            .returning(User)
        )
        if user is None:
            raise ValueError(
                "This request no longer exists or has already been reviewed. Refresh the list."
            )
    return user


def _set_status(user_id: int, status: str) -> User:
    _validate_user_id(user_id)
    if status not in {"active", "rejected"}:
        raise ValueError("Choose a valid review decision.")
    with _transaction() as session:
        user = session.scalar(
            update(User)
            .where(User.id == user_id, User.status == "pending")
            .values(status=status)
            .returning(User)
        )
        if user is None:
            raise ValueError(
                "This request no longer exists or has already been reviewed. Refresh the list."
            )
    return user


def activate_user(user_id: int) -> User:
    """Activate only a pending request; missing or reviewed IDs raise ValueError."""
    return _set_status(user_id, "active")


def reject_user(user_id: int) -> User:
    """Reject only a pending request; missing or reviewed IDs raise ValueError."""
    return _set_status(user_id, "rejected")


BULK_EMAIL_MAX_BYTES = 1_048_576
BULK_EMAIL_MAX_ADDRESSES = 500


class BulkEmailResult(TypedDict):
    email: str
    password: str
    outcome: str


def _validate_bulk_addresses(addresses: list[str]) -> list[str]:
    if not addresses:
        raise ValueError("The file contains no email addresses.")
    if len(addresses) > BULK_EMAIL_MAX_ADDRESSES:
        raise ValueError(
            "A file may contain at most 500 email addresses. Nothing was changed."
        )
    validated: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(addresses, start=1):
        address = _required_text(value, f"Email at entry {index}")
        local, separator, domain = address.partition("@")
        labels = domain.split(".")
        valid = (
            len(address) <= 254
            and 0 < len(local) <= 64
            and separator == "@"
            and re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+", local)
            is not None
            and not local.startswith(".")
            and not local.endswith(".")
            and ".." not in local
            and len(labels) >= 2
            and all(
                re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label
                )
                is not None
                for label in labels
            )
            and re.fullmatch(
                r"[A-Za-z]{2,63}|xn--[A-Za-z0-9-]{2,59}", labels[-1]
            )
            is not None
        )
        if not valid:
            raise ValueError(
                f"Invalid email at entry {index}: {address}. Nothing was changed."
            )
        if address in seen:
            raise ValueError(
                f"Duplicate email at entry {index}: {address}. Remove duplicates; nothing was changed."
            )
        seen.add(address)
        validated.append(address)
    return validated


def parse_bulk_email_file(filename: str, data: bytes) -> list[str]:
    extension = Path(filename).suffix.lower()
    if extension not in {".txt", ".csv"}:
        raise ValueError("Choose a UTF-8 .txt or one-column .csv file.")
    if len(data) > BULK_EMAIL_MAX_BYTES:
        raise ValueError("The file exceeds 1 MB. Nothing was changed.")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeError as e:
        logging.exception(f"Error: {e}")
        raise ValueError(
            "The file must use UTF-8 encoding. Nothing was changed."
        ) from e
    addresses: list[str] = []
    try:
        rows = (
            csv.reader(io.StringIO(content, newline=""), strict=True)
            if extension == ".csv"
            else ([line] for line in content.splitlines())
        )
        for row_number, row in enumerate(rows, start=1):
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 1:
                raise ValueError(
                    f"Row {row_number} has multiple columns. Use exactly one email column; nothing was changed."
                )
            address = row[0].strip()
            if not addresses and address.lower() == "email":
                # Only the first nonblank row may be a header.
                addresses.append("")
                continue
            addresses.append(address)
    except csv.Error as e:
        logging.exception(f"Error: {e}")
        raise ValueError(
            "The CSV is malformed. Use one email per row; nothing was changed."
        ) from e
    if addresses and addresses[0] == "":
        addresses.pop(0)
    return _validate_bulk_addresses(addresses)


def _temporary_password() -> str:
    alphabet = f"{string.ascii_letters}{string.digits}!@#$%&*-_"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(24))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%&*-_" for c in password)
        ):
            return password


def bulk_approve_emails(
    admin_user_id: int, addresses: list[str]
) -> list[BulkEmailResult]:
    """Return transient credentials only after a successful, all-or-nothing commit."""
    _validate_user_id(admin_user_id)
    emails = _validate_bulk_addresses(addresses)
    results: list[BulkEmailResult] = []
    with _transaction() as session:
        # Serialize against all account writers, including concurrent signups/imports.
        session.execute(
            text("LOCK TABLE public.users IN SHARE ROW EXCLUSIVE MODE")
        )
        admin = session.execute(
            text(
                "SELECT role, status FROM public.users WHERE id = :id FOR UPDATE"
            ),
            {"id": admin_user_id},
        ).first()
        if (
            admin is None
            or admin.role != "system_admin"
            or admin.status != "active"
        ):
            raise PermissionError(
                "Only active system administrators may import accounts."
            )
        rows = session.execute(
            text(
                "SELECT id, email, status FROM public.users WHERE email = ANY(:emails)"
            ),
            {"emails": emails},
        ).all()
        existing = {str(row.email): row for row in rows}
        inserts: list[dict[str, str]] = []
        updates: list[dict[str, str | int]] = []
        for email in emails:
            user = existing.get(email)
            if user is not None and user.status == "active":
                results.append(
                    BulkEmailResult(
                        email=email, password="", outcome="Already approved"
                    )
                )
                continue
            if user is not None and user.status not in {"pending", "rejected"}:
                raise ValueError(
                    "An account has an unsupported status. Nothing was changed."
                )
            password = _temporary_password()
            password_hash = _hash_password(password)
            if user is None:
                local = email.partition("@")[0]
                name = re.sub(r"[._-]+", " ", local).strip() or local
                inserts.append(
                    {"email": email, "name": name, "hash": password_hash}
                )
                outcome = "Created"
            else:
                updates.append({"id": int(user.id), "hash": password_hash})
                outcome = "Reactivated"
            results.append(
                BulkEmailResult(email=email, password=password, outcome=outcome)
            )
        # Recheck the persisted identity immediately before the first write.
        admin = session.execute(
            text(
                "SELECT role, status FROM public.users WHERE id = :id FOR UPDATE"
            ),
            {"id": admin_user_id},
        ).first()
        if (
            admin is None
            or admin.role != "system_admin"
            or admin.status != "active"
        ):
            raise PermissionError(
                "Administrator access was lost. Nothing was changed."
            )
        if inserts:
            session.execute(
                text(
                    "INSERT INTO public.users (full_name, email, password_hash, role, status) VALUES (:name, :email, :hash, 'student', 'active')"
                ),
                inserts,
            )
        if updates:
            session.execute(
                text(
                    "UPDATE public.users SET status = 'active', password_hash = :hash WHERE id = :id AND status IN ('pending', 'rejected')"
                ),
                updates,
            )
    return results


def seed_system_admin(full_name: str, email: str, password: str) -> User:
    """Explicitly create an active system administrator only if no administrator exists.

    Concurrent seed calls serialize on a transaction-scoped PostgreSQL advisory lock.
    An existing system administrator is returned unchanged, regardless of status.
    This function is never invoked automatically or during module import.
    """
    name = _required_text(full_name, "Full name")
    address = _required_text(email, "Email")
    password_hash = _hash_password(password)
    with _transaction() as session:
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _ADMIN_SEED_LOCK},
        )
        user = session.scalar(
            select(User)
            .where(User.role == "system_admin")
            .order_by(User.id)
            .limit(1)
        )
        if user is None:
            user = _insert_user(
                session, name, address, password_hash, "system_admin", "active"
            )
    return user
