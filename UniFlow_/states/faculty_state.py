import reflex as rx

import asyncio
import logging

from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.project_services import (
    get_faculty_projects,
    get_faculty_project_details,
    get_faculty_project_file,
    AttachmentMetadata,
)


class FacultyState(rx.State):
    full_name: str = ""
    _authorized: bool = False

    projects: list[dict[str, str]] = []
    selected_project: dict[str, str] = {}
    files: list[AttachmentMetadata] = []
    project_error: str = ""
    _load_version: int = 0

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
        self._load_version += 1

    @rx.event(background=True)
    async def load_faculty(self):
        async with self:
            self._clear_access()
            version = self._load_version
            route_id = self.router.page.params.get("id")
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        if account is None:
            yield rx.redirect(redirect_to)
            return
        async with self:
            if version != self._load_version:
                return
            self.full_name = str(account.full_name).strip()
            self._authorized = True

        if route_id is None:
            try:
                projects = await asyncio.to_thread(get_faculty_projects)
            except Exception as e:
                logging.exception(f"Error: {e}")
                async with self:
                    if version == self._load_version:
                        self.project_error = (
                            "Projects could not be loaded. Please try again."
                        )
                return
            async with self:
                if version == self._load_version:
                    self.projects = projects
            return

        try:
            project_id = int(route_id)
            if project_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            async with self:
                if version == self._load_version:
                    self.project_error = "Invalid project."
            return
        try:
            details = await asyncio.to_thread(
                get_faculty_project_details, project_id
            )
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                if version == self._load_version:
                    self.project_error = (
                        "Project details could not be loaded. Please try again."
                    )
            return
        async with self:
            if (
                version != self._load_version
                or route_id != self.router.page.params.get("id")
            ):
                return
            if details is None or details["id"] != str(project_id):
                self.project_error = "Project not found."
            else:
                self.selected_project = {
                    key: details[key]
                    for key in (
                        "id",
                        "title",
                        "description",
                        "sponsor_name",
                        "created_at",
                        "status",
                    )
                }
                self.files = details["files"]

    @rx.event(background=True)
    async def download_file(self, file_id: str):
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        if account is None:
            async with self:
                self._clear_access()
            yield rx.redirect(redirect_to)
            return

        async with self:
            self.project_error = ""
            version = self._load_version
            route_id = self.router.page.params.get("id", "")
            selected_id = self.selected_project.get("id", "")
        try:
            attachment_id = int(file_id)
            project_id = int(route_id)
            if attachment_id <= 0 or project_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            async with self:
                self.project_error = "Invalid project or attachment."
            return
        if str(project_id) != selected_id:
            async with self:
                self.project_error = "Project details do not match."
            return

        try:
            attachment = await asyncio.to_thread(
                get_faculty_project_file, attachment_id, project_id
            )
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                if version == self._load_version:
                    self.project_error = (
                        "Attachment could not be downloaded. Please try again."
                    )
            return

        current_account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        if current_account is None:
            async with self:
                self._clear_access()
            yield rx.redirect(redirect_to)
            return
        async with self:
            if (
                current_account.id != account.id
                or version != self._load_version
                or route_id != self.router.page.params.get("id", "")
                or selected_id != self.selected_project.get("id", "")
            ):
                return
            if attachment is None:
                self.project_error = "Attachment not found."
                return
        yield rx.download(
            data=attachment["data"],
            filename=attachment["filename"],
        )

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
