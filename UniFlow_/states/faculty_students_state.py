import reflex as rx

import asyncio
import logging

from UniFlow_.assignment_services import (
    FacultyCourseStudents,
    list_faculty_students,
)

from UniFlow_.course_assignment_services import (
    ManualProjectOption,
    list_manual_assignment_projects,
    update_manual_assignment,
)

from UniFlow_.courses_services import parse_course_id
from UniFlow_.states.role_guard import check_dashboard_access


class FacultyStudentsState(rx.State):
    """Faculty My students page (#96 and #101)."""

    courses: list[FacultyCourseStudents] = []
    loading: bool = True
    error: str = ""

    # T12 (#101): Manual assignment edits.
    available_projects: dict[str, list[ManualProjectOption]] = {}
    assignment_busy: bool = False
    assignment_message: str = ""
    assignment_error: str = ""

    @rx.event(background=True)
    async def load_students(self):
        async with self:
            self.courses = []
            self.available_projects = {}
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
        projects: dict[str, list[ManualProjectOption]] = {}
        error = ""

        try:
            courses = await asyncio.to_thread(
                list_faculty_students, int(account.id)
            )

            for course in courses:
                course_id = course["course_id"]

                projects[course_id] = await asyncio.to_thread(
                    list_manual_assignment_projects,
                    int(account.id),
                    parse_course_id(course_id),
                )

        except PermissionError:
            logging.exception("Faculty access denied")
            error = "You don't have access to this page."

        except Exception:
            logging.exception("Could not load faculty students")
            error = "Your students could not be loaded. Please try again."

        current_account, _ = await check_dashboard_access(
            self, "faculty", background=True
        )

        async with self:
            if (
                current_account is None
                or current_account.id != account.id
            ):
                self.courses = []
                self.available_projects = {}
                self.loading = False
                return

            self.courses = courses if not error else []
            self.available_projects = projects if not error else {}
            self.error = error
            self.loading = False

    @rx.event
    async def change_assignment(
        self,
        course_id: str,
        student_id: int,
        project_id: str,
    ):
        """Assign or move a student to a selected project."""

        if self.assignment_busy or self.loading:
            return

        self.assignment_message = ""
        self.assignment_error = ""
        self.assignment_busy = True

        try:
            account, _ = await check_dashboard_access(
                self, "faculty", background=False
            )

            if account is None:
                raise PermissionError("Faculty access denied.")

            if not project_id:
                raise ValueError("Please select a project.")

            message = await asyncio.to_thread(
                update_manual_assignment,
                int(account.id),
                parse_course_id(course_id),
                student_id,
                parse_course_id(project_id),
            )

            self.assignment_message = message
            yield FacultyStudentsState.load_students

        except (PermissionError, ValueError) as exc:
            self.assignment_error = str(exc)

        except Exception:
            logging.exception("Could not update student assignment")
            self.assignment_error = (
                "Assignment could not be updated. Please try again."
            )

        finally:
            self.assignment_busy = False

    @rx.event
    async def unassign_student(
        self,
        course_id: str,
        student_id: int,
    ):
        """Remove a student's assignment from the selected course."""

        if self.assignment_busy or self.loading:
            return

        self.assignment_message = ""
        self.assignment_error = ""
        self.assignment_busy = True

        try:
            account, _ = await check_dashboard_access(
                self, "faculty", background=False
            )

            if account is None:
                raise PermissionError("Faculty access denied.")

            message = await asyncio.to_thread(
                update_manual_assignment,
                int(account.id),
                parse_course_id(course_id),
                student_id,
                None,
            )

            self.assignment_message = message
            yield FacultyStudentsState.load_students

        except (PermissionError, ValueError) as exc:
            self.assignment_error = str(exc)

        except Exception:
            logging.exception("Could not unassign student")
            self.assignment_error = (
                "Student could not be unassigned. Please try again."
            )

        finally:
            self.assignment_busy = False