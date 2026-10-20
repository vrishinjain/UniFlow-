import reflex as rx

from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.project_services import get_faculty_projects


class FacultyState(rx.State):
    full_name: str = ""
    _authorized: bool = False
    projects: list[dict] = []

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
        self.projects = []

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

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
