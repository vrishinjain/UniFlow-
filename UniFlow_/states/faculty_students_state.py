import reflex as rx

import asyncio
import logging

from UniFlow_.assignment_services import (
    FacultyCourseStudents,
    list_faculty_students,
)
from UniFlow_.states.role_guard import check_dashboard_access


class FacultyStudentsState(rx.State):
    """Faculty "My students" page (#96)."""

    courses: list[FacultyCourseStudents] = []
    loading: bool = True
    error: str = ""

    @rx.event(background=True)
    async def load_students(self):
        async with self:
            self.courses = []
            self.error = ""
            self.loading = True
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        if account is None:
            async with self:
                self.loading = False
            return
        courses: list[FacultyCourseStudents] = []
        error = ""
        try:
            courses = await asyncio.to_thread(
                list_faculty_students, int(account.id)
            )
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            error = "You don't have access to this page."
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Your students could not be loaded. Please try again."
        async with self:
            self.courses = courses
            self.error = error
            self.loading = False
