import reflex as rx

import asyncio
import logging
import re
from typing import TypedDict

from UniFlow_.project_services import get_shared_project_for_student
from UniFlow_.states.role_guard import check_dashboard_access


class StudentProjectAttachment(TypedDict):
    filename: str
    uploaded_at: str


class StudentProjectDetail(TypedDict):
    id: int
    title: str
    description: str


class StudentProjectDetailState(rx.State):
    # Reflex supplies project_id on the base State for the dynamic route.
    project: StudentProjectDetail = {"id": 0, "title": "", "description": ""}
    files: list[StudentProjectAttachment] = []
    full_name: str = ""
    _authorized: bool = False
    _loaded_project_id: str = ""

    @rx.var
    def authorized(self) -> bool:
        return (
            self._authorized
            and self._loaded_project_id != ""
            and self.project_id == self._loaded_project_id
        )

    def _clear_access(self):
        self._authorized = False
        self._loaded_project_id = ""
        self.project = {"id": 0, "title": "", "description": ""}
        self.files = []
        self.full_name = ""

    @rx.event
    async def load_student_project_detail(self):
        self._clear_access()
        yield
        account, redirect_to = await check_dashboard_access(self, "student")
        if account is None:
            yield rx.redirect(redirect_to)
            return

        route_id = self.project_id
        if (
            not isinstance(route_id, str)
            or len(route_id) > 19
            or not re.fullmatch(r"[0-9]+", route_id)
        ):
            yield rx.redirect("/student")
            return
        parsed_id = int(route_id)
        if not 0 < parsed_id <= 9223372036854775807:
            yield rx.redirect("/student")
            return

        try:
            project = await asyncio.to_thread(
                get_shared_project_for_student, int(account.id), parsed_id
            )
        except Exception as e:
            logging.exception(f"Error: {e}")
            yield rx.redirect("/student")
            return

        if project is None:
            yield rx.redirect("/student")
            return

        self.project = {
            "id": int(project["id"]),
            "title": str(project["title"]),
            "description": str(project["description"]),
        }
        self.files = [
            {
                "filename": str(file["filename"]),
                "uploaded_at": str(file["uploaded_at"]),
            }
            for file in project["files"]
        ]
        self.full_name = str(account.full_name).strip()
        self._loaded_project_id = route_id
        self._authorized = True
