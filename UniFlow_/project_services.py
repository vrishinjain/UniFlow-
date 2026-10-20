import reflex as rx

from typing import TypedDict

from sqlalchemy import text

from UniFlow_.user_services import _get_engine, _validate_user_id


class SponsorProject(TypedDict):
    id: int
    title: str
    status: str
    submitted_date: str
    submitted_at: str


def list_sponsor_projects(sponsor_id: int) -> list[SponsorProject]:
    """Read only this sponsor's projects, newest first; never change the schema."""
    _validate_user_id(sponsor_id)
    with _get_engine().connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, title, status, created_at FROM public.projects "
                "WHERE sponsor_id = :sponsor_id "
                "ORDER BY created_at DESC, id DESC"
            ),
            {"sponsor_id": sponsor_id},
        ).all()
    return [
        SponsorProject(
            id=int(row.id),
            title=str(row.title),
            status=str(row.status).replace("_", " ").title(),
            submitted_date=row.created_at.strftime("%b %d, %Y"),
            submitted_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
