"""Shared access check for the role dashboards (T-2).

Every dashboard page calls check_dashboard_access() from its on_load event, so
the rules for "who may open this page" live in one place:
  - not signed in                -> sent to the login page
  - must still set a password    -> sent to /set-password
  - signed in with another role  -> sent to the login page, which forwards
                                    them to their own dashboard
"""

import asyncio
import logging

import reflex as rx

from UniFlow_.states.login_state import LoginState
from UniFlow_.user_services import get_user_by_id


async def check_dashboard_access(state: rx.State, role: str):
    """Return (account, "") if access is allowed, otherwise (None, redirect_url)."""
    login = await state.get_state(LoginState)
    session_id = login._session_user_id
    if not login.signed_in or session_id <= 0 or login.role != role:
        return None, "/"
    if login.must_change_password:
        return None, "/set-password"
    try:
        account = await asyncio.to_thread(get_user_by_id, session_id)
    except Exception as e:
        logging.exception(f"Error: {e}")
        return None, "/"
    # Re-check against the database: the account may have been changed or
    # deactivated since the user signed in.
    if (
        account is None
        or account.status != "active"
        or account.id != session_id
        or account.role != role
        or not login.signed_in
        or login._session_user_id != session_id
        or login.role != role
    ):
        return None, "/"
    return account, ""
