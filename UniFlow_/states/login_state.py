import reflex as rx

import asyncio
from typing import Any

from UniFlow_.user_services import get_user_by_email, verify_password

import logging


DASHBOARD_ROUTES = {
    "student": "/student",
    "faculty": "/faculty",
    "program_admin": "/programadmin",
    "sponsor": "/sponsor",
    "system_admin": "/admin",
}


class LoginState(rx.State):
    email: str = ""
    full_name: str = ""
    role: str = ""
    signed_in: bool = False
    must_change_password: bool = False
    loading: bool = False
    message: str = ""
    password_revision: int = 0
    _session_user_id: int = 0

    def _clear_session(self):
        self._session_user_id = 0
        self.signed_in = False
        self.must_change_password = False
        self.full_name = ""
        self.role = ""
        self.email = ""
        self.message = ""
        self.password_revision += 1

    async def _clear_dashboard_access(self):
        from UniFlow_.states.admin_state import AdminState
        from UniFlow_.states.student_state import StudentState
        from UniFlow_.states.faculty_state import FacultyState
        from UniFlow_.states.program_admin_state import ProgramAdminState
        from UniFlow_.states.sponsor_state import SponsorState

        for state_class in (
            AdminState,
            StudentState,
            FacultyState,
            ProgramAdminState,
            SponsorState,
        ):
            dashboard = await self.get_state(state_class)
            dashboard._clear_access()

    @rx.event
    def redirect_signed_in_user(self):
        if self.signed_in:
            if self._session_user_id > 0 and self.must_change_password:
                return rx.redirect("/set-password")
            if self._session_user_id > 0 and self.role in DASHBOARD_ROUTES:
                return rx.redirect(DASHBOARD_ROUTES[self.role])
            self._clear_session()

    @rx.event
    def clear_feedback(self):
        if not self.loading:
            self.message = ""

    @rx.event
    async def sign_in(self, form_data: dict[str, Any]):
        password = form_data.pop("password", "")
        if self.loading or self.signed_in:
            return
        self._session_user_id = 0
        self.signed_in = False
        self.email = str(form_data.get("email", "")).strip()
        self.message = ""
        self.full_name = ""
        self.role = ""
        self.loading = True
        self.password_revision += 1
        yield

        try:
            if not self.email or not isinstance(password, str) or not password:
                self.message = "Invalid email or password"
                return
            user = await asyncio.to_thread(get_user_by_email, self.email)
            if user is None:
                self.message = "Invalid email or password"
                return
            verified = await asyncio.to_thread(
                verify_password, password, user.password_hash
            )
            if not verified:
                self.message = "Invalid email or password"
                return
            match user.status:
                case "pending":
                    self.message = "Your account is awaiting approval"
                case "rejected":
                    self.message = "Your request was not approved"
                case "active":
                    await self._clear_dashboard_access()
                    self.full_name = str(user.full_name).strip()
                    self.role = str(user.role)
                    self.email = str(user.email)
                    self._session_user_id = int(user.id)
                    self.signed_in = True
                    self.must_change_password = bool(
                        user.must_change_password
                    )
                    if self.must_change_password:
                        yield rx.redirect("/set-password")
                    elif user.role in DASHBOARD_ROUTES:
                        yield rx.redirect(DASHBOARD_ROUTES[user.role])
                case _:
                    self.message = "Invalid email or password"
        except Exception as exc:
            logging.exception("Unexpected error")
            self._session_user_id = 0
            self.signed_in = False
            self.full_name = ""
            self.role = ""
            self.message = (
                "Sign-in is temporarily unavailable. Please try again later."
            )
        finally:
            password = ""
            form_data.clear()
            self.loading = False
            self.password_revision += 1

    @rx.event
    async def sign_out(self):
        if self.loading:
            return
        from UniFlow_.states.admin_state import AdminState

        admin = await self.get_state(AdminState)
        admin._clear_access()
        await self._clear_dashboard_access()
        self._clear_session()
        return rx.redirect("/")
