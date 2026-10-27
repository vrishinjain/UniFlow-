from datetime import datetime
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    LargeBinary,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from UniFlow_.user_model import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'pending', 'accepted', 'rejected')",
            name="projects_status_check",
        ),
        {"schema": "public"},
    )
    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    sponsor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ProjectFile(Base):
    __tablename__ = "project_files"
    __table_args__ = {"schema": "public"}
    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.projects.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
