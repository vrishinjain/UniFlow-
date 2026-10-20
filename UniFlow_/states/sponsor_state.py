import reflex as rx

import asyncio
import logging

from UniFlow_.project_services import SponsorProject, list_sponsor_projects
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access


class SponsorState(rx.State):
    full_name: str = ""
    _authorized: bool = False
    projects: list[SponsorProject] = []
    projects_loading: bool = False
    projects_loaded: bool = False
    projects_error: str = ""
    _projects_revision: int = 0

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

    @rx.event
    async def load_sponsor(self):
        self._clear_access()
        yield
        account, redirect_to = await check_dashboard_access(self, "sponsor")
        if account is None:
            yield rx.redirect(redirect_to)
            return
        self.full_name = str(account.full_name).strip()
        self._authorized = True

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
