
import base64

import reflex as rx

from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.project_services import (
    get_faculty_projects,
    get_faculty_project_details,
    get_faculty_project_file,
)


class FacultyState(rx.State):
    full_name: str = ""
    _authorized: bool = False

    projects: list[dict] = []
    selected_project: dict = {}
    files: list[dict] = []
    project_error: str = ""

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
        self.projects = []
        self.selected_project = {}
        self.files = []
        self.project_error = ""

    @rx.event
    async def load_faculty(self):
        self._clear_access()
        yield

        account, redirect_to = await check_dashboard_access(
            self, "faculty"
        )

        if account is None:
            yield rx.redirect(redirect_to)
            return

        self.full_name = str(account.full_name).strip()
        self._authorized = True
        self.projects = get_faculty_projects()

        project_id = self.router.page.params.get("id")

        if project_id is not None:
            try:
                details = get_faculty_project_details(
                    int(project_id)
                )
            except (TypeError, ValueError):
                details = None

            if details is None:
                self.project_error = "Project not found."
            else:
                self.selected_project = details
                self.files = details.get("files", [])

    @rx.event
    async def download_file(self, file_id: str):
        account, redirect_to = await check_dashboard_access(
            self, "faculty"
        )

        if account is None:
            return rx.redirect(redirect_to)

        self.project_error = ""

        try:
            attachment_id = int(file_id)
            project_id = int(
                self.router.page.params.get("id", "")
            )

            if attachment_id <= 0 or project_id <= 0:
                raise ValueError

        except (TypeError, ValueError):
            self.project_error = "Invalid project or attachment."
            return

        if str(project_id) != self.selected_project.get("id"):
            self.project_error = "Project details do not match."
            return

        attachment = get_faculty_project_file(
            attachment_id,
            project_id,
        )

        if attachment is None:
            self.project_error = "Attachment not found."
            return

        encoded = base64.b64encode(
            attachment["data"]
        ).decode("ascii")

        data_url = (
            "data:"
            + attachment["content_type"]
            + ";base64,"
            + encoded
        )

        return rx.download(
            data=data_url,
            filename=attachment["filename"],
        )

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
