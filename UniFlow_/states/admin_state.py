import reflex as rx

import asyncio
import csv
import io
from typing import TypedDict

from UniFlow_.states.login_state import LoginState
from UniFlow_.user_services import (
    activate_user,
    BULK_EMAIL_MAX_BYTES,
    BulkEmailResult,
    BulkEmailParse,
    CourseEmailEntry,
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
    _import_epoch: int = 0
    _pending_import: tuple[int, BulkEmailParse] = (
        0,
        {"addresses": [], "invalid_lines": []},
    )
    _import_invalid_lines: list[CourseEmailEntry] = []

    @rx.var
    def import_invalid_lines(self) -> list[CourseEmailEntry]:
        return self._import_invalid_lines if self._authorized else []

    @rx.var
    def bulk_results(self) -> list[BulkEmailResult]:
        return self._bulk_results if self._authorized else []

    @rx.var
    def has_issued_passwords(self) -> bool:
        return self._authorized and any(
            row["password"] and row["outcome"] in {"Created", "Reactivated"}
            for row in self._bulk_results
        )

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
        self._import_epoch += 1
        self._pending_import = (0, {"addresses": [], "invalid_lines": []})
        self._import_invalid_lines = []
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
    async def download_passwords(self):
        if not await self._authorize():
            return rx.redirect("/")
        if self.loading:
            return
        rows = [
            (row["email"], row["password"])
            for row in self._bulk_results
            if row["password"] and row["outcome"] in {"Created", "Reactivated"}
        ]
        if not rows:
            self.import_error = True
            self.import_message = (
                "No newly issued passwords are available to download."
            )
            return
        with io.StringIO(newline="") as output:
            writer = csv.writer(output, quoting=csv.QUOTE_ALL)
            writer.writerow(("email", "password"))
            writer.writerows(rows)
            data = output.getvalue().encode("utf-8")
        return rx.download(data=data, filename="uniflow_passwords.csv")

    @rx.event
    def dismiss_import_results(self):
        if not self.importing:
            self._clear_import()

    @rx.event
    async def import_emails(self, files: list[rx.UploadFile]):
        if self.loading or self.importing:
            yield rx.clear_selected_files("admin_bulk_emails")
            return
        self._clear_import()
        try:
            login = await self.get_state(LoginState)
            if not login._session_user_id or not self._authorized:
                self._clear_access()
                yield rx.redirect("/")
                return
            if len(files) != 1:
                raise ValueError(
                    "Choose exactly one .txt or .csv file. Nothing was changed."
                )
            file = files[0]
            data = await file.read(BULK_EMAIL_MAX_BYTES + 1)
            parsed = parse_bulk_email_file(file.name or "", data)
            self._pending_import = (login._session_user_id, parsed)
            self.loading = True
            self.importing = True
            self.import_message = "Validating access and preparing accounts… Larger imports may take several minutes."
            yield AdminState.process_email_import(self._import_epoch)
        except ValueError as e:
            logging.exception(f"Error: {e}")
            self.import_error = True
            self.import_message = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.import_error = True
            self.import_message = (
                "The selected file could not be read. No accounts were changed."
            )
        finally:
            yield rx.clear_selected_files("admin_bulk_emails")

    async def _verify_import_access(self, user_id: int, epoch: int) -> bool:
        async with self:
            login = await self.get_state(LoginState)
            if epoch != self._import_epoch or login._session_user_id != user_id:
                return False
        user = await asyncio.to_thread(get_user_by_id, user_id)
        if (
            user is None
            or user.role != "system_admin"
            or user.status != "active"
        ):
            raise PermissionError("Administrator access was lost.")
        async with self:
            login = await self.get_state(LoginState)
            return (
                epoch == self._import_epoch
                and login._session_user_id == user_id
                and self._authorized
            )

    @rx.event(background=True)
    async def process_email_import(self, epoch: int):
        async with self:
            if epoch != self._import_epoch or not self.importing:
                return
            user_id, parsed = self._pending_import
            if not user_id:
                return
            self._pending_import = (0, {"addresses": [], "invalid_lines": []})
        committed = False
        try:
            if not await self._verify_import_access(user_id, epoch):
                return
            addresses = [entry["email"] for entry in parsed["addresses"]]
            results: list[BulkEmailResult] = []
            if addresses:
                results = await asyncio.to_thread(
                    bulk_approve_emails, user_id, addresses
                )
                committed = True
            if not await self._verify_import_access(user_id, epoch):
                return
            created = sum(row["outcome"] == "Created" for row in results)
            reactivated = sum(
                row["outcome"] == "Reactivated" for row in results
            )
            unchanged = sum(
                row["outcome"] == "Already approved" for row in results
            )
            skipped = len(parsed["invalid_lines"])
            message = (
                f"Import complete: {len(addresses)} unique valid addresses; {created} created, {reactivated} reactivated, {unchanged} already approved (unchanged). {skipped} invalid lines skipped."
                if addresses
                else f"No valid email addresses were found. {skipped} invalid lines skipped; no accounts were changed. Correct the lines below and upload again."
            )
            requests: list[PendingRequest] = []
            approved: list[ApprovedUser] = []
            refresh_failed = False
            if addresses:
                try:
                    pending_users, active_users = await asyncio.gather(
                        asyncio.to_thread(list_pending_users),
                        asyncio.to_thread(list_active_users),
                    )
                    requests = [
                        PendingRequest(
                            id=int(user.id),
                            full_name=str(user.full_name),
                            email=str(user.email),
                            role=str(user.role),
                            date_label=user.created_at.strftime(
                                "%b %d, %Y · %H:%M %Z"
                            ),
                            date_iso=user.created_at.isoformat(),
                        )
                        for user in pending_users
                    ]
                    labels = {
                        "system_admin": "System admin",
                        "program_admin": "Program admin",
                        "faculty": "Faculty",
                        "student": "Student",
                        "sponsor": "Sponsor",
                    }
                    approved = [
                        ApprovedUser(
                            id=int(user.id),
                            full_name=str(user.full_name),
                            email=str(user.email),
                            role=labels.get(
                                user.role, user.role.replace("_", " ").title()
                            ),
                        )
                        for user in active_users
                    ]
                except Exception as e:
                    logging.exception(f"Error: {e}")
                    refresh_failed = True
                    message = f"{message} Accounts were saved, but dashboard lists could not refresh. Use Refresh; keep these credentials before leaving."
            if not await self._verify_import_access(user_id, epoch):
                return
            async with self:
                login = await self.get_state(LoginState)
                if (
                    epoch != self._import_epoch
                    or login._session_user_id != user_id
                ):
                    return
                self._bulk_results = results
                self._import_invalid_lines = parsed["invalid_lines"]
                self.import_error = not addresses
                self.import_message = message
                if addresses and not refresh_failed:
                    self.requests = requests
                    self.approved_users = approved
                    self.error = False
                    self.approved_error = False
                    self.revision += 1
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            async with self:
                if epoch != self._import_epoch:
                    return
                self._clear_access()
            yield rx.redirect("/")
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                if epoch != self._import_epoch:
                    return
                self._bulk_results = []
                self._import_invalid_lines = parsed["invalid_lines"]
                self.import_error = True
                self.import_message = (
                    "Accounts were saved, but access could not be verified. Credentials cannot be displayed; contact an administrator before retrying."
                    if committed
                    else str(e)
                    if isinstance(e, ValueError)
                    else "The import could not be completed. No accounts were changed. Please try again."
                )
        finally:
            async with self:
                if epoch == self._import_epoch:
                    self.loading = False
                    self.importing = False

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
