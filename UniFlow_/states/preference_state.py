import reflex as rx

import asyncio
import logging
from typing import Any

from UniFlow_.courses_services import EnrolledStudent
from UniFlow_.preference_services import (
    CoursePreferenceForm,
    get_course_preference_status,
    get_student_preference_forms,
    save_student_preferences,
    set_course_preferences_open,
)
from UniFlow_.states.role_guard import check_dashboard_access


class CoursePreferencesState(rx.State):
    """Faculty panel on /faculty/course/[id]: open/close + who hasn't submitted (#95)."""

    preferences_open: bool = False
    enrolled: int = 0
    submitted: int = 0
    missing: list[EnrolledStudent] = []
    loaded: bool = False
    busy: bool = False
    error: str = ""
    _course_id: str = ""

    def _reset_panel(self):
        self.preferences_open = False
        self.enrolled = 0
        self.submitted = 0
        self.missing = []
        self.loaded = False
        self.busy = False
        self.error = ""

    @rx.event(background=True)
    async def load_panel(self):
        async with self:
            self._reset_panel()
            self.busy = True
            course_id = str(self.router.page.params.get("id", ""))
            self._course_id = course_id
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        if account is None:
            async with self:
                self._reset_panel()
            return
        status = None
        error = ""
        try:
            status = await asyncio.to_thread(
                get_course_preference_status, int(account.id), course_id
            )
        except (PermissionError, ValueError) as e:
            logging.exception(f"Error: {e}")
            error = "Preference status is unavailable for this course."
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Preference status could not be loaded. Please try again."
        async with self:
            if course_id != self._course_id:
                return
            self.busy = False
            self.error = error
            if status is not None:
                self.preferences_open = status["preferences_open"]
                self.enrolled = status["enrolled"]
                self.submitted = status["submitted"]
                self.missing = status["missing"]
                self.loaded = True

    @rx.event(background=True)
    async def toggle_preferences(self):
        async with self:
            if self.busy or not self.loaded:
                return
            self.busy = True
            self.error = ""
            course_id = self._course_id
            new_value = not self.preferences_open
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        if account is None:
            async with self:
                self._reset_panel()
            yield rx.redirect(redirect_to or "/")
            return
        error = ""
        try:
            await asyncio.to_thread(
                set_course_preferences_open, int(account.id), course_id, new_value
            )
        except (PermissionError, ValueError) as e:
            logging.exception(f"Error: {e}")
            error = "You can't change preferences for this course."
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "The change could not be saved. Please try again."
        async with self:
            if course_id != self._course_id:
                return
            self.busy = False
            self.error = error
        if not error:
            yield CoursePreferencesState.load_panel


class StudentPreferencesState(rx.State):
    """Student page /student/preferences: rank projects per course (#94)."""

    forms: list[CoursePreferenceForm] = []
    authorized: bool = False
    loading: bool = True
    saving_course_id: str = ""
    error: str = ""
    message: str = ""
    form_revision: int = 0

    def _clear(self):
        self.forms = []
        self.authorized = False
        self.loading = False
        self.saving_course_id = ""
        self.error = ""
        self.message = ""

    @rx.event(background=True)
    async def load_preferences(self):
        async with self:
            self._clear()
            self.loading = True
        account, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        if account is None:
            async with self:
                self._clear()
            yield rx.redirect(redirect_to or "/")
            return
        forms: list[CoursePreferenceForm] = []
        error = ""
        try:
            forms = await asyncio.to_thread(
                get_student_preference_forms, int(account.id)
            )
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            async with self:
                self._clear()
            yield rx.redirect("/")
            return
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Your preferences could not be loaded. Please try again."
        async with self:
            self.forms = forms
            self.error = error
            self.loading = False
            self.authorized = True
            self.form_revision += 1

    @rx.event(background=True)
    async def save_preferences(self, form_data: dict[str, Any]):
        course_id = str(form_data.get("course_id", "")).strip()
        async with self:
            if self.saving_course_id:
                return
            self.saving_course_id = course_id
            self.error = ""
            self.message = ""
            slot_count = next(
                (f["slot_count"] for f in self.forms if f["course_id"] == course_id),
                0,
            )
        choices = [
            str(form_data.get(f"choice_{rank}", "")).strip()
            for rank in range(1, slot_count + 1)
        ]
        account, redirect_to = await check_dashboard_access(
            self, "student", background=True
        )
        if account is None:
            async with self:
                self._clear()
            yield rx.redirect(redirect_to or "/")
            return
        error = ""
        try:
            await asyncio.to_thread(
                save_student_preferences, int(account.id), course_id, choices
            )
        except (PermissionError, ValueError) as e:
            error = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Your preferences could not be saved. Please try again."
        forms = None
        if not error:
            try:
                forms = await asyncio.to_thread(
                    get_student_preference_forms, int(account.id)
                )
            except Exception as e:
                logging.exception(f"Error: {e}")
        async with self:
            self.saving_course_id = ""
            self.error = error
            if not error:
                self.message = "Your preferences were saved."
            if forms is not None:
                self.forms = forms
                self.form_revision += 1
