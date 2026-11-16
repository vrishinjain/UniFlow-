import reflex as rx

import asyncio
import csv
import io
import logging
import re
import unicodedata
import hashlib
from concurrent.futures import TimeoutError as FutureTimeoutError

from UniFlow_.course_assignment_services import (
    ASSIGNMENT_MAX_BYTES,
    SkippedAssignmentLine,
    decode_assignment_file,
    save_course_assignments,
)

from UniFlow_.course_assignment_services import (
    export_course_preferences_csv,
    get_assignment_course_context,
)
from UniFlow_.courses_services import parse_course_id
from UniFlow_.states.role_guard import check_dashboard_access


_DENIED = "You don't have permission to export this course's preferences"
_IMPORT_DENIED = (
    "You don't have permission to import assignments for this course"
)
UPLOAD_ID = "course_assignment_txt"
_EMPTY_CONTEXT = (0, "", 0, "", "", 0)


class AssignmentState(rx.State):
    export_busy: bool = False
    export_error: str = ""
    import_busy: bool = False
    import_error: str = ""
    import_message: str = ""
    skipped_rows: list[SkippedAssignmentLine] = []
    replacement_open: bool = False
    existing_count: int = 0
    _pending_text: str = ""
    _pending_context: tuple[int, str, int, str, str, int] = _EMPTY_CONTEXT
    _selection_context: tuple[int, str, int, str, str, int] = _EMPTY_CONTEXT
    _pending_snapshot: str = ""
    _import_token: int = 0
    _save_running: bool = False

    @rx.var
    def busy(self) -> bool:
        return self.export_busy or self.import_busy

    @rx.var
    async def import_context_key(self) -> str:
        context = await self._context()
        return hashlib.sha256(repr(context).encode("utf-8")).hexdigest()

    async def _context(self) -> tuple[int, str, int, str, str, int]:
        from UniFlow_.states.login_state import LoginState
        from UniFlow_.states.faculty_state import FacultyState

        login = await self.get_state(LoginState)
        faculty = await self.get_state(FacultyState)
        return (
            login._session_user_id
            if login.signed_in and not login.must_change_password
            else 0,
            login.role,
            login.password_revision,
            self.router.page.path,
            str(self.router.page.params.get("id", "")),
            faculty._courses_epoch,
        )

    async def _authorized(
        self, actor_id: int, role: str, *, background: bool = True
    ) -> bool:
        account, _ = await check_dashboard_access(
            self,
            role if role in {"faculty", "system_admin"} else "faculty",
            background=background,
        )
        return (
            role in {"faculty", "system_admin"}
            and account is not None
            and account.id == actor_id
            and account.role == role
            and not account.must_change_password
        )

    def _filename(self, code: str, term: str) -> str:
        parts: list[str] = []
        for value in (code, term):
            safe = "".join(
                "_"
                if char.isspace() or unicodedata.category(char).startswith("C")
                else char
                for char in value
            )
            safe = re.sub(r'[\\/<>:"|?*]', "_", safe)
            safe = safe.replace("..", "_").strip(" ._")[:80] or "course"
            parts.append(safe)
        return f"preferences_{parts[0]}_{parts[1]}.csv"

    @rx.event(background=True)
    async def export_preferences(self):
        async with self:
            context = await self._context()
        actor_id, role, _, path, route_id, _ = context
        allowed = await self._authorized(actor_id, role)
        async with self:
            if context != await self._context():
                return
            if not allowed:
                self.export_error = _DENIED
                yield rx.toast.error(_DENIED)
                return
            if self.busy or self.replacement_open:
                return
            self.export_error = ""
            self.export_busy = True

        csv_text = ""
        filename = ""
        empty = False
        error = ""
        denied = False
        try:
            course_id = parse_course_id(route_id)
            if path.rstrip("/") not in {
                "/faculty/course/[id]",
                f"/faculty/course/{route_id}",
            }:
                raise PermissionError(_DENIED)
            csv_text = await asyncio.to_thread(
                export_course_preferences_csv, actor_id, course_id
            )
            course = await asyncio.to_thread(
                get_assignment_course_context, actor_id, course_id
            )
            filename = self._filename(course["code"], course["term"])
            reader = csv.reader(io.StringIO(csv_text, newline=""))
            next(reader)
            empty = next(reader, None) is None
        except (PermissionError, ValueError):
            denied = True
        except Exception:
            logging.exception("Failed to export course preferences")
            error = "Preferences could not be exported. Please try again."

        allowed = await self._authorized(actor_id, role)
        async with self:
            self.export_busy = False
            if context != await self._context():
                self.export_error = ""
                return
            if denied or not allowed:
                self.export_error = _DENIED
                yield rx.toast.error(_DENIED)
            elif error:
                self.export_error = error
                yield rx.toast.error(error)
            elif empty:
                self.export_error = ""
                yield rx.toast.info("No student preferences submitted yet")
            else:
                self.export_error = ""
                yield rx.download(data=csv_text, filename=filename)

    def _discard_pending(self):
        self._pending_text = ""
        self._pending_context = _EMPTY_CONTEXT
        self._pending_snapshot = ""
        self.replacement_open = False
        self.existing_count = 0
        self._import_token += 1

    def _clear_import_feedback(self):
        self.import_error = ""
        self.import_message = ""
        self.skipped_rows = []

    async def _guard_import(
        self,
        context: tuple[int, str, int, str, str, int],
        *,
        background: bool = True,
    ) -> str:
        actor_id, role, _, path, route_id, _ = context
        if not await self._authorized(actor_id, role, background=background):
            return _IMPORT_DENIED
        try:
            course_id = parse_course_id(route_id)
            if path.rstrip("/") not in {
                "/faculty/course/[id]",
                f"/faculty/course/{route_id}",
            }:
                return _IMPORT_DENIED
            await asyncio.to_thread(
                get_assignment_course_context, actor_id, course_id
            )
        except (PermissionError, ValueError):
            return _IMPORT_DENIED
        except Exception:
            logging.exception("Could not verify assignment import access")
            return "Assignment access could not be verified. Please try again."
        return ""

    @rx.event(background=True)
    async def initialize_import(self):
        async with self:
            context = await self._context()
        error = await self._guard_import(context)
        async with self:
            if context != await self._context():
                return
            self._discard_pending()
            self._clear_import_feedback()
            self._selection_context = context if not error else _EMPTY_CONTEXT
            self.import_error = error
        yield rx.clear_selected_files(UPLOAD_ID)

    @rx.event
    async def upload_assignments(self, files: list[rx.UploadFile]):
        """Bounded upload only; validation and saving run in the background."""
        context = await self._context()
        try:
            error = await self._guard_import(context, background=False)
            if error:
                self._discard_pending()
                self._clear_import_feedback()
                self.import_error = error
                return
            if self.busy or self.replacement_open:
                return
            if (
                context != self._selection_context
                or context != await self._context()
            ):
                self._discard_pending()
                self._clear_import_feedback()
                self.import_error = (
                    "The course or session changed. Select the file again."
                )
                return
            self._discard_pending()
            self._clear_import_feedback()
            if len(files) != 1:
                self.import_error = (
                    "Choose exactly one UTF-8 .txt file, up to 1 MB."
                )
                return
            data = await files[0].read(ASSIGNMENT_MAX_BYTES + 1)
            self._pending_text = decode_assignment_file(
                files[0].filename or "", data
            )
            if context != await self._context():
                self._discard_pending()
                self.import_error = (
                    "The course or session changed. Select the file again."
                )
                return
            self._pending_context = context
            self.import_busy = True
            yield AssignmentState.import_assignments
        except (ValueError, OSError) as exc:
            self._discard_pending()
            self.import_error = (
                str(exc)
                if isinstance(exc, ValueError)
                else "The file could not be read. Select it again and retry."
            )
        except Exception:
            logging.exception("Failed to receive assignment text file")
            self._discard_pending()
            self.import_error = (
                "The file could not be read. Select it again and retry."
            )
        finally:
            for file in files:
                try:
                    await file.close()
                except OSError:
                    logging.exception("Could not close assignment upload")
            yield rx.clear_selected_files(UPLOAD_ID)

    async def _can_save(
        self, context: tuple[int, str, int, str, str, int], token: int
    ) -> bool:
        async with self:
            return (
                context == await self._context()
                and context == self._pending_context
                and token == self._import_token
            )

    async def _perform_import(self, *, replace: bool):
        async with self:
            context = await self._context()
            pending_context = self._pending_context
            content = self._pending_text
            snapshot = self._pending_snapshot
            token = self._import_token
        error = await self._guard_import(context)
        async with self:
            if self._save_running and not error:
                return
            if (
                error
                or context != await self._context()
                or context != pending_context
            ):
                self._discard_pending()
                self._clear_import_feedback()
                self.import_busy = False
                self.import_error = (
                    error
                    or "The course or session changed. Select the file again."
                )
                return
            if self.export_busy or (replace and self.import_busy):
                return
            if replace and not self.replacement_open:
                self.import_error = (
                    "Select and import a file before confirming replacement."
                )
                return
            self.import_busy = True
            self._save_running = True
            self.import_error = ""
        loop = asyncio.get_running_loop()

        def current() -> bool:
            future = asyncio.run_coroutine_threadsafe(
                self._can_save(context, token), loop
            )
            try:
                return future.result(timeout=5)
            except FutureTimeoutError:
                future.cancel()
                return False

        result = None
        try:
            result = await asyncio.to_thread(
                save_course_assignments,
                context[0],
                parse_course_id(context[4]),
                content,
                replace=replace,
                expected_snapshot=snapshot,
                context_is_current=current,
            )
        except PermissionError:
            error = _IMPORT_DENIED
        except ValueError:
            error = "Assignments could not be imported. Select a valid UTF-8 .txt file and retry."
        except Exception:
            logging.exception("Failed to import course assignments")
            error = "Assignments could not be saved. Nothing was changed. Please retry the import."
        access_error = await self._guard_import(context)
        async with self:
            self.import_busy = False
            self._save_running = False
            if context != await self._context() or token != self._import_token:
                self._discard_pending()
                self._clear_import_feedback()
                return
            if access_error or error:
                self.import_error = access_error or error
                if access_error or error == _IMPORT_DENIED:
                    self._discard_pending()
                    self.skipped_rows = []
                    self.import_message = ""
                # A replacement failure keeps its original payload for an explicit retry.
                elif not replace:
                    self._discard_pending()
                return
            if result is not None:
                self.skipped_rows = result["skipped"]
                self.import_message = result["message"]
                if result["confirmation_required"]:
                    self._pending_snapshot = result["snapshot"]
                    self.existing_count = result["existing_count"]
                    self.replacement_open = True
                else:
                    self._discard_pending()

    @rx.event(background=True)
    async def import_assignments(self):
        async with self:
            pass
        await self._perform_import(replace=False)

    @rx.event(background=True)
    async def replace_assignments(self):
        async with self:
            pass
        await self._perform_import(replace=True)

    async def _cancel_import(self):
        async with self:
            context = await self._context()
        error = await self._guard_import(context)
        async with self:
            if context != await self._context() or (
                self._pending_context != _EMPTY_CONTEXT
                and context != self._pending_context
            ):
                error = _IMPORT_DENIED
            if self.import_busy and not error:
                return
            self._discard_pending()
            self._clear_import_feedback()
            self.import_error = error
        yield rx.clear_selected_files(UPLOAD_ID)

    @rx.event(background=True)
    async def cancel_import(self):
        async with self:
            pass
        async for event in self._cancel_import():
            yield event
