import reflex as rx

import asyncio
import logging

from UniFlow_.states.login_state import LoginState
from UniFlow_.user_services import get_user_by_id


class SponsorState(rx.State):
    full_name: str = ""
    _authorized: bool = False

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""

    @rx.event
    async def load_sponsor(self):
        self._clear_access()
        yield
        login = await self.get_state(LoginState)
        session_id = login._session_user_id
        if not login.signed_in or session_id <= 0 or login.role != "sponsor":
            yield rx.redirect("/")
            return
        try:
            account = await asyncio.to_thread(get_user_by_id, session_id)
        except Exception as e:
            logging.exception(f"Error: {e}")
            yield rx.redirect("/")
            return
        if (
            account is None
            or account.status != "active"
            or account.id != session_id
            or account.role != "sponsor"
            or not login.signed_in
            or login._session_user_id != session_id
            or login.role != "sponsor"
        ):
            yield rx.redirect("/")
            return
        self.full_name = str(account.full_name).strip()
        self._authorized = True

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
