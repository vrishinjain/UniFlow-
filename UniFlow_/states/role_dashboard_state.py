import reflex as rx

import asyncio
import logging

from UniFlow_.user_services import get_user_by_email


class RoleDashboardState(rx.State):
    authorized: bool = False
    authorized_role: str = ""
    full_name: str = ""

    def _clear_authorization(self):
        self.authorized = False
        self.authorized_role = ""
        self.full_name = ""

    @rx.event
    async def authorize(self, expected_role: str):
        from UniFlow_.states.login_state import LoginState

        self._clear_authorization()
        yield
        login = await self.get_state(LoginState)
        if (
            not login.signed_in
            or login._authenticated_user_id <= 0
            or not login.email
            or expected_role
            not in {"student", "faculty", "program_admin", "sponsor"}
        ):
            yield rx.redirect("/")
            return

        try:
            user = await asyncio.to_thread(get_user_by_email, login.email)
        except Exception as exc:
            logging.exception(f"Error: {type(exc).__name__}")
            yield rx.redirect("/")
            return

        if (
            user is None
            or user.id != login._authenticated_user_id
            or user.email != login.email
            or user.status != "active"
            or user.role != login.role
            or user.role != expected_role
            or not login.signed_in
        ):
            yield rx.redirect("/")
            return

        self.full_name = str(user.full_name).strip()
        login.full_name = self.full_name
        self.authorized_role = expected_role
        self.authorized = True

    @rx.event
    async def logout(self):
        from UniFlow_.states.login_state import LoginState

        login = await self.get_state(LoginState)
        login._authenticated_user_id = 0
        login.signed_in = False
        login.email = ""
        login.full_name = ""
        login.role = ""
        login.message = ""
        login.loading = False
        login.password_revision += 1
        self._clear_authorization()
        return rx.redirect("/")
