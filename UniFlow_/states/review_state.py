"""T-65: State for the review panel on the faculty project details page."""

import logging

import reflex as rx

from UniFlow_.review_services import (
    STATUS_LABELS,
    list_review_history,
    review_project,
)
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.states.role_guard import check_dashboard_access


_SUCCESS_MESSAGES = {
    "accepted": "Project accepted.",
    "revision_requested": "Changes requested. The sponsor will see your notes.",
    "rejected": "Project rejected.",
}


class ReviewState(rx.State):
    notes: str = ""
    history: list[dict] = []
    review_error: str = ""
    review_message: str = ""
    saving: bool = False

    def _clear(self):
        self.notes = ""
        self.history = []
        self.review_error = ""
        self.review_message = ""
        self.saving = False

    def _project_id(self) -> int:
        """Project id from the URL; raises ValueError if it isn't a number."""
        return int(self.router.page.params.get("id", ""))

    @rx.event
    def set_notes(self, value: str):
        self.notes = value

    @rx.event
    async def load_history(self):
        """Runs on page load, after FacultyState.load_faculty."""
        self._clear()

        account, _ = await check_dashboard_access(self, "faculty")
        if account is None:
            # FacultyState.load_faculty already redirects.
            return

        try:
            self.history = list_review_history(self._project_id())
        except (ValueError, TypeError):
            # Bad project id; FacultyState already shows the error.
            return
        except Exception:
            logging.exception("Failed to load review history")
            self.review_error = "Unable to load review history."

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
                int(account.id), project_id, action, self.notes
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
        self.review_message = _SUCCESS_MESSAGES.get(
            new_status, STATUS_LABELS.get(new_status, "Saved.")
        )

        try:
            self.history = list_review_history(project_id)
        except Exception:
            logging.exception("Failed to reload review history")

    @rx.event
    async def accept(self):
        return await self._review("accept")

    @rx.event
    async def request_revision(self):
        return await self._review("request_revision")

    @rx.event
    async def reject(self):
        return await self._review("reject")
