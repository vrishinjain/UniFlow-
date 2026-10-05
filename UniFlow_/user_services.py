import reflex as rx

import logging

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from UniFlow_.user_model import User


__all__ = [
    "create_user",
    "get_user_by_email",
    "verify_password",
    "list_pending_users",
    "activate_user",
    "reject_user",
    "seed_system_admin",
    "update_user_role",
    "update_user_status",
]

_ALLOWED_ROLES = frozenset(
    {"system_admin", "program_admin", "faculty", "student", "sponsor"}
)
_ALLOWED_STATUSES = frozenset({"pending", "active", "rejected"})
_ADMIN_SEED_LOCK = 6143972381094261


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
        session.execute(
            select(User.id).where(User.email == email).limit(1)
        ).first()
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


def _raise_database_error(error: SQLAlchemyError) -> None:
    logging.exception(f"Error: {error}")
    if isinstance(error, IntegrityError):
        original = error.orig
        sqlstate = getattr(original, "sqlstate", None)
        diagnostic = getattr(original, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)
        if sqlstate == "23505" and constraint == "users_email_key":
            raise ValueError(
                "A user with that email already exists."
            ) from error
    raise error


def _validate_user_id(user_id: int) -> None:
    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
    ):
        raise ValueError("User ID must be a positive integer.")


def create_user(full_name: str, email: str, password: str, role: str) -> User:
    """Create a pending user and return a fully loaded user after commit."""
    if not isinstance(role, str) or role not in _ALLOWED_ROLES:
        raise ValueError(
            "Invalid role. Expected system_admin, program_admin, faculty, student, or sponsor."
        )
    name = _required_text(full_name, "Full name")
    address = _required_text(email, "Email")
    password_hash = _hash_password(password)
    try:
        with rx.session() as session:
            if role == "system_admin":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": _ADMIN_SEED_LOCK},
                )
                existing_admin = (
                    session.execute(
                        select(User)
                        .where(User.role == "system_admin")
                        .order_by(User.id)
                        .limit(1)
                    )
                    .scalars()
                    .first()
                )
                if existing_admin is not None:
                    raise ValueError("A system administrator already exists.")
            user = _insert_user(
                session, name, address, password_hash, role, "pending"
            )
            session.commit()
            session.refresh(user)
        return user
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


def get_user_by_email(email: str) -> User | None:
    """Return the matching user, or None when no matching email exists."""
    address = _required_text(email, "Email")
    try:
        with rx.session() as session:
            user = (
                session.execute(
                    select(User).where(User.email == address).limit(1)
                )
                .scalars()
                .first()
            )
        return user
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


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
    try:
        with rx.session() as session:
            users = list(
                session.execute(
                    select(User)
                    .where(User.status == "pending")
                    .order_by(User.created_at, User.id)
                )
                .scalars()
                .all()
            )
        return users
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


def _set_user_status(session: Session, user_id: int, status: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("No user exists with that ID.")
    user.status = status
    return user


def activate_user(user_id: int) -> User:
    """Set only the identified user's status to active; missing IDs raise ValueError."""
    _validate_user_id(user_id)
    try:
        with rx.session() as session:
            user = _set_user_status(session, user_id, "active")
            session.commit()
            session.refresh(user)
        return user
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


def reject_user(user_id: int) -> User:
    """Set only the identified user's status to rejected; missing IDs raise ValueError."""
    _validate_user_id(user_id)
    try:
        with rx.session() as session:
            user = _set_user_status(session, user_id, "rejected")
            session.commit()
            session.refresh(user)
        return user
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


def seed_system_admin(full_name: str, email: str, password: str) -> User:
    """Create an active system administrator only if none exists."""
    name = _required_text(full_name, "Full name")
    address = _required_text(email, "Email")
    password_hash = _hash_password(password)
    try:
        with rx.session() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _ADMIN_SEED_LOCK},
            )
            user = (
                session.execute(
                    select(User)
                    .where(User.role == "system_admin")
                    .order_by(User.id)
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if user is None:
                user = _insert_user(
                    session,
                    name,
                    address,
                    password_hash,
                    "system_admin",
                    "active",
                )
                session.commit()
                session.refresh(user)
        return user
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


def update_user_role(user_id: int, role: str) -> None:
    """Update a user's role; invalid roles and missing users raise ValueError."""
    _validate_user_id(user_id)
    if not isinstance(role, str) or role not in _ALLOWED_ROLES:
        raise ValueError(
            "Invalid role. Expected system_admin, program_admin, faculty, student, or sponsor."
        )
    try:
        with rx.session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("No user exists with that ID.")
            if role == "system_admin":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": _ADMIN_SEED_LOCK},
                )
                existing_admin = (
                    session.execute(
                        select(User)
                        .where(
                            User.role == "system_admin",
                            User.id != user_id,
                        )
                        .order_by(User.id)
                        .limit(1)
                    )
                    .scalars()
                    .first()
                )
                if existing_admin is not None:
                    raise ValueError("A system administrator already exists.")
            user.role = role
            session.commit()
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)


def update_user_status(user_id: int, status: str) -> None:
    """Update a user's status; invalid statuses and missing users raise ValueError."""
    _validate_user_id(user_id)
    if not isinstance(status, str) or status not in _ALLOWED_STATUSES:
        raise ValueError(
            "Invalid status. Expected pending, active, or rejected."
        )
    try:
        with rx.session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("No user exists with that ID.")
            user.status = status
            session.commit()
    except SQLAlchemyError as e:
        logging.exception("Unexpected error")
        _raise_database_error(e)
