"""T-67: State for the sponsor's project details page (status + resubmit)."""

import logging

import reflex as rx

from UniFlow_.sponsor_review_services import (
    get_sponsor_project,
    resubmit_project,
)
from UniFlow_.states.role_guard import check_dashboard_access


class SponsorProjectState(rx.State):
    project: dict = {}
    edit_title: str = ""
    edit_description: str = ""
    page_error: str = ""
    form_error: str = ""
    form_message: str = ""
    saving: bool = False
    loaded: bool = False

    def _clear(self):
        self.project = {}
        self.edit_title = ""
        self.edit_description = ""
        self.page_error = ""
        self.form_error = ""
        self.form_message = ""
        self.saving = False
        self.loaded = False

    def _project_id(self) -> int:
        """Project id from the URL; raises ValueError if it isn't a number."""
        return int(self.router.page.params.get("id", ""))

    def _show(self, details: dict):
        self.project = dict(details)
        self.edit_title = details["title"]
        self.edit_description = details["description"]

    @rx.event
    def set_edit_title(self, value: str):
        if not self.saving:
            self.edit_title = value

    @rx.event
    def set_edit_description(self, value: str):
        if not self.saving:
            self.edit_description = value

    @rx.event
    async def load_project(self):
        """Runs on page load, after SponsorState.load_sponsor."""
        self._clear()

        account, redirect_to = await check_dashboard_access(self, "sponsor")
        if account is None:
            return rx.redirect(redirect_to)

        try:
            details = get_sponsor_project(int(account.id), self._project_id())
        except (ValueError, TypeError):
            self.page_error = "Project not found."
            self.loaded = True
            return
        except Exception:
            logging.exception("Failed to load sponsor project")
            self.page_error = "This project could not be loaded. Please try again."
            self.loaded = True
            return

        if details is None:
            # Missing or someone else's project: same message either way.
            self.page_error = "Project not found."
        else:
            self._show(details)
        self.loaded = True

    @rx.event
    async def resubmit(self):
        if self.saving:
            return

        self.form_error = ""
        self.form_message = ""

        # Always check access on the server, never trust the page.
        account, redirect_to = await check_dashboard_access(self, "sponsor")
        if account is None:
            return rx.redirect(redirect_to)

        try:
            project_id = self._project_id()
        except (ValueError, TypeError):
            self.form_error = "Project not found."
            return

        self.saving = True
        try:
            resubmit_project(
                int(account.id),
                project_id,
                self.edit_title,
                self.edit_description,
            )
            details = get_sponsor_project(int(account.id), project_id)
        except (PermissionError, ValueError) as e:
            self.form_error = str(e)
            return
        except Exception:
            logging.exception("Failed to resubmit project")
            self.form_error = "Your changes could not be saved. Nothing was changed."
            return
        finally:
            self.saving = False

        if details is not None:
            self._show(details)
        self.form_message = "Resubmitted. Faculty will review your project again."
