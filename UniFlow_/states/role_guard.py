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


async def check_dashboard_access(
    state: rx.State, role: str, *, background: bool = False
):
    """Return (account, "") if access is allowed, otherwise (None, redirect_url)."""
    if background:
        async with state:
            login = await state.get_state(LoginState)
            session_id = login._session_user_id
            signed_in = login.signed_in
            login_role = login.role
            must_change_password = login.must_change_password
    else:
        login = await state.get_state(LoginState)
        session_id = login._session_user_id
        signed_in = login.signed_in
        login_role = login.role
        must_change_password = login.must_change_password
    if not signed_in or session_id <= 0 or login_role != role:
        return None, "/"
    if must_change_password:
        return None, "/set-password"
    try:
        account = await asyncio.to_thread(get_user_by_id, session_id)
    except Exception as e:
        logging.exception(f"Error: {e}")
        return None, "/"
    if background:
        async with state:
            login = await state.get_state(LoginState)
            still_signed_in = login.signed_in
            current_id = login._session_user_id
            current_role = login.role
            current_password_change = login.must_change_password
    else:
        still_signed_in = login.signed_in
        current_id = login._session_user_id
        current_role = login.role
        current_password_change = login.must_change_password
    # Re-check against the database: the account may have been changed or
    # deactivated since the user signed in.
    if (
        account is None
        or account.status != "active"
        or account.id != session_id
        or account.role != role
        or not still_signed_in
        or current_id != session_id
        or current_role != role
        or current_password_change
    ):
        return None, "/"
    return account, ""
