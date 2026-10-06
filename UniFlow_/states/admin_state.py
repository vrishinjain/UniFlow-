import asyncio
import logging
from typing import TypedDict

import reflex as rx

from UniFlow_.user_model import User
from UniFlow_.user_services import (
    ROLE_OPTIONS,
    activate_user,
    list_pending_users,
    reject_user,
)


class SampleUser(TypedDict):
    id: int
    name: str
    email: str
    role: str
    role_key: str
    date: str
    status: str
    initials: str


def _to_sample_user(user: User) -> SampleUser:
    name_parts = user.full_name.split()
    initials = "".join(part[0] for part in name_parts[:2]).upper()
    return SampleUser(
        id=user.id,
        name=user.full_name,
        email=user.email,
        role=user.role.replace("_", " ").title(),
        role_key=user.role,
        date=user.created_at.strftime("%b %d, %Y"),
        status=user.status.title(),
        initials=initials,
    )


def _display_users(
    pending: list[SampleUser], reviewed: list[SampleUser]
) -> list[SampleUser]:
    reviewed_ids = {user["id"] for user in reviewed}
    return [
        user for user in pending if user["id"] not in reviewed_ids
    ] + reviewed


class AdminState(rx.State):
    users: list[SampleUser] = []
    reviewed_users: list[SampleUser] = []
    processing_ids: list[int] = []
    selected_roles: dict[str, str] = {}
    announcement: str = ""

    @rx.var
    def role_options(self) -> list[dict[str, str]]:
        return [
            {"value": role, "label": role.replace("_", " ").title()}
            for role in ROLE_OPTIONS
        ]

    @rx.event
    def choose_role(self, user_id: int, role: str):
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            self.announcement = "This account is no longer pending review."
            return
        if not any(
            user["id"] == user_id and user["status"] == "Pending"
            for user in self.users
        ):
            self.announcement = "This account is no longer pending review."
            return
        if user_id in self.processing_ids:
            return
        if role not in ROLE_OPTIONS:
            self.announcement = "Please choose an allowed role."
            return
        self.selected_roles[str(user_id)] = role

    def _initialize_role_choices(self) -> None:
        for user in self.users:
            if user["status"] == "Pending":
                self.selected_roles.setdefault(
                    str(user["id"]), user["role_key"]
                )

    @rx.var
    def total_users(self) -> int:
        return len(self.users)

    @rx.var
    def pending_users(self) -> int:
        return sum(user["status"] == "Pending" for user in self.users)

    @rx.var
    def active_users(self) -> int:
        return sum(user["status"] == "Active" for user in self.users)

    @rx.var
    def rejected_users(self) -> int:
        return sum(user["status"] == "Rejected" for user in self.users)

    @rx.event(background=True)
    async def load_pending_users(self):
        try:
            pending_records = await asyncio.to_thread(list_pending_users)
            pending = [_to_sample_user(user) for user in pending_records]
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.announcement = (
                    "Unable to load pending accounts. Please try again."
                )
            return
        async with self:
            self.users = _display_users(pending, self.reviewed_users)
            self._initialize_role_choices()
            self.announcement = "Pending accounts refreshed."

    async def _review_account(self, user_id: int, approve: bool):
        async with self:
            requested = next(
                (
                    dict(user)
                    for user in self.users
                    if user["id"] == user_id and user["status"] == "Pending"
                ),
                None,
            )
            if (
                isinstance(user_id, bool)
                or not isinstance(user_id, int)
                or requested is None
            ):
                self.announcement = "This account is no longer pending review."
                return
            if user_id in self.processing_ids:
                return
            selected_role = self.selected_roles.get(
                str(user_id), requested["role_key"]
            )
            if approve and selected_role not in ROLE_OPTIONS:
                self.announcement = (
                    "Please choose an allowed role before approving."
                )
                return
            self.processing_ids.append(user_id)

        service = activate_user if approve else reject_user
        decision = "approved" if approve else "rejected"
        status = "Active" if approve else "Rejected"
        try:
            if approve:
                reviewed_record = await asyncio.to_thread(
                    service, user_id, role=selected_role
                )
            else:
                reviewed_record = await asyncio.to_thread(service, user_id)
            reviewed = _to_sample_user(reviewed_record)
            reviewed["role_key"] = requested["role_key"]
            reviewed["role"] = requested["role"]
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.processing_ids.remove(user_id)
                self.announcement = (
                    f"Unable to {decision} this account. Please try again."
                )
            return

        async with self:
            self._record_reviewed_user(reviewed)
            self.users = [
                reviewed if user["id"] == user_id else user
                for user in self.users
            ]

        try:
            pending_records = await asyncio.to_thread(list_pending_users)
            pending = [_to_sample_user(user) for user in pending_records]
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self._record_reviewed_user(reviewed)
                self.users = [
                    reviewed if user["id"] == user_id else user
                    for user in self.users
                ]
                self.processing_ids.remove(user_id)
                self.announcement = f"{reviewed['name']} {decision}. Pending accounts could not be refreshed."
            return

        async with self:
            self._record_reviewed_user(reviewed)
            self.users = _display_users(pending, self.reviewed_users)
            self._initialize_role_choices()
            self.processing_ids.remove(user_id)
            self.announcement = (
                f"{reviewed['name']} {decision}. Status is now {status}."
            )

    def _record_reviewed_user(self, reviewed: SampleUser) -> None:
        self.reviewed_users = [
            user for user in self.reviewed_users if user["id"] != reviewed["id"]
        ] + [reviewed]

    @rx.event(background=True)
    async def approve_user(self, user_id: int):
        async with self:
            pass
        await self._review_account(user_id, approve=True)

    @rx.event(background=True)
    async def reject_user(self, user_id: int):
        async with self:
            pass
        await self._review_account(user_id, approve=False)
