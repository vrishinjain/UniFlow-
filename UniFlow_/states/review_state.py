"""T-65 / T-66: State for the review panel on the faculty project details page."""

import logging

import reflex as rx

from UniFlow_.courses_services import list_faculty_courses
from UniFlow_.review_services import (
    STATUS_LABELS,
    course_option,
    list_project_courses,
    list_review_history,
    review_project,
    set_project_courses,
)
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.states.role_guard import check_dashboard_access


_SUCCESS_MESSAGES = {
    "accepted": "Project accepted and shared with the selected courses.",
    "revision_requested": "Changes requested. The sponsor will see your notes.",
    "rejected": "Project rejected.",
}


class ReviewState(rx.State):
    notes: str = ""
    history: list[dict] = []
    review_error: str = ""
    review_message: str = ""
    saving: bool = False

    # T-66: course sharing
    my_courses: list[dict] = []  # [{"id": "3", "label": "CS682 · ..."}]
    selected_course_ids: list[str] = []
    shared_courses: list[dict] = []
    editing_courses: bool = False

    def _clear(self):
        self.notes = ""
        self.history = []
        self.review_error = ""
        self.review_message = ""
        self.saving = False
        self.my_courses = []
        self.selected_course_ids = []
        self.shared_courses = []
        self.editing_courses = False

    def _selected_ints(self) -> list[int]:
        return [int(value) for value in self.selected_course_ids]

    def _load_courses(self, faculty_id: int, project_id: int):
        self.my_courses = [
            course_option(course) for course in list_faculty_courses(faculty_id)
        ]
        self.shared_courses = list_project_courses(project_id)

    def _project_id(self) -> int:
        """Project id from the URL; raises ValueError if it isn't a number."""
        return int(self.router.page.params.get("id", ""))

    @rx.event
    def set_notes(self, value: str):
        self.notes = value

    @rx.event
    def toggle_course(self, course_id: str, checked: bool):
        if checked and course_id not in self.selected_course_ids:
            self.selected_course_ids = [*self.selected_course_ids, course_id]
        elif not checked:
            self.selected_course_ids = [
                value for value in self.selected_course_ids if value != course_id
            ]

    @rx.event
    def start_editing_courses(self):
        """Pre-tick the courses this faculty member already shared with."""
        mine = {course["id"] for course in self.my_courses}
        self.selected_course_ids = [
            course["id"] for course in self.shared_courses if course["id"] in mine
        ]
        self.review_error = ""
        self.review_message = ""
        self.editing_courses = True

    @rx.event
    def cancel_editing_courses(self):
        self.selected_course_ids = []
        self.editing_courses = False

    @rx.event
    async def load_history(self):
        """Runs on page load, after FacultyState.load_faculty."""
        self._clear()

        account, _ = await check_dashboard_access(self, "faculty")
        if account is None:
            # FacultyState.load_faculty already redirects.
            return

        try:
            project_id = self._project_id()
            self.history = list_review_history(project_id)
            self._load_courses(int(account.id), project_id)
        except (ValueError, TypeError):
            # Bad project id; FacultyState already shows the error.
            return
        except Exception:
            logging.exception("Failed to load review details")
            self.review_error = "Unable to load review history or courses."

    async def _review(self, action: str):
        if self.saving:
            return

        self.review_error = ""
        self.review_message = ""

        # Always check access on the server, never trust the page.
        account, redirect_to = await check_dashboard_access(self, "faculty")
        if account is None:
            return rx.redirect(redirect_to)

        try:
            project_id = self._project_id()
        except (ValueError, TypeError):
            self.review_error = "Invalid project ID."
            return

        self.saving = True
        try:
            new_status = review_project(
                int(account.id),
                project_id,
                action,
                self.notes,
                self._selected_ints() if action == "accept" else None,
            )
        except (PermissionError, ValueError) as e:
            self.review_error = str(e)
            return
        except Exception:
            logging.exception("Failed to save project review")
            self.review_error = "Unable to save the review. Nothing was changed."
            return
        finally:
            self.saving = False

        # Update what the faculty pages show without reloading.
        faculty = await self.get_state(FacultyState)
        faculty.selected_project = {
            **faculty.selected_project,
            "status": new_status,
        }
        faculty.projects = [
            {**project, "status": new_status}
            if str(project.get("id")) == str(project_id)
            else project
            for project in faculty.projects
        ]

        self.notes = ""
        self.selected_course_ids = []
        self.review_message = _SUCCESS_MESSAGES.get(
            new_status, STATUS_LABELS.get(new_status, "Saved.")
        )

        try:
            self.history = list_review_history(project_id)
            self._load_courses(int(account.id), project_id)
        except Exception:
            logging.exception("Failed to reload review details")

    @rx.event
    async def save_courses(self):
        """Change sharing on an already accepted project."""
        if self.saving:
            return

        self.review_error = ""
        self.review_message = ""

        account, redirect_to = await check_dashboard_access(self, "faculty")
        if account is None:
            return rx.redirect(redirect_to)

        try:
            project_id = self._project_id()
        except (ValueError, TypeError):
            self.review_error = "Invalid project ID."
            return

        self.saving = True
        try:
            set_project_courses(
                int(account.id), project_id, self._selected_ints()
            )
        except (PermissionError, ValueError) as e:
            self.review_error = str(e)
            return
        except Exception:
            logging.exception("Failed to update project sharing")
            self.review_error = "Unable to update sharing. Nothing was changed."
            return
        finally:
            self.saving = False

        self.editing_courses = False
        self.selected_course_ids = []
        self.review_message = "Sharing updated."
        try:
            self._load_courses(int(account.id), project_id)
        except Exception:
            logging.exception("Failed to reload shared courses")

    @rx.event
    async def accept(self):
        return await self._review("accept")

    @rx.event
    async def request_revision(self):
        return await self._review("request_revision")

    @rx.event
    async def reject(self):
        return await self._review("reject")
