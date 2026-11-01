import secrets
import sys
from pathlib import Path


repository_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository_root))

from sqlalchemy import text
from sqlalchemy.orm import Session

from UniFlow_.user_services import _get_engine, _hash_password


TEST_USERS = (
    ("Avery Admin", "admin@uniflow.test", "system_admin"),
    ("Morgan Program", "progadmin@uniflow.test", "program_admin"),
    ("Taylor Faculty", "faculty@uniflow.test", "faculty"),
    ("Jordan Student", "student@uniflow.test", "student"),
    ("Riley Sponsor", "sponsor@uniflow.test", "sponsor"),
)

PROJECTS = (
    ("Sample Project 1", "Sample project for testing", "pending"),
    ("Sample Project 2", "Sample project for testing", "pending"),
)


def seed_sprint2() -> None:
    user_results: list[tuple[str, str, str, str]] = []
    project_results: list[tuple[str, str]] = []

    with Session(_get_engine()) as session:
        with session.begin():
            session.execute(
                text(
                    "LOCK TABLE public.users, public.projects IN SHARE ROW EXCLUSIVE MODE"
                )
            )

            for full_name, email, role in TEST_USERS:
                existing_user_id = session.execute(
                    text("SELECT id FROM public.users WHERE email = :email"),
                    {"email": email},
                ).scalar_one_or_none()
                if existing_user_id is not None:
                    user_results.append(("skipped", email, role, ""))
                    continue

                password = secrets.token_urlsafe(24)
                password_hash = _hash_password(password)
                session.execute(
                    text(
                        "INSERT INTO public.users "
                        "(full_name, email, password_hash, role, status, must_change_password) "
                        "VALUES (:full_name, :email, :password_hash, :role, :status, :must_change_password)"
                    ),
                    {
                        "full_name": full_name,
                        "email": email,
                        "password_hash": password_hash,
                        "role": role,
                        "status": "active",
                        "must_change_password": False,
                    },
                )
                user_results.append(("created", email, role, password))

            sponsor_id = session.execute(
                text(
                    "SELECT id FROM public.users "
                    "WHERE email = :email AND role = :role"
                ),
                {"email": "sponsor@uniflow.test", "role": "sponsor"},
            ).scalar_one()

            for title, description, status in PROJECTS:
                existing_project_id = session.execute(
                    text(
                        "SELECT id FROM public.projects "
                        "WHERE sponsor_id = :sponsor_id AND title = :title"
                    ),
                    {"sponsor_id": sponsor_id, "title": title},
                ).scalar_one_or_none()
                if existing_project_id is not None:
                    project_results.append(("skipped", title))
                    continue

                session.execute(
                    text(
                        "INSERT INTO public.projects "
                        "(sponsor_id, title, description, status) "
                        "VALUES (:sponsor_id, :title, :description, :status)"
                    ),
                    {
                        "sponsor_id": sponsor_id,
                        "title": title,
                        "description": description,
                        "status": status,
                    },
                )
                project_results.append(("created", title))

    for action, email, role, password in user_results:
        if action == "created":
            print(
                f"Created user {email} ({role}); generated password: {password}"
            )
        else:
            print(f"Skipped user {email} ({role}); already exists")

    for action, title in project_results:
        print(f"{action.capitalize()} project {title}")


if __name__ == "__main__":
    seed_sprint2()
