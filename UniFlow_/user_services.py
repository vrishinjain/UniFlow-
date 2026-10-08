import reflex as rx

import logging
import os
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
    "activate_user",
    "reject_user",
    "seed_system_admin",
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
