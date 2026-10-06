import reflex as rx

import asyncio
from typing import Any

from UniFlow_.user_services import get_user_by_email, verify_password

import logging


class LoginState(rx.State):
    email: str = ""
    full_name: str = ""
    role: str = ""
    signed_in: bool = False
    loading: bool = False
    message: str = ""
    password_revision: int = 0
    _session_user_id: int = 0

    def _clear_session(self):
        self._session_user_id = 0
        self.signed_in = False
        self.full_name = ""
        self.role = ""
        self.email = ""
        self.message = ""
        self.password_revision += 1

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
                    self.full_name = str(user.full_name).strip()
                    self.role = str(user.role)
                    self.email = str(user.email)
                    self._session_user_id = int(user.id)
                    self.signed_in = True
                    if user.role == "system_admin":
                        yield rx.redirect("/admin")
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
        self._clear_session()
        return rx.redirect("/")
