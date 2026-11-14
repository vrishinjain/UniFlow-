from datetime import date, datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from UniFlow_.user_model import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','revision_requested', 'accepted', 'rejected')",
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


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    faculty_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    preferences_open: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class Milestone(Base):
    __tablename__ = "milestone"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    project: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )


class StudentPreference(Base):
    __tablename__ = "student_preference"
    __table_args__ = (
        UniqueConstraint(
            "student", "project", name="student_preference_student_project_key"
        ),
        UniqueConstraint(
            "student", "rank", name="student_preference_student_rank_key"
        ),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    student: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    project: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.projects.id"), nullable=False
    )
    course: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.courses.id"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ProjectAssignment(Base):
    __tablename__ = "project_assignment"
    __table_args__ = (
        UniqueConstraint(
            "student", "course", name="project_assignment_student_course_key"
        ),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    student: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    project: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.projects.id"), nullable=False
    )
    course: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.courses.id"), nullable=False
    )
    assigned_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Ticket(Base):
    __tablename__ = "ticket"
    __table_args__ = (
        CheckConstraint(
            "status IN ('To Do','In Progress','Review','Done')",
            name="ticket_status_check",
        ),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    project: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'To Do'")
    )
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=True
    )
    milestone: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.milestone.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
