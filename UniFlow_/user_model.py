from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Identity,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
)


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        CheckConstraint(
            "role IN ('system_admin', 'program_admin', 'faculty', 'student', 'sponsor')",
            name="users_role_check",
        ),
        CheckConstraint(
            "status IN ('pending', 'active', 'rejected')",
            name="users_status_check",
        ),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        init=False,
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        init=False,
    )
