import reflex as rx

import asyncio
import logging
from typing import Any

from UniFlow_.project_services import submit_project as save_project
from UniFlow_.utils.files import ValidatedFile, read_and_validate
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access


class SponsorState(rx.State):
    full_name: str = ""
    _authorized: bool = False
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
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
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
    def report_upload_rejections(self, rejections: list[dict[str, Any]]):
        if self.loading:
            return
        messages: list[str] = []
        guidance = {
            "file-invalid-type": "Unsupported file type. Select only PDF, DOCX, or PPTX documents.",
            "file-too-large": "A file exceeds 10 MB. Reduce its size to 10 MB or less and select it again.",
            "too-many-files": "Too many files. Select no more than 3 attachments at once.",
            "file-too-small": "A file is too small. Select a non-empty document.",
        }
        for rejection in rejections:
            for error in rejection.get("errors", []):
                message = guidance.get(
                    error.get("code", ""),
                    "An attachment could not be selected. Retry with up to 3 PDF, DOCX, or PPTX documents, each 10 MB or less.",
                )
                if message not in messages:
                    messages.append(message)
        self.upload_error = " ".join(messages) or (
            "Attachments could not be selected. Select up to 3 PDF, DOCX, or PPTX documents, each 10 MB or less."
        )

    @rx.event
    def clear_upload_error(self):
        if not self.loading:
            self.upload_error = ""

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
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
