import reflex as rx

import asyncio
from typing import TypedDict

from UniFlow_.states.login_state import LoginState
from UniFlow_.user_services import (
    activate_user,
    BULK_EMAIL_MAX_BYTES,
    BulkEmailResult,
    bulk_approve_emails,
    parse_bulk_email_file,
    change_pending_user_role,
    get_user_by_id,
    list_active_users,
    list_pending_users,
    reject_user,
)

import logging


class PendingRequest(TypedDict):
    id: int
    full_name: str
    email: str
    role: str
    date_label: str
    date_iso: str


class ApprovedUser(TypedDict):
    id: int
    full_name: str
    email: str
    role: str


class AdminState(rx.State):
    requests: list[PendingRequest] = []
    approved_users: list[ApprovedUser] = []
    approved_error: bool = False
    loading: bool = False
    message: str = ""
    error: bool = False
    revision: int = 0
    _authorized: bool = False
    _bulk_results: list[BulkEmailResult] = []
    import_message: str = ""
    import_error: bool = False
    importing: bool = False

    @rx.var
    def bulk_results(self) -> list[BulkEmailResult]:
        return self._bulk_results if self._authorized else []

    @rx.var
    def already_approved_count(self) -> int:
        return (
            sum(
                row["outcome"] == "Already approved"
                for row in self._bulk_results
            )
            if self._authorized
            else 0
        )

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_import(self):
        self._bulk_results = []
        self.import_message = ""
        self.import_error = False

    def _clear_access(self):
        self._clear_import()
        self.importing = False
        self._authorized = False
        self.requests = []
        self.approved_users = []
        self.approved_error = False
        self.message = ""
        self.error = False
        self.loading = False

    async def _authorize(self) -> bool:
        login = await self.get_state(LoginState)
        self._authorized = False
        if not login._session_user_id:
            self._clear_access()
            return False
        try:
            user = await asyncio.to_thread(
                get_user_by_id, login._session_user_id
            )
        except Exception as e:
            logging.exception("Unexpected error")
            self._clear_access()
            login.message = "Account verification is temporarily unavailable. Please try again later."
            return False
        if (
            user is None
            or user.status != "active"
            or user.role != "system_admin"
        ):
            self._clear_access()
            if user is None or user.status != "active":
                login._clear_session()
            return False
        self._authorized = True
        return True

    async def _refresh(self) -> bool:
        if not await self._authorize():
            return False
        self.requests = []
        self.approved_users = []
        self.error = False
        self.approved_error = False
        try:
            users = await asyncio.to_thread(list_pending_users)
            self.requests = [
                PendingRequest(
                    id=int(user.id),
                    full_name=str(user.full_name),
                    email=str(user.email),
                    role=str(user.role),
                    date_label=user.created_at.strftime("%b %d, %Y · %H:%M %Z"),
                    date_iso=user.created_at.isoformat(),
                )
                for user in users
            ]
            self.revision += 1
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.error = True
            self.message = (
                "Requests could not be loaded. Please refresh and try again."
            )
        try:
            users = await asyncio.to_thread(list_active_users)
            role_labels = {
                "system_admin": "System admin",
                "program_admin": "Program admin",
                "faculty": "Faculty",
                "student": "Student",
                "sponsor": "Sponsor",
            }
            self.approved_users = [
                ApprovedUser(
                    id=int(user.id),
                    full_name=str(user.full_name),
                    email=str(user.email),
                    role=role_labels.get(
                        user.role, user.role.replace("_", " ").title()
                    ),
                )
                for user in users
            ]
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.approved_users = []
            self.approved_error = True
        return True

    @rx.event
    async def load_admin(self):
        self._clear_access()
        self.loading = True
        yield
        try:
            if not await self._refresh():
                yield rx.redirect("/")
                return
        finally:
            self.loading = False

    @rx.event
    async def refresh_requests(self):
        if self.loading:
            return
        self.loading = True
        self.message = ""
        self.error = False
        yield
        try:
            if not await self._refresh():
                yield rx.redirect("/")
        finally:
            self.loading = False

    async def _change(
        self, user_id: int, operation: str, role: str = ""
    ) -> bool:
        if not await self._authorize():
            return False
        try:
            if operation == "role":
                await asyncio.to_thread(change_pending_user_role, user_id, role)
                self.message = "Account role saved."
            elif operation == "approve":
                await asyncio.to_thread(activate_user, user_id)
                self.message = "Request approved. The user can now sign in."
            elif operation == "reject":
                await asyncio.to_thread(reject_user, user_id)
                self.message = "Request rejected."
            else:
                raise ValueError("Choose approve or reject for this request.")
        except ValueError as e:
            self.error = True
            self.message = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.error = True
            self.message = "The change could not be saved. Refresh the list before trying again."
        return await self._refresh()

    @rx.event
    async def change_role(self, user_id: int, role: str):
        if self.loading:
            return
        self.loading = True
        self.error = False
        self.message = ""
        yield
        try:
            if not await self._change(user_id, "role", role):
                yield rx.redirect("/")
        finally:
            self.loading = False

    @rx.event
    async def decide(self, user_id: int, decision: str):
        if self.loading:
            return
        self.loading = True
        self.error = False
        self.message = ""
        yield
        try:
            if decision not in {"approve", "reject"}:
                if not await self._authorize():
                    yield rx.redirect("/")
                    return
                self.error = True
                self.message = "Choose approve or reject for this request."
                return
            if not await self._change(user_id, decision):
                yield rx.redirect("/")
        finally:
            self.loading = False

    @rx.event
    def dismiss_import_results(self):
        self._clear_import()

    @rx.event
    async def import_emails(self, files: list[rx.UploadFile]):
        self._clear_import()
        if self.loading:
            self.import_error = True
            self.import_message = (
                "Wait for the current operation to finish, then try again."
            )
            yield rx.clear_selected_files("admin_bulk_emails")
            return
        self.loading = True
        self.importing = True
        self.import_message = "Validating the file and preparing accounts… Larger imports may take several minutes."
        yield
        results: list[BulkEmailResult] = []
        try:
            if not await self._authorize():
                yield rx.redirect("/")
                return
            if len(files) != 1:
                raise ValueError(
                    "Choose exactly one .txt or .csv file. Nothing was changed."
                )
            file = files[0]
            data = await file.read(BULK_EMAIL_MAX_BYTES + 1)
            addresses = parse_bulk_email_file(file.name or "", data)
            login = await self.get_state(LoginState)
            results = await asyncio.to_thread(
                bulk_approve_emails, login._session_user_id, addresses
            )
            if not await self._refresh():
                results.clear()
                yield rx.redirect("/")
                return
            self._bulk_results = results
            created = sum(row["outcome"] == "Created" for row in results)
            reactivated = sum(
                row["outcome"] == "Reactivated" for row in results
            )
            unchanged = sum(
                row["outcome"] == "Already approved" for row in results
            )
            self.import_message = f"Import complete: {created} created, {reactivated} reactivated, {unchanged} already approved (unchanged)."
            if self.error or self.approved_error:
                self.import_message = f"{self.import_message} Accounts were saved, but a dashboard list could not refresh. Use Refresh; keep these credentials before leaving."
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            self._clear_access()
            yield rx.redirect("/")
        except ValueError as e:
            self.import_error = True
            self.import_message = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.import_error = True
            self.import_message = "The import could not be completed. No accounts were changed. Please try again."
        finally:
            self.loading = False
            self.importing = False
            yield rx.clear_selected_files("admin_bulk_emails")

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
