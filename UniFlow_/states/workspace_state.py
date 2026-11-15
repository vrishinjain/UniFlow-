import reflex as rx

import asyncio
import logging
from datetime import date
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from UniFlow_.states.login_state import LoginState
from UniFlow_.workspace_services import (
    WorkspaceMember,
    WorkspaceMilestone,
    WorkspaceTicket,
    WorkspaceSnapshot,
    TICKET_STATUSES,
    create_ticket,
    create_milestone,
    update_milestone,
    validate_milestone_fields,
    update_ticket,
    delete_ticket,
    move_ticket,
    validate_ticket_fields,
    validate_ticket_id,
    get_workspace,
)


class WorkspaceState(rx.State):
    title: str = ""
    team: list[WorkspaceMember] = []
    tickets: list[WorkspaceTicket] = []
    milestones: list[WorkspaceMilestone] = []
    selected_project_id: str = ""
    selected_assignee: str = ""
    selected_milestone: str = ""
    server_today: str = ""
    milestone_dialog_open: bool = False
    current_milestone_id: str = ""
    milestone_title: str = ""
    milestone_description: str = ""
    milestone_due_date: str = ""
    milestone_ticket_ids: list[str] = []
    actor_role: str = ""
    can_edit_milestones: bool = False
    loading: bool = False
    error: str = ""
    _authorized: bool = False
    _load_request: int = 0
    _actor_id: int = 0
    _password_revision: int = 0
    _mutation_running: bool = False
    dialog_open: bool = False
    delete_open: bool = False
    current_ticket_id: str = ""
    delete_id: str = ""
    delete_title: str = ""
    menu_ticket_id: str = ""
    form_title: str = ""
    form_description: str = ""
    form_priority: str = "Medium"
    form_assignee: str = ""
    form_milestone: str = ""
    mutation_error: str = ""
    saving: bool = False
    move_pending: str = ""
    keyboard_ticket_id: str = ""
    announcement: str = ""

    @rx.var
    def mutation_pending(self) -> bool:
        return self.saving or bool(self.move_pending) or self._mutation_running

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    @rx.var
    def visible_tickets(self) -> list[WorkspaceTicket]:
        if not self._authorized:
            return []
        return [
            ticket
            for ticket in self.tickets
            if (
                not self.selected_assignee
                or ticket["assignee"] == self.selected_assignee
            )
            and (
                not self.selected_milestone
                or ticket["milestone"] == self.selected_milestone
            )
        ]

    @rx.var
    def board_columns(self) -> list[dict[str, str | list[WorkspaceTicket]]]:
        return [
            {
                "status": status,
                "tickets": [
                    ticket
                    for ticket in self.visible_tickets
                    if ticket["status"] == status
                ],
            }
            for status in ("To Do", "In Progress", "Review", "Done")
        ]

    @rx.var
    def empty_filter_message(self) -> str:
        if self.selected_milestone and self.selected_assignee:
            return "No tickets match this milestone and assignee. Clear either filter to broaden the results."
        if self.selected_milestone:
            return "No tickets match this milestone. Clear the milestone filter to see all tickets."
        if self.selected_assignee:
            return "No tickets match this assignee. Clear the assignee filter to see all tickets."
        return "No tickets have been added to this project yet."

    @rx.var
    def empty_column_message(self) -> str:
        if self.selected_milestone and self.selected_assignee:
            return "No tickets for this milestone and assignee in this column."
        if self.selected_milestone:
            return "No tickets for this milestone in this column."
        if self.selected_assignee:
            return "No tickets for this assignee in this column."
        return "No tickets in this column."

    def _clear_dialogs(self):
        self.milestone_dialog_open = False
        self.current_milestone_id = ""
        self.milestone_title = ""
        self.milestone_description = ""
        self.milestone_due_date = ""
        self.milestone_ticket_ids = []
        self.dialog_open = False
        self.delete_open = False
        self.current_ticket_id = ""
        self.delete_id = ""
        self.delete_title = ""
        self.menu_ticket_id = ""
        self.form_title = ""
        self.form_description = ""
        self.form_priority = "Medium"
        self.form_assignee = ""
        self.form_milestone = ""
        self.mutation_error = ""
        self.keyboard_ticket_id = ""

    def _clear_access(self):
        self._clear_dialogs()
        self.saving = False
        self.move_pending = ""
        self.announcement = ""
        self._actor_id = 0
        self._password_revision = 0
        self._mutation_running = False
        self.title = ""
        self.team = []
        self.tickets = []
        self.milestones = []
        self.selected_project_id = ""
        self.selected_assignee = ""
        self.selected_milestone = ""
        self.server_today = ""
        self.actor_role = ""
        self.can_edit_milestones = False
        self.loading = False
        self.error = ""
        self._authorized = False
        self._load_request += 1

    def _route_identity(self) -> tuple[str, str]:
        return (
            str(self.router.page.params.get("project_id", "")),
            str(self.router.page.path),
        )

    @rx.event
    def clear_workspace(self):
        self._clear_access()

    @rx.event
    def load_workspace(self):
        self._clear_access()
        self.loading = True
        route_id, path = self._route_identity()
        return WorkspaceState.fetch_workspace(
            self._load_request, route_id, path, ""
        )

    async def _session_allowed(self) -> bool:
        login = await self.get_state(LoginState)
        route_id, _ = self._route_identity()
        valid = (
            login.signed_in
            and not login.must_change_password
            and login._session_user_id > 0
            and login._session_user_id == self._actor_id
            and login.password_revision == self._password_revision
            and self.selected_project_id == route_id
            and bool(route_id)
            and self._authorized
        )
        if not valid:
            self._clear_access()
        return valid

    @rx.event
    async def set_assignee(self, assignee: str):
        if not await self._session_allowed():
            return
        eligible = {member["id"] for member in self.team}
        if assignee == "" or assignee in eligible:
            self.selected_assignee = (
                "" if assignee == self.selected_assignee else assignee
            )

    @rx.event
    async def clear_assignee(self):
        if await self._session_allowed():
            self.selected_assignee = ""

    @rx.event
    async def set_milestone(self, milestone: str):
        if not await self._session_allowed():
            return
        valid = {item["id"] for item in self.milestones}
        if milestone == "" or milestone in valid:
            self.selected_milestone = (
                "" if milestone == self.selected_milestone else milestone
            )

    @rx.event
    async def clear_milestone(self):
        if await self._session_allowed():
            self.selected_milestone = ""

    def _apply_snapshot(self, snapshot: WorkspaceSnapshot):
        if self.selected_project_id != snapshot["id"]:
            self.selected_milestone = ""
            if self.selected_project_id:
                self.selected_assignee = ""
                self._clear_dialogs()
        valid_milestones = {item["id"] for item in snapshot["milestones"]}
        if self.selected_milestone not in valid_milestones:
            self.selected_milestone = ""
        self.server_today = date.today().isoformat()
        eligible = {member["id"] for member in snapshot["team"]}
        if self.selected_assignee not in eligible:
            self.selected_assignee = ""
        self.selected_project_id = snapshot["id"]
        self.title = snapshot["title"]
        self.team = snapshot["team"]
        self.tickets = snapshot["tickets"]
        self.milestones = snapshot["milestones"]
        self.actor_role = snapshot["actor_role"]
        self.can_edit_milestones = snapshot["can_edit_milestones"]
        self._authorized = True

    @rx.event(background=True)
    async def fetch_workspace(
        self, request: int, route_id: str, path: str, assignee: str
    ):
        async with self:
            if (
                request != self._load_request
                or (route_id, path) != self._route_identity()
            ):
                return
            self._clear_access()
            request = self._load_request
            self.loading = True
            login = await self.get_state(LoginState)
            actor_id = login._session_user_id
            session_revision = login.password_revision
            signed_in = login.signed_in
            password_required = login.must_change_password
        snapshot = None
        error = ""
        try:
            if not signed_in or password_required or actor_id <= 0:
                raise PermissionError("Access denied")
            if (
                not route_id.isascii()
                or not route_id.isdecimal()
                or len(route_id) > 19
            ):
                raise ValueError("Invalid project ID")
            project_id = int(route_id)
            if not 0 < project_id <= 9223372036854775807:
                raise ValueError("Invalid project ID")
            snapshot = await asyncio.to_thread(
                get_workspace, actor_id, project_id
            )
        except (PermissionError, ValueError):
            pass
        except (SQLAlchemyError, RuntimeError):
            logging.exception("Workspace read failed")
            error = "The workspace could not be loaded. Please try again."
        except Exception:
            logging.exception("Unexpected workspace read failure")
            error = "The workspace could not be loaded. Please try again."
        async with self:
            if (
                request != self._load_request
                or (route_id, path) != self._route_identity()
            ):
                return
            login = await self.get_state(LoginState)
            if (
                login._session_user_id != actor_id
                or login.password_revision != session_revision
                or login.signed_in != signed_in
                or login.must_change_password != password_required
            ):
                self._clear_access()
                return
            self.loading = False
            self.error = error
            if snapshot is None:
                return
            self.selected_assignee = assignee
            self._apply_snapshot(snapshot)
            self._actor_id = actor_id
            self._password_revision = session_revision

    @rx.event
    async def open_create_milestone(self):
        if not await self._session_allowed() or self.mutation_pending:
            return
        if not self.can_edit_milestones or self.actor_role != "faculty":
            return
        self._clear_dialogs()
        self.server_today = date.today().isoformat()
        self.milestone_dialog_open = True

    @rx.event
    async def open_edit_milestone(self, milestone_id: str):
        if not await self._session_allowed() or self.mutation_pending:
            return
        if not self.can_edit_milestones or self.actor_role != "faculty":
            return
        milestone = next(
            (item for item in self.milestones if item["id"] == milestone_id),
            None,
        )
        if milestone is None:
            self.mutation_error = "Milestone not found in this project."
            return
        self._clear_dialogs()
        self.server_today = date.today().isoformat()
        self.current_milestone_id = milestone_id
        self.milestone_title = milestone["title"]
        self.milestone_description = milestone["description"]
        self.milestone_due_date = milestone["due_date"]
        self.milestone_ticket_ids = [
            ticket["id"]
            for ticket in self.tickets
            if ticket["milestone"] == milestone_id
        ]
        self.milestone_dialog_open = True

    @rx.event
    async def toggle_milestone_ticket(self, ticket_id: str):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or not self.milestone_dialog_open
        ):
            return
        if not self.can_edit_milestones or self.actor_role != "faculty":
            return
        if not any(ticket["id"] == ticket_id for ticket in self.tickets):
            self.mutation_error = "Choose tickets from this project."
            return
        if ticket_id in self.milestone_ticket_ids:
            self.milestone_ticket_ids = [
                value
                for value in self.milestone_ticket_ids
                if value != ticket_id
            ]
        else:
            self.milestone_ticket_ids.append(ticket_id)

    @rx.event
    async def submit_milestone(self, form_data: dict[str, Any]):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or not self.milestone_dialog_open
        ):
            return
        self.server_today = date.today().isoformat()
        self.milestone_title = (
            form_data.get("title", "")
            if isinstance(form_data.get("title"), str)
            else ""
        )
        self.milestone_description = (
            form_data.get("description", "")
            if isinstance(form_data.get("description"), str)
            else ""
        )
        self.milestone_due_date = (
            form_data.get("due_date", "")
            if isinstance(form_data.get("due_date"), str)
            else ""
        )
        try:
            validate_milestone_fields(
                form_data.get("title"),
                form_data.get("description"),
                form_data.get("due_date"),
            )
            selected = form_data.get("ticket_ids", self.milestone_ticket_ids)
            if not isinstance(selected, list):
                raise ValueError("Choose tickets from this project.")
            ids = list(
                dict.fromkeys(
                    str(validate_ticket_id(value)) for value in selected
                )
            )
            if not set(ids).issubset({ticket["id"] for ticket in self.tickets}):
                raise ValueError("Choose tickets from this project.")
            self.milestone_ticket_ids = ids
            if self.current_milestone_id:
                validate_ticket_id(self.current_milestone_id, "Milestone")
                if not any(
                    item["id"] == self.current_milestone_id
                    for item in self.milestones
                ):
                    raise ValueError("Milestone not found in this project.")
        except ValueError as exc:
            self.mutation_error = str(exc)
            return
        self.mutation_error = ""
        self.saving = True
        route_id, path = self._route_identity()
        return WorkspaceState.mutate_milestone(
            self._load_request, route_id, path, self.current_milestone_id
        )

    @rx.event(background=True)
    async def mutate_milestone(
        self, request: int, route_id: str, path: str, milestone_id: str
    ):
        async with self:
            if request != self._load_request:
                return
            if (route_id, path) != self._route_identity():
                self._clear_access()
                return
            if not await self._session_allowed() or self._mutation_running:
                return
            if not (
                self.saving
                and self.milestone_dialog_open
                and self.current_milestone_id == milestone_id
            ):
                self.saving = False
                return
            login = await self.get_state(LoginState)
            actor_id = login._session_user_id
            revision = login.password_revision
            fields = (
                self.milestone_title,
                self.milestone_description,
                self.milestone_due_date,
                list(self.milestone_ticket_ids),
            )
            self._mutation_running = True
        snapshot = None
        failure = ""
        denied = False
        try:
            project_id = validate_ticket_id(route_id, "Project")
            if milestone_id:
                target = validate_ticket_id(milestone_id, "Milestone")
                snapshot = await asyncio.to_thread(
                    update_milestone, actor_id, project_id, target, *fields
                )
            else:
                snapshot = await asyncio.to_thread(
                    create_milestone, actor_id, project_id, *fields
                )
        except PermissionError:
            denied = True
        except ValueError as exc:
            failure = str(exc)
        except (SQLAlchemyError, RuntimeError):
            logging.exception("Workspace milestone mutation failed")
            failure = "The milestone could not be saved. Please try again."
        except Exception:
            logging.exception("Unexpected workspace milestone mutation failure")
            failure = "The milestone could not be saved. Please try again."
        async with self:
            if request != self._load_request:
                return
            if (route_id, path) != self._route_identity():
                self._clear_access()
                return
            login = await self.get_state(LoginState)
            if (
                denied
                or login._session_user_id != actor_id
                or login.password_revision != revision
                or not login.signed_in
                or login.must_change_password
            ):
                self._clear_access()
                return
            self.saving = False
            self._mutation_running = False
            self.server_today = date.today().isoformat()
            if snapshot is not None:
                self._apply_snapshot(snapshot)
                self._clear_dialogs()
                self.announcement = "Milestone saved."
            else:
                self.mutation_error = failure
                self.announcement = failure

    @rx.event
    async def toggle_menu(self, ticket_id: str):
        if not await self._session_allowed() or self.mutation_pending:
            return
        if any(ticket["id"] == ticket_id for ticket in self.tickets):
            self.menu_ticket_id = (
                "" if self.menu_ticket_id == ticket_id else ticket_id
            )

    @rx.event
    async def open_create(self):
        if not await self._session_allowed() or self.mutation_pending:
            return
        self._clear_dialogs()
        self.dialog_open = True

    @rx.event
    async def open_edit(self, ticket_id: str):
        if not await self._session_allowed() or self.mutation_pending:
            return
        ticket = next(
            (ticket for ticket in self.tickets if ticket["id"] == ticket_id),
            None,
        )
        if ticket is None:
            self.mutation_error = "Ticket not found in this project."
            return
        self._clear_dialogs()
        self.current_ticket_id = ticket_id
        self.form_title = ticket["title"]
        self.form_description = ticket["description"]
        self.form_priority = ticket["priority"]
        self.form_assignee = ticket["assignee"]
        self.form_milestone = ticket["milestone"]
        self.dialog_open = True

    @rx.event
    async def open_delete(self, ticket_id: str):
        if not await self._session_allowed() or self.mutation_pending:
            return
        ticket = next(
            (ticket for ticket in self.tickets if ticket["id"] == ticket_id),
            None,
        )
        if ticket is None:
            self.mutation_error = "Ticket not found in this project."
            return
        self._clear_dialogs()
        self.delete_id = ticket_id
        self.delete_title = ticket["title"]
        self.delete_open = True

    @rx.event
    async def close_dialog(self):
        if await self._session_allowed() and not self.mutation_pending:
            self._clear_dialogs()

    @rx.event
    async def dialog_changed(self, opened: bool):
        if (
            await self._session_allowed()
            and not opened
            and not self.mutation_pending
        ):
            self._clear_dialogs()

    @rx.event
    async def submit_ticket(self, form_data: dict[str, Any]):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or not self.dialog_open
        ):
            return
        self.form_title = (
            form_data.get("title", "")
            if isinstance(form_data.get("title", ""), str)
            else ""
        )
        self.form_description = (
            form_data.get("description", "")
            if isinstance(form_data.get("description", ""), str)
            else ""
        )
        self.form_priority = (
            form_data.get("priority", "")
            if isinstance(form_data.get("priority", ""), str)
            else ""
        )
        self.form_assignee = (
            form_data.get("assignee", "")
            if isinstance(form_data.get("assignee", ""), str)
            else ""
        )
        self.form_milestone = (
            form_data.get("milestone", "")
            if isinstance(form_data.get("milestone", ""), str)
            else ""
        )
        try:
            validate_ticket_fields(
                form_data.get("title"),
                form_data.get("description"),
                form_data.get("priority"),
                form_data.get("assignee"),
                form_data.get("milestone"),
            )
        except ValueError as exc:
            self.mutation_error = str(exc)
            return
        self.mutation_error = ""
        self.saving = True
        route_id, path = self._route_identity()
        return WorkspaceState.mutate_ticket(
            self._load_request,
            route_id,
            path,
            "update" if self.current_ticket_id else "create",
            self.current_ticket_id,
            "",
        )

    @rx.event
    async def confirm_delete(self):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or not self.delete_open
            or not self.delete_id
        ):
            return
        self.saving = True
        self.mutation_error = ""
        route_id, path = self._route_identity()
        return WorkspaceState.mutate_ticket(
            self._load_request, route_id, path, "delete", self.delete_id, ""
        )

    @rx.event
    async def change_status(self, ticket_id: str, status: str):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or self.milestone_dialog_open
        ):
            return
        ticket = next(
            (ticket for ticket in self.tickets if ticket["id"] == ticket_id),
            None,
        )
        if ticket is None or status not in TICKET_STATUSES:
            self.mutation_error = "Choose a valid ticket and status."
            return
        if ticket["status"] == status:
            return
        self.move_pending = ticket_id
        self.keyboard_ticket_id = ""
        self.menu_ticket_id = ""
        self.mutation_error = ""
        route_id, path = self._route_identity()
        return WorkspaceState.mutate_ticket(
            self._load_request, route_id, path, "move", ticket_id, status
        )

    @rx.event
    async def drop_ticket(self, item: dict[str, Any], target: str):
        if not await self._session_allowed() or self.mutation_pending:
            return
        source = item.get("id", "")
        if not isinstance(source, str) or not source.startswith("ticket:"):
            self.mutation_error = "Invalid ticket drop."
            return
        ticket_id = source.removeprefix("ticket:")
        if target.startswith("column:"):
            status = target.removeprefix("column:")
        elif target.startswith("ticket:"):
            target_id = target.removeprefix("ticket:")
            ticket = next(
                (
                    ticket
                    for ticket in self.tickets
                    if ticket["id"] == target_id
                ),
                None,
            )
            status = ticket["status"] if ticket else ""
        else:
            status = ""
        return WorkspaceState.change_status(ticket_id, status)

    @rx.event
    async def keyboard_pickup(self, ticket_id: str):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or self.milestone_dialog_open
        ):
            return
        if any(ticket["id"] == ticket_id for ticket in self.tickets):
            self.keyboard_ticket_id = (
                "" if self.keyboard_ticket_id == ticket_id else ticket_id
            )
            self.announcement = (
                "Ticket selected. Tab to a column's Move here button and press Enter, or press this handle again to cancel."
                if self.keyboard_ticket_id
                else "Move cancelled."
            )

    @rx.event
    async def keyboard_drop(self, status: str):
        if (
            not await self._session_allowed()
            or self.mutation_pending
            or not self.keyboard_ticket_id
        ):
            return
        return WorkspaceState.change_status(self.keyboard_ticket_id, status)

    @rx.event(background=True)
    async def mutate_ticket(
        self,
        request: int,
        route_id: str,
        path: str,
        operation: str,
        ticket_id: str,
        status: str,
    ):
        async with self:
            if (
                request != self._load_request
                or (route_id, path) != self._route_identity()
            ):
                return
            if not await self._session_allowed():
                return
            login = await self.get_state(LoginState)
            actor_id = login._session_user_id
            revision = login.password_revision
            if self._mutation_running:
                return
            fields = (
                self.form_title,
                self.form_description,
                self.form_priority,
                self.form_assignee,
                self.form_milestone,
            )
            if operation in ("create", "update") and not (
                self.saving
                and self.dialog_open
                and self.current_ticket_id == ticket_id
            ):
                return
            if operation == "delete" and not (
                self.saving and self.delete_open and self.delete_id == ticket_id
            ):
                return
            if operation == "move" and self.move_pending != ticket_id:
                return
            if operation not in ("create", "update", "delete", "move"):
                return
            self._mutation_running = True
        snapshot = None
        failure = ""
        denied = False
        succeeded = False
        try:
            project_id = validate_ticket_id(route_id, "Project")
            if operation == "create":
                snapshot = await asyncio.to_thread(
                    create_ticket, actor_id, project_id, *fields
                )
            elif operation == "update":
                target = validate_ticket_id(ticket_id)
                snapshot = await asyncio.to_thread(
                    update_ticket, actor_id, project_id, target, *fields
                )
            elif operation == "delete":
                target = validate_ticket_id(ticket_id)
                snapshot = await asyncio.to_thread(
                    delete_ticket, actor_id, project_id, target
                )
            elif operation == "move":
                target = validate_ticket_id(ticket_id)
                snapshot = await asyncio.to_thread(
                    move_ticket, actor_id, project_id, target, status
                )
            else:
                raise ValueError("Invalid ticket operation.")
            succeeded = True
        except PermissionError:
            denied = True
        except ValueError as exc:
            failure = str(exc)
        except (SQLAlchemyError, RuntimeError):
            logging.exception("Workspace ticket mutation failed")
            failure = "The change could not be confirmed. Please try again."
        except Exception:
            logging.exception("Unexpected workspace ticket mutation failure")
            failure = "The change could not be confirmed. Please try again."
        if failure:
            try:
                snapshot = await asyncio.to_thread(
                    get_workspace, actor_id, int(route_id)
                )
            except PermissionError:
                denied = True
            except (ValueError, SQLAlchemyError, RuntimeError):
                logging.exception(
                    "Workspace refresh after ticket failure failed"
                )
            except Exception:
                logging.exception("Unexpected workspace refresh failure")
        async with self:
            if (
                request != self._load_request
                or (route_id, path) != self._route_identity()
            ):
                return
            login = await self.get_state(LoginState)
            if (
                denied
                or login._session_user_id != actor_id
                or login.password_revision != revision
                or not login.signed_in
                or login.must_change_password
            ):
                self._clear_access()
                return
            self.saving = False
            self.move_pending = ""
            self._mutation_running = False
            if snapshot is not None:
                self._apply_snapshot(snapshot)
            if succeeded:
                self._clear_dialogs()
                self.announcement = (
                    "Ticket deleted."
                    if operation == "delete"
                    else "Ticket saved."
                )
            else:
                self.mutation_error = failure
                self.announcement = failure
                if snapshot is None:
                    self.mutation_error = f"{failure} Refresh is unavailable; no local changes have been applied."
