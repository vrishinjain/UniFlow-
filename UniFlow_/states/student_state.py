import reflex as rx

import asyncio
import logging

from UniFlow_.project_services import (
    SharedStudentProject,
    StudentProjectFile,
    list_shared_projects_for_student,
    get_shared_project_for_student,
    get_shared_project_file_for_student,
)
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access


class StudentState(rx.State):
    full_name: str = ""
    _authorized: bool = False

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""

    @rx.event
    async def load_student(self):
        self._clear_access()
        yield
        account, redirect_to = await check_dashboard_access(self, "student")
        if account is None:
            yield rx.redirect(redirect_to)
            return
        self.full_name = str(account.full_name).strip()
        self._authorized = True

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")


class StudentProjectsState(rx.State):
    projects: list[SharedStudentProject] = []
    authorized: bool = False
    loading: bool = True
    error: str = ""
    _load_request: int = 0

    def _clear_access(self):
        self.projects = []
        self.authorized = False
        self.loading = False
        self.error = ""
        self._load_request += 1

    async def _session_matches(self, student_id: int) -> bool:
        login = await self.get_state(LoginState)
        return (
            login.signed_in
            and login._session_user_id == student_id
            and login.role == "student"
            and not login.must_change_password
        )

    @rx.event(background=True)
    async def load_student_projects(self):
        async with self:
            self._clear_access()
            self.loading = True
            request = self._load_request
            path = self.router.page.path
        account, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        if account is None:
            async with self:
                if (
                    request != self._load_request
                    or path != self.router.page.path
                ):
                    return
                self._clear_access()
            yield rx.redirect(redirect_to or "/")
            return
        student_id = int(account.id)
        projects: list[SharedStudentProject] = []
        error = ""
        denied = False
        try:
            projects = await asyncio.to_thread(
                list_shared_projects_for_student, student_id
            )
        except (PermissionError, ValueError) as e:
            logging.exception(f"Error: {e}")
            denied = True
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Your projects could not be loaded. Please try again."
        current, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        async with self:
            if request != self._load_request or path != self.router.page.path:
                return
            allowed = (
                not denied
                and current is not None
                and current.id == student_id
                and await self._session_matches(student_id)
            )
            if allowed:
                self.projects = projects
                self.error = error
                self.loading = False
                self.authorized = True
            else:
                self._clear_access()
        if not allowed:
            yield rx.redirect(redirect_to or "/")


class StudentProjectDetailState(rx.State):
    title: str = ""
    description: str = ""
    files: list[StudentProjectFile] = []
    selected_project_id: str = ""
    authorized: bool = False
    ready: bool = False
    loading: bool = True
    error: str = ""
    downloading_file_id: str = ""
    _load_request: int = 0

    def _clear_access(self):
        self.title = ""
        self.description = ""
        self.files = []
        self.selected_project_id = ""
        self.authorized = False
        self.ready = False
        self.loading = False
        self.error = ""
        self.downloading_file_id = ""
        self._load_request += 1

    async def _session_matches(self, student_id: int) -> bool:
        login = await self.get_state(LoginState)
        return (
            login.signed_in
            and login._session_user_id == student_id
            and login.role == "student"
            and not login.must_change_password
        )

    @rx.event(background=True)
    async def load_student_project_detail(self):
        async with self:
            self._clear_access()
            self.loading = True
            request = self._load_request
            route_id = str(self.router.page.params.get("project_id", ""))
            path = self.router.page.path
        account, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        if account is None:
            async with self:
                if (
                    request != self._load_request
                    or route_id
                    != str(self.router.page.params.get("project_id", ""))
                    or path != self.router.page.path
                ):
                    return
                self._clear_access()
            yield rx.redirect(redirect_to or "/")
            return
        student_id = int(account.id)
        detail = None
        error = ""
        try:
            detail = await asyncio.to_thread(
                get_shared_project_for_student, student_id, int(route_id)
            )
        except (ValueError, PermissionError) as e:
            logging.exception(f"Error: {e}")
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "This project could not be loaded. Please try again."
        current, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        async with self:
            if (
                request != self._load_request
                or route_id
                != str(self.router.page.params.get("project_id", ""))
                or path != self.router.page.path
            ):
                return
            allowed = (
                current is not None
                and current.id == student_id
                and await self._session_matches(student_id)
            )
            if not allowed:
                self._clear_access()
            elif error:
                self.loading = False
                self.authorized = True
                self.error = error
            elif detail is None:
                self._clear_access()
            else:
                self.title = detail["title"]
                self.description = detail["description"]
                self.files = detail["files"]
                self.selected_project_id = route_id
                self.authorized = True
                self.ready = True
                self.loading = False
        if not allowed:
            yield rx.redirect(redirect_to or "/")
        elif detail is None and not error:
            yield rx.redirect("/student")

    @rx.event(background=True)
    async def download_file(self, file_id: str):
        async with self:
            route_id = str(self.router.page.params.get("project_id", ""))
            path = self.router.page.path
            request = self._load_request
            if (
                not self.ready
                or not self.authorized
                or self.selected_project_id != route_id
                or self.downloading_file_id
            ):
                return
            self.downloading_file_id = file_id
            self.error = ""
        account, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        if account is None:
            async with self:
                if request != self._load_request or route_id != str(
                    self.router.page.params.get("project_id", "")
                ):
                    return
                self._clear_access()
            yield rx.redirect(redirect_to or "/")
            return
        student_id = int(account.id)
        attachment = None
        error = ""
        try:
            attachment = await asyncio.to_thread(
                get_shared_project_file_for_student,
                student_id,
                int(route_id),
                int(file_id),
            )
        except (ValueError, PermissionError) as e:
            logging.exception(f"Error: {e}")
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "The attachment could not be downloaded. Please try again."
        current, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        async with self:
            if (
                request != self._load_request
                or route_id
                != str(self.router.page.params.get("project_id", ""))
                or path != self.router.page.path
            ):
                return
            allowed = current is not None and current.id == student_id
            self.downloading_file_id = ""
            if not allowed or (attachment is None and not error):
                self._clear_access()
            else:
                self.error = error
        if not allowed:
            yield rx.redirect(redirect_to or "/")
        elif attachment is None and not error:
            yield rx.redirect("/student")
        elif attachment is not None:
            yield rx.download(
                data=attachment["data"], filename=attachment["filename"]
            )
