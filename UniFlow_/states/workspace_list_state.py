import reflex as rx

import asyncio
import logging

from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.workspace_list_services import WorkspaceListing, list_workspaces


class WorkspaceListState(rx.State):
    """Project workspaces page for faculty (/faculty/workspaces) and
    system admins (/admin/workspaces)."""

    workspaces: list[WorkspaceListing] = []
    loading: bool = True
    error: str = ""

    async def _load(self, role: str):
        async with self:
            self.workspaces = []
            self.error = ""
            self.loading = True

        account, _ = await check_dashboard_access(self, role, background=True)
        if account is None:
            async with self:
                self.loading = False
            return

        workspaces: list[WorkspaceListing] = []
        error = ""
        try:
            workspaces = await asyncio.to_thread(list_workspaces, int(account.id))
        except PermissionError:
            error = "You don't have access to this page."
        except Exception:
            logging.exception("Could not load project workspaces")
            error = "Project workspaces could not be loaded. Please try again."

        # The session may have changed while the list was loading.
        current, _ = await check_dashboard_access(self, role, background=True)
        async with self:
            self.loading = False
            if current is None or current.id != account.id:
                self.workspaces = []
                return
            self.workspaces = workspaces if not error else []
            self.error = error

    @rx.event(background=True)
    async def load_faculty_workspaces(self):
        await self._load("faculty")

    @rx.event(background=True)
    async def load_admin_workspaces(self):
        await self._load("system_admin")
