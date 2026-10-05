import asyncio
import logging
from typing import Any

import reflex as rx

from UniFlow_.user_services import create_user

# What the user picks in the form -> the role saved in the database.
# Admin roles are never offered here; admins are created separately.
# "external" -> "sponsor" is an assumption: confirm it with the team.
ACCOUNT_TYPES = {
    "student": "student",
    "faculty": "faculty",
    "external": "sponsor",
}

MIN_PASSWORD_LENGTH = 8


class SignupState(rx.State):
    loading: bool = False
    message: str = ""
    submitted: bool = False
    submitted_email: str = ""

    @rx.event
    def reset_form(self):
        self.loading = False
        self.message = ""
        self.submitted = False
        self.submitted_email = ""

    @rx.event
    def clear_feedback(self):
        if not self.loading:
            self.message = ""

    @rx.event
    async def request_account(self, form_data: dict[str, Any]):
        if self.loading or self.submitted:
            return

        full_name = str(form_data.get("full_name", "")).strip()
        # Same rule as the login page (strip only). If the team decides to
        # lowercase emails, change it here AND in login_state.py.
        email = str(form_data.get("email", "")).strip()
        password = str(form_data.get("password", ""))
        confirm = str(form_data.get("confirm_password", ""))
        role = ACCOUNT_TYPES.get(str(form_data.get("account_type", "")))

        if not full_name or not email:
            self.message = "Enter your full name and email address."
            return
        if role is None:
            self.message = "Choose an account type."
            return
        if len(password) < MIN_PASSWORD_LENGTH:
            self.message = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            return
        if password != confirm:
            self.message = "Passwords don't match."
            return

        self.loading = True
        self.message = ""
        yield  # show "Sending request..." right away

        try:
            await asyncio.to_thread(create_user, full_name, email, password, role)
            self.submitted = True
            self.submitted_email = email
        except ValueError as e:
            # create_user raises ValueError with messages that are safe to show,
            # e.g. "A user with that email already exists."
            self.message = str(e)
        except Exception:
            logging.exception("Account request failed")
            self.message = "Your request couldn't be sent. Try again in a few minutes."
        finally:
            self.loading = False
