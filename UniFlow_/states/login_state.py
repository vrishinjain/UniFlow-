import reflex as rx

import asyncio
import logging
from typing import Any

from UniFlow_.user_services import get_user_by_email, verify_password


class LoginState(rx.State):
    email: str = ""
    full_name: str = ""
    role: str = ""
    signed_in: bool = False
    loading: bool = False
    message: str = ""
    password_revision: int = 0

    @rx.event
    def clear_feedback(self):
        if not self.loading:
            self.message = ""

    @rx.event
    async def sign_in(self, form_data: dict[str, Any]):
        password = form_data.pop("password", "")
        if self.loading or self.signed_in:
            return
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
                    self.signed_in = True
                case _:
                    self.message = "Invalid email or password"
        except Exception as exc:
            # Suppress exception details that could contain connection or account data.

            logging.error("Sign-in failed (%s)", type(exc).name)
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
    def sign_out(self):
        if self.loading:
            return
        self.signed_in = False
        self.full_name = ""
        self.role = ""
        self.email = ""
        self.message = ""
        self.password_revision += 1
