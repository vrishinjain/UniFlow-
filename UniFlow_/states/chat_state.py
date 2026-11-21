import reflex as rx

import asyncio
import logging
import time

from sqlalchemy.exc import SQLAlchemyError

from UniFlow_.chat_services import (
    ChatMessage,
    ChatPage,
    ChatPoll,
    MAX_MESSAGE_LENGTH,
    delete_message,
    load_older_messages,
    open_project_chat,
    poll_messages,
    post_message,
    validate_message_body,
)
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.workspace_state import WorkspaceState


POLL_SECONDS = 3.0
IDLE_SECONDS = 15 * 60
MAX_FAILED_POLLS = 3
MAX_LOADED_MESSAGES = 500

_LOAD_FAILED = "The chat could not be loaded. Please try again."
_NO_ACCESS = "You don't have access to this chat."


class ChatState(rx.State):
    """Team chat for the project workspace.

    Each browser tab has its own state, so new messages from other people are
    picked up by a background task that polls every few seconds while the
    chat is open and expanded. Polling stops when the chat is collapsed, the
    page is left, the session changes, or after 15 minutes without activity.
    Every service call re-authorizes the actor in the database.
    """

    messages: list[ChatMessage] = []
    channel_id: str = ""
    has_older: bool = False
    draft: str = ""
    collapsed: bool = False
    loading: bool = False
    loading_older: bool = False
    sending: bool = False
    live: bool = False
    paused: bool = False
    pause_reason: str = ""
    error: str = ""
    send_error: str = ""
    confirm_delete_id: str = ""
    deleting_id: str = ""
    _actor_id: int = 0
    _password_revision: int = 0
    _project_id: str = ""
    _server_time: str = ""
    _session: int = 0
    _last_activity: float = 0.0

    # --- computed ---------------------------------------------------------

    @rx.var
    def messages_newest_first(self) -> list[ChatMessage]:
        # Rendered in a flex-col-reverse container, which keeps the view
        # pinned to the newest message without any scrolling script.
        return list(reversed(self.messages))

    @rx.var
    def draft_length(self) -> int:
        return len(self.draft)

    @rx.var
    def can_send(self) -> bool:
        return (
            not self.sending
            and not self.loading
            and bool(self.channel_id)
            and bool(self.draft.strip())
            and len(self.draft) <= MAX_MESSAGE_LENGTH
        )

    # --- helpers ----------------------------------------------------------

    def _reset(self):
        self.messages = []
        self.channel_id = ""
        self.has_older = False
        self.draft = ""
        self.loading = False
        self.loading_older = False
        self.sending = False
        self.live = False
        self.paused = False
        self.pause_reason = ""
        self.error = ""
        self.send_error = ""
        self.confirm_delete_id = ""
        self.deleting_id = ""
        self._actor_id = 0
        self._password_revision = 0
        self._project_id = ""
        self._server_time = ""
        self._session += 1

    def _clear_access(self):
        """Called by LoginState on sign-in and sign-out."""
        self._reset()

    def _touch(self):
        self._last_activity = time.time()

    async def _session_ok(self) -> bool:
        login = await self.get_state(LoginState)
        workspace = await self.get_state(WorkspaceState)
        valid = (
            login.signed_in
            and not login.must_change_password
            and login._session_user_id > 0
            and login._session_user_id == self._actor_id
            and login.password_revision == self._password_revision
            and workspace._authorized
            and bool(self._project_id)
            and workspace.selected_project_id == self._project_id
        )
        if not valid:
            self._reset()
        return valid

    def _merge(self, incoming: list[ChatMessage]):
        by_id = {message["id"]: message for message in self.messages}
        for message in incoming:
            by_id[message["id"]] = message
        merged = sorted(by_id.values(), key=lambda message: int(message["id"]))
        if len(merged) > MAX_LOADED_MESSAGES:
            merged = merged[-MAX_LOADED_MESSAGES:]
            self.has_older = True
        self.messages = merged

    def _mark_deleted(self, deleted_ids: list[str]):
        if not deleted_ids:
            return
        targets = set(deleted_ids)
        self.messages = [
            {**message, "body": "", "deleted": True, "can_delete": False}
            if message["id"] in targets and not message["deleted"]
            else message
            for message in self.messages
        ]
        if self.confirm_delete_id in targets:
            self.confirm_delete_id = ""

    def _apply_page(self, page: ChatPage):
        self.channel_id = page["channel_id"]
        self.messages = page["messages"]
        self.has_older = page["has_older"]
        self._server_time = page["server_time"]
        self.loading = False
        self.error = ""
        self.live = True
        self.paused = False
        self.pause_reason = ""

    def _apply_poll(self, poll: ChatPoll):
        self._merge(poll["messages"])
        self._mark_deleted(poll["deleted_ids"])
        self._server_time = poll["server_time"]

    def _newest_id(self) -> int:
        return int(self.messages[-1]["id"]) if self.messages else 0

    def _start(self):
        """Begin a fresh load + polling loop; returns the background event."""
        self._session += 1
        self.loading = True
        self.live = False
        self.paused = False
        self.pause_reason = ""
        self.error = ""
        self._touch()
        return ChatState.run_chat(self._session)

    # --- lifecycle --------------------------------------------------------

    @rx.event
    async def start_chat(self):
        """on_mount of the chat section (only rendered for authorized members)."""
        self._reset()
        login = await self.get_state(LoginState)
        workspace = await self.get_state(WorkspaceState)
        if not (
            login.signed_in
            and not login.must_change_password
            and login._session_user_id > 0
            and workspace._authorized
            and workspace.selected_project_id
        ):
            return
        self._actor_id = login._session_user_id
        self._password_revision = login.password_revision
        self._project_id = workspace.selected_project_id
        if self.collapsed:
            return
        return self._start()

    @rx.event
    def stop_chat(self):
        """on_unmount: stop polling and drop loaded messages."""
        self._reset()

    @rx.event
    async def toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self.confirm_delete_id = ""
        if self.collapsed:
            # Stop polling while hidden; keeps the database idle.
            self._session += 1
            self.live = False
            return
        if await self._session_ok():
            return self._start()

    @rx.event
    async def resume_chat(self):
        if self.collapsed or not await self._session_ok():
            return
        return self._start()

    @rx.event(background=True)
    async def run_chat(self, session: int):
        async with self:
            if session != self._session or not await self._session_ok():
                return
            actor_id = self._actor_id
            project_id = int(self._project_id)
        try:
            page = await asyncio.to_thread(open_project_chat, actor_id, project_id)
        except PermissionError:
            async with self:
                if session == self._session:
                    self.loading = False
                    self.error = _NO_ACCESS
            return
        except (SQLAlchemyError, RuntimeError, ValueError):
            logging.exception("Chat load failed")
            page = None
        except Exception:
            logging.exception("Unexpected chat load failure")
            page = None
        async with self:
            if session != self._session or not await self._session_ok():
                return
            if page is None:
                self.loading = False
                self.error = _LOAD_FAILED
                return
            self._apply_page(page)

        failures = 0
        while True:
            await asyncio.sleep(POLL_SECONDS)
            async with self:
                if session != self._session or not await self._session_ok():
                    return
                if time.time() - self._last_activity > IDLE_SECONDS:
                    self.live = False
                    self.paused = True
                    self.pause_reason = (
                        "Live updates paused after 15 minutes without activity."
                    )
                    return
                channel_id = int(self.channel_id)
                after_id = self._newest_id()
                since = self._server_time
            reload = False
            try:
                poll = await asyncio.to_thread(
                    poll_messages, actor_id, channel_id, after_id, since
                )
                failures = 0
                reload = poll["truncated"]
            except PermissionError:
                async with self:
                    if session == self._session:
                        self._reset()
                        self.error = "You no longer have access to this chat."
                return
            except Exception:
                logging.exception("Chat poll failed")
                failures += 1
                if failures >= MAX_FAILED_POLLS:
                    async with self:
                        if session == self._session:
                            self.live = False
                            self.paused = True
                            self.pause_reason = "Live updates stopped because the chat couldn't be reached."
                    return
                continue
            if reload:
                # Too many new messages to merge; fetch the latest page instead.
                try:
                    page = await asyncio.to_thread(
                        open_project_chat, actor_id, project_id
                    )
                except Exception:
                    logging.exception("Chat reload failed")
                    continue
                async with self:
                    if session != self._session:
                        return
                    self._apply_page(page)
                continue
            async with self:
                if session != self._session:
                    return
                self._apply_poll(poll)

    # --- composing --------------------------------------------------------

    @rx.event
    def update_draft(self, value: str):
        self.draft = value[: MAX_MESSAGE_LENGTH + 100]
        self.send_error = ""
        self._touch()

    @rx.event
    async def send_message(self, form_data: dict):
        if self.sending or not await self._session_ok() or not self.channel_id:
            return
        body = self.draft
        try:
            validate_message_body(body)
        except ValueError as exc:
            self.send_error = str(exc)
            return
        self.sending = True
        self.send_error = ""
        self._touch()
        return ChatState.do_send(self._session, body)

    @rx.event(background=True)
    async def do_send(self, session: int, body: str):
        async with self:
            if session != self._session or not await self._session_ok():
                return
            actor_id = self._actor_id
            channel_id = int(self.channel_id)
        message = None
        failure = ""
        denied = False
        try:
            message = await asyncio.to_thread(
                post_message, actor_id, channel_id, body
            )
        except PermissionError:
            denied = True
        except ValueError as exc:
            failure = str(exc)
        except (SQLAlchemyError, RuntimeError):
            logging.exception("Chat send failed")
            failure = "Your message couldn't be sent. Please try again."
        except Exception:
            logging.exception("Unexpected chat send failure")
            failure = "Your message couldn't be sent. Please try again."
        async with self:
            if session != self._session:
                return
            if denied:
                self._reset()
                self.error = "You no longer have access to this chat."
                return
            self.sending = False
            if message is not None:
                self._merge([message])
                if self.draft == body:
                    self.draft = ""
            else:
                self.send_error = failure

    # --- history ----------------------------------------------------------

    @rx.event
    async def load_older(self):
        if (
            self.loading_older
            or not self.has_older
            or not self.messages
            or not await self._session_ok()
        ):
            return
        self.loading_older = True
        self._touch()
        return ChatState.do_load_older(self._session, self.messages[0]["id"])

    @rx.event(background=True)
    async def do_load_older(self, session: int, before_id: str):
        async with self:
            if session != self._session or not await self._session_ok():
                return
            actor_id = self._actor_id
            channel_id = int(self.channel_id)
        page = None
        denied = False
        try:
            page = await asyncio.to_thread(
                load_older_messages, actor_id, channel_id, int(before_id)
            )
        except PermissionError:
            denied = True
        except Exception:
            logging.exception("Loading older chat messages failed")
        async with self:
            if session != self._session:
                return
            self.loading_older = False
            if denied:
                self._reset()
                self.error = "You no longer have access to this chat."
                return
            if page is None:
                self.send_error = "Older messages couldn't be loaded. Please try again."
                return
            self._merge(page["messages"])
            self.has_older = page["has_older"]

    # --- deleting ---------------------------------------------------------

    @rx.event
    def request_delete(self, message_id: str):
        target = next((m for m in self.messages if m["id"] == message_id), None)
        if target is not None and target["can_delete"] and not self.deleting_id:
            self.confirm_delete_id = message_id
        self._touch()

    @rx.event
    def cancel_delete(self):
        self.confirm_delete_id = ""

    @rx.event
    async def confirm_delete(self):
        message_id = self.confirm_delete_id
        if not message_id or self.deleting_id or not await self._session_ok():
            return
        self.deleting_id = message_id
        self.send_error = ""
        self._touch()
        return ChatState.do_delete(self._session, message_id)

    @rx.event(background=True)
    async def do_delete(self, session: int, message_id: str):
        async with self:
            if session != self._session or not await self._session_ok():
                return
            actor_id = self._actor_id
            channel_id = int(self.channel_id)
        message = None
        failure = ""
        denied = False
        try:
            message = await asyncio.to_thread(
                delete_message, actor_id, channel_id, int(message_id)
            )
        except PermissionError:
            denied = True
        except ValueError as exc:
            failure = str(exc)
        except Exception:
            logging.exception("Chat delete failed")
            failure = "The message couldn't be deleted. Please try again."
        async with self:
            if session != self._session:
                return
            if denied:
                self._reset()
                self.error = "You no longer have access to this chat."
                return
            self.deleting_id = ""
            self.confirm_delete_id = ""
            if message is not None:
                self._merge([message])
            else:
                self.send_error = failure
