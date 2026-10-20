
import reflex as rx

from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.project_services import (
    get_faculty_projects,
    get_faculty_project_details,
)


class FacultyState(rx.State):
    full_name: str = ""
    _authorized: bool = False

    projects: list[dict] = []
    selected_project: dict = {}
    project_error: str = ""

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
        self.projects = []
        self.selected_project = {}
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
                self.selected_project = (
                    get_faculty_project_details(int(project_id)) or {}
                )

                if not self.selected_project:
                    self.project_error = "Project not found."

            except (TypeError, ValueError):
                self.project_error = "Invalid project ID."

            except Exception:
                self.project_error = "Unable to load project details."

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
