import asyncio
import logging
from typing import Any

import reflex as rx

from UniFlow_.project_services import (
    SponsorProject,
    list_sponsor_projects,
    submit_project as save_project,
)
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.utils.files import ValidatedFile, read_and_validate


class SponsorState(rx.State):
    full_name: str = ""
    _authorized: bool = False
    projects: list[SponsorProject] = []
    projects_loading: bool = False
    projects_loaded: bool = False
    projects_error: str = ""
    _projects_revision: int = 0

    title: str = ""
    description: str = ""
    title_error: str = ""
    description_error: str = ""
    upload_error: str = ""
    submission_error: str = ""
    loading: bool = False
    success_message: str = ""
    _pending_files: list[ValidatedFile] = []

    @rx.var
    def projects_view(self) -> str:
        if self.projects_loading:
            return "loading"
        if self.projects_error:
            return "error"
        if not self.projects_loaded:
            return "loading"
        if not self.projects:
            return "empty"
        return "table"

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
        self._projects_revision += 1
        self.projects = []
        self.projects_loading = False
        self.projects_loaded = False
        self.projects_error = ""
        self.title = ""
        self.description = ""
        self.title_error = ""
        self.description_error = ""
        self.upload_error = ""
        self.submission_error = ""
        self.success_message = ""
        self._pending_files = []

    @rx.event(background=True)
    async def load_sponsor(self):
        async with self:
            self._authorized = False
            self.full_name = ""
        account, redirect_to = await check_dashboard_access(
            self, "sponsor", background=True
        )
        async with self:
            if account is not None:
                self.full_name = str(account.full_name).strip()
                self._authorized = True
            else:
                self._clear_access()
        if account is None:
            yield rx.redirect(redirect_to)

    @rx.event
    def update_title(self, value: str):
        if not self.loading:
            self.title = value
            self.title_error = ""

    @rx.event
    def update_description(self, value: str):
        if not self.loading:
            self.description = value
            self.description_error = ""

    @rx.event
    def clear_upload_error(self):
        if not self.loading:
            self.upload_error = ""

    @rx.event
    def report_upload_rejections(self, rejections: list[dict[str, Any]]):
        if self.loading:
            return
        messages: list[str] = []
        error_messages = {
            "file-invalid-type": "Only PDF, DOCX, or PPTX files are allowed.",
            "file-too-large": "Each file must be 10 MB or smaller.",
            "too-many-files": "You can attach a maximum of 3 files.",
            "file-too-small": "Files must not be empty.",
        }
        for rejection in rejections:
            for error in rejection.get("errors", []):
                message = error_messages.get(
                    error.get("code", ""),
                    "A file could not be selected. Please select your documents again.",
                )
                if message not in messages:
                    messages.append(message)
        self.upload_error = " ".join(messages)

    async def _prepare_submission(self, files: list[rx.UploadFile]) -> bool:
        if self.loading:
            return False
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.title_error = "Title is required." if not self.title else ""
        self.description_error = (
            "Description is required." if not self.description else ""
        )
        if "\x00" in self.title:
            self.title_error = "Title must not contain null characters."
        if "\x00" in self.description:
            self.description_error = (
                "Description must not contain null characters."
            )
        self.upload_error = ""
        self.submission_error = ""
        self.success_message = ""
        if self.title_error or self.description_error:
            return False
        self.loading = True
        try:
            self._pending_files = await read_and_validate(files)
        except ValueError as e:
            self.upload_error = str(e)
            self.loading = False
            return False
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.upload_error = "The attachments could not be read. Please select them again and retry."
            self.loading = False
            return False
        return True

    @rx.event
    async def submit_project(self, files: list[rx.UploadFile]):
        if await self._prepare_submission(files):
            yield SponsorState.save_submission

    @rx.event
    async def submit_without_files(self):
        if await self._prepare_submission([]):
            yield SponsorState.save_submission

    @rx.event(background=True)
    async def save_submission(self):
        try:
            account, redirect_to = await check_dashboard_access(
                self, "sponsor", background=True
            )
            if account is None:
                async with self:
                    self._clear_access()
                yield rx.redirect(redirect_to)
                return
            async with self:
                login = await self.get_state(LoginState)
                if (
                    not self.loading
                    or login._session_user_id != account.id
                    or not login.signed_in
                ):
                    return
                title = self.title
                description = self.description
                attachments = self._pending_files
                self._pending_files = []
            await asyncio.to_thread(
                save_project, int(account.id), title, description, attachments
            )
            async with self:
                login = await self.get_state(LoginState)
                same_session = (
                    login.signed_in
                    and login._session_user_id == account.id
                    and login.role == "sponsor"
                )
                if same_session:
                    self.title = ""
                    self.description = ""
                    self.success_message = (
                        "Your project was submitted successfully."
                    )
            yield rx.clear_selected_files("project_files")
            if same_session:
                yield rx.redirect("/sponsor")
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            async with self:
                self._clear_access()
            yield rx.redirect("/")
        except ValueError as e:
            async with self:
                self.submission_error = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.submission_error = (
                    "Your project could not be saved. Please try again."
                )
        finally:
            async with self:
                self.loading = False
                self._pending_files = []

    @rx.event
    async def load_my_projects(self):
        self._projects_revision += 1
        revision = self._projects_revision
        self.projects = []
        self.projects_loading = True
        self.projects_loaded = False
        self.projects_error = ""
        yield

        account, redirect_to = await check_dashboard_access(self, "sponsor")
        if revision != self._projects_revision:
            return
        if account is None:
            self._clear_access()
            yield rx.redirect(redirect_to or "/")
            return

        sponsor_id = int(account.id)
        projects: list[SponsorProject] = []
        error = ""
        try:
            projects = await asyncio.to_thread(
                list_sponsor_projects, sponsor_id
            )
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Projects could not be loaded. Please try again."

        account, redirect_to = await check_dashboard_access(self, "sponsor")
        if revision != self._projects_revision:
            return
        login = await self.get_state(LoginState)
        if (
            account is None
            or int(account.id) != sponsor_id
            or not login.signed_in
            or login._session_user_id != sponsor_id
            or login.role != "sponsor"
            or login.must_change_password
        ):
            self._clear_access()
            yield rx.redirect(redirect_to or "/")
            return

        self.projects_loading = False
        if error:
            self.projects_error = error
            return

        self.projects = projects
        self.projects_loaded = True
        self.full_name = str(account.full_name).strip()
        self._authorized = True

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
