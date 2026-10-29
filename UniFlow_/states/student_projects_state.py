import reflex as rx

import asyncio
import logging
from typing import TypedDict

from UniFlow_.project_services import list_shared_projects_for_student
from UniFlow_.states.role_guard import check_dashboard_access


class StudentProject(TypedDict):
    id: int
    title: str
    description: str


class StudentProjectsState(rx.State):
    full_name: str = ""
    projects: list[StudentProject] = []
    loading: bool = True
    error: str = ""
    _authorized: bool = False

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
        self.projects = []
        self.loading = True
        self.error = ""

    @rx.event
    async def load_student_projects(self):
        self._clear_access()
        yield
        account, redirect_to = await check_dashboard_access(self, "student")
        if account is None:
            yield rx.redirect(redirect_to)
            return
        self.full_name = str(account.full_name).strip()
        self._authorized = True
        try:
            self.projects = await asyncio.to_thread(
                list_shared_projects_for_student, int(account.id)
            )
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.error = (
                "Projects are temporarily unavailable. Please try again later."
            )
        finally:
            self.loading = False
