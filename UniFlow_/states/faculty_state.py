
import logging

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

        try:
            self.projects = get_faculty_projects()

            project_id = self.router.page.params.get("id")

            if project_id is not None:
                details = get_faculty_project_details(
                    int(project_id)
                )

                if details is None:
                    self.project_error = "Project not found."
                else:
                    self.selected_project = {
                        key: value
                        for key, value in details.items()
                        if key != "files"
                    }

                    self.files = details.get("files", [])

        except (ValueError, TypeError):
            self.project_error = "Invalid project ID."

        except Exception:
            logging.exception(
                "Failed to load faculty projects"
            )
            self.project_error = (
                "Unable to load project details."
            )

    @rx.event
    async def download_file(self, file_id: str):
        self.project_error = ""

        account, redirect_to = await check_dashboard_access(
            self, "faculty"
        )

        if account is None:
            return rx.redirect(redirect_to)

        project_id = self.router.page.params.get("id")

        if project_id is None:
            self.project_error = "Project not found."
            return

        try:
            attachment = get_faculty_project_file(
                int(file_id),
                int(project_id),
            )

            if attachment is None:
                self.project_error = "Attachment not found."
                return

            file_bytes = attachment["data"]
            filename = attachment["filename"]

            if not isinstance(file_bytes, bytes):
                file_bytes = bytes(file_bytes)

            if not file_bytes:
                self.project_error = "Attachment is empty."
                return

            return rx.download(
                data=file_bytes,
                filename=filename,
            )

        except (ValueError, TypeError):
            self.project_error = "Invalid attachment."

        except Exception:
            logging.exception(
                "Failed to download faculty attachment"
            )
            self.project_error = (
                "Unable to download attachment."
            )

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
