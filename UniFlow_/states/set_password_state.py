import reflex as rx

import asyncio
import logging
from typing import Any

from UniFlow_.states.login_state import DASHBOARD_ROUTES, LoginState
from UniFlow_.user_services import set_new_password


class SetPasswordState(rx.State):
    """First-login page: users with a temporary password must choose their own."""

    message: str = ""
    saving: bool = False
    form_revision: int = 0
    _authorized: bool = False

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    @rx.event
    async def load_set_password(self):
        self._authorized = False
        self.message = ""
        login = await self.get_state(LoginState)
        if not login.signed_in or login._session_user_id <= 0:
            return rx.redirect("/")
        if not login.must_change_password:
            # Nothing to do here; send them to their own dashboard.
            return rx.redirect(DASHBOARD_ROUTES.get(login.role, "/"))
        self._authorized = True

    @rx.event
    async def save_password(self, form_data: dict[str, Any]):
        new_password = str(form_data.pop("new_password", ""))
        confirm_password = str(form_data.pop("confirm_password", ""))
        form_data.clear()
        if self.saving or not self._authorized:
            return
        self.message = ""
        if len(new_password) < 8:
            self.message = "Your new password must be at least 8 characters."
            return
        if new_password != confirm_password:
            self.message = "The two passwords don't match."
            return

        login = await self.get_state(LoginState)
        user_id = login._session_user_id
        if not login.signed_in or user_id <= 0:
            yield rx.redirect("/")
            return

        self.saving = True
        yield
        try:
            await asyncio.to_thread(set_new_password, user_id, new_password)
        except ValueError as e:
            self.message = str(e)
            return
        except PermissionError:
            login._clear_session()
            yield rx.redirect("/")
            return
        except Exception:
            logging.exception("Unexpected error")
            self.message = "Something went wrong. Please try again."
            return
        finally:
            new_password = ""
            confirm_password = ""
            self.saving = False
            self.form_revision += 1

        login.must_change_password = False
        self._authorized = False
        yield rx.redirect(DASHBOARD_ROUTES.get(login.role, "/"))

    @rx.event
    async def sign_out(self):
        self._authorized = False
        login = await self.get_state(LoginState)
        login._clear_session()
        return rx.redirect("/")
