import reflex as rx

import asyncio
import logging
from typing import Any

from UniFlow_.courses_services import (
    CourseRow,
    EnrolledStudent,
    EnrollmentSummary,
    list_faculty_courses,
    get_faculty_course_detail,
    enroll_course_student,
    bulk_enroll_course_students,
    remove_course_student,
    parse_course_id,
)
from UniFlow_.user_services import BULK_EMAIL_MAX_BYTES
from pathlib import Path
from uuid import uuid4
from UniFlow_.courses_services import create_course as save_course

from UniFlow_.states.login_state import LoginState
from UniFlow_.states.role_guard import check_dashboard_access
from UniFlow_.project_services import (
    get_faculty_projects,
    get_faculty_project_details,
    get_faculty_project_file,
)


class FacultyState(rx.State):
    full_name: str = ""
    _authorized: bool = False

    projects: list[dict] = []
    selected_project: dict = {}
    files: list[dict] = []
    project_error: str = ""
    courses: list[CourseRow] = []
    courses_loading: bool = False
    courses_error: str = ""
    course_name: str = ""
    course_code: str = ""
    course_term: str = ""
    course_creating: bool = False
    course_error: str = ""
    course_success: str = ""
    course_form_revision: int = 0
    _courses_epoch: int = 0
    _courses_load_request: int = 0
    course_detail: dict[str, str] = {"name": "", "code": "", "term": ""}
    enrolled_students: list[EnrolledStudent] = []
    course_detail_loading: bool = False
    course_detail_error: str = ""
    course_detail_ready: bool = False
    enrollment_email: str = ""
    enrollment_busy: bool = False
    enrollment_error: str = ""
    enrollment_message: str = ""
    enrollment_summary: EnrollmentSummary = {
        "added": [],
        "already_enrolled": [],
        "no_account": [],
        "not_student": [],
        "not_approved": [],
        "invalid_lines": [],
    }
    enrollment_has_summary: bool = False
    _course_detail_request: int = 0
    _pending_course_upload: tuple[str, bytes, str, int, str] = (
        "",
        b"",
        "",
        0,
        "",
    )

    @rx.var
    def authorized(self) -> bool:
        return self._authorized

    def _clear_access(self):
        self._authorized = False
        self.full_name = ""
        self.projects = []
        self.selected_project = {}
        self.files = []
        self.project_error = ""
        self.courses = []
        self.courses_loading = False
        self.courses_error = ""
        self.course_name = ""
        self.course_code = ""
        self.course_term = ""
        self.course_creating = False
        self.course_error = ""
        self.course_success = ""
        self.course_form_revision += 1
        self._courses_epoch += 1
        self._courses_load_request += 1
        self.course_detail = {"name": "", "code": "", "term": ""}
        self.enrolled_students = []
        self.course_detail_loading = False
        self.course_detail_error = ""
        self.course_detail_ready = False
        self.enrollment_email = ""
        self.enrollment_busy = False
        self.enrollment_error = ""
        self.enrollment_message = ""
        self.enrollment_summary = {
            "added": [],
            "already_enrolled": [],
            "no_account": [],
            "not_student": [],
            "not_approved": [],
            "invalid_lines": [],
        }
        self.enrollment_has_summary = False
        self._course_detail_request = 0
        self._pending_course_upload = ("", b"", "", 0, "")

    async def _courses_session_matches(
        self, faculty_id: int, epoch: int
    ) -> bool:
        login = await self.get_state(LoginState)
        return (
            self._courses_epoch == epoch
            and login.signed_in
            and login._session_user_id == faculty_id
            and login.role == "faculty"
            and not login.must_change_password
        )

    @rx.event(background=True)
    async def load_courses(self):
        async with self:
            epoch = self._courses_epoch
            self._courses_load_request += 1
            request = self._courses_load_request
            self.courses = []
            self.courses_error = ""
            self.courses_loading = True
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        async with self:
            if epoch != self._courses_epoch:
                return
            if account is None:
                self._clear_access()
            elif not await self._courses_session_matches(
                int(account.id), epoch
            ):
                self._clear_access()
                account = None
        if account is None:
            yield rx.redirect(redirect_to or "/")
            return
        faculty_id = int(account.id)
        courses: list[CourseRow] = []
        error = ""
        denied = False
        try:
            courses = await asyncio.to_thread(list_faculty_courses, faculty_id)
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            denied = True
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Your courses could not be loaded. Please try again."
        current, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        async with self:
            if (
                epoch != self._courses_epoch
                or request != self._courses_load_request
            ):
                return
            allowed = (
                not denied
                and current is not None
                and current.id == faculty_id
                and await self._courses_session_matches(faculty_id, epoch)
            )
            if not allowed:
                self._clear_access()
            else:
                self.courses = courses
                self.courses_error = error
                self.courses_loading = False
        if not allowed:
            yield rx.redirect(redirect_to or "/")

    @rx.event(background=True)
    async def create_course(self, form_data: dict[str, Any]):
        async with self:
            epoch = self._courses_epoch
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        async with self:
            if epoch != self._courses_epoch:
                return
            if account is None:
                self._clear_access()
            elif not await self._courses_session_matches(
                int(account.id), epoch
            ):
                self._clear_access()
                account = None
            elif self.course_creating:
                return
            else:
                self.course_name = str(form_data.get("name", "")).strip()
                self.course_code = str(form_data.get("code", "")).strip()
                self.course_term = str(form_data.get("term", "")).strip()
                name, code, term = (
                    self.course_name,
                    self.course_code,
                    self.course_term,
                )
                self.course_error = ""
                self.course_success = ""
                self.course_creating = True
        if account is None:
            yield rx.redirect(redirect_to or "/")
            return
        faculty_id = int(account.id)
        error = ""
        denied = False
        try:
            await asyncio.to_thread(save_course, faculty_id, name, code, term)
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            denied = True
        except ValueError as e:
            logging.exception(f"Error: {e}")
            error = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Your course could not be saved. Please try again."
        current, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        async with self:
            if epoch != self._courses_epoch:
                return
            allowed = (
                not denied
                and current is not None
                and current.id == faculty_id
                and await self._courses_session_matches(faculty_id, epoch)
            )
            if not allowed:
                self._clear_access()
            else:
                self.course_creating = False
                self.course_error = error
                if not error:
                    self.course_name = ""
                    self.course_code = ""
                    self.course_term = ""
                    self.course_form_revision += 1
                    self.course_success = "Course added successfully."
        if not allowed:
            yield rx.redirect(redirect_to or "/")
        elif not error:
            yield FacultyState.load_courses

    @rx.event
    async def load_faculty(self):
        self._clear_access()
        yield

        account, redirect_to = await check_dashboard_access(self, "faculty")

        if account is None:
            yield rx.redirect(redirect_to)
            return

        self.full_name = str(account.full_name).strip()
        self._authorized = True

        path = self.router.page.path.rstrip("/")
        if path == "/faculty/courses" or path.startswith("/faculty/course/"):
            return

        try:
            self.projects = get_faculty_projects()

            project_id = self.router.page.params.get("id")

            if project_id is not None:
                details = get_faculty_project_details(int(project_id))

                if details is None:
                    self.project_error = "Project not found."
                else:
                    self.selected_project = {
                        key: value
                        for key, value in details.items()
                        if key != "files"
                    }

                    self.files = details.get("files", [])

        except (ValueError, TypeError):
            self.project_error = "Invalid project ID."

        except Exception:
            logging.exception("Failed to load faculty projects")
            self.project_error = "Unable to load project details."

    @rx.event
    async def download_file(self, file_id: str):
        self.project_error = ""

        account, redirect_to = await check_dashboard_access(self, "faculty")

        if account is None:
            self._clear_access()
            return rx.redirect(redirect_to)

        project_id = self.router.page.params.get("id")

        if project_id is None:
            self.project_error = "Project not found."
            return

        try:
            attachment = get_faculty_project_file(
                int(file_id),
                int(project_id),
            )

            if attachment is None:
                self.project_error = "Attachment not found."
                return

            file_bytes = attachment["data"]
            filename = attachment["filename"]

            if not isinstance(file_bytes, bytes):
                file_bytes = bytes(file_bytes)

            if not file_bytes:
                self.project_error = "Attachment is empty."
                return

            return rx.download(
                data=file_bytes,
                filename=filename,
            )

        except (ValueError, TypeError):
            self.project_error = "Invalid attachment."

        except Exception:
            logging.exception("Failed to download faculty attachment")
            self.project_error = "Unable to download attachment."

    async def _perform_course_action(
        self,
        action: str,
        email: str = "",
        student_id: int = 0,
        upload_token: str = "",
    ) -> str:
        async with self:
            epoch = self._courses_epoch
            route_id = str(self.router.page.params.get("id", ""))
            route_path = self.router.page.path
        account, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        async with self:
            if epoch != self._courses_epoch:
                return ""
            if account is None or not await self._courses_session_matches(
                int(account.id), epoch
            ):
                self._clear_access()
                return redirect_to or "/"
            if self.enrollment_busy:
                return ""
            if (
                route_id != str(self.router.page.params.get("id", ""))
                or route_path != self.router.page.path
            ):
                return ""
            filename, data = "", b""
            if action == "bulk":
                filename, data, upload_route, upload_epoch, token = (
                    self._pending_course_upload
                )
                self._pending_course_upload = ("", b"", "", 0, "")
                if (
                    token != upload_token
                    or upload_epoch != epoch
                    or upload_route != route_id
                ):
                    return ""
            self._course_detail_request += 1
            request = self._course_detail_request
            self.course_detail_error = ""
            if action == "load":
                self.course_detail_loading = True
                self.course_detail_ready = False
                self.course_detail = {"name": "", "code": "", "term": ""}
                self.enrolled_students = []
            else:
                self.enrollment_busy = True
                self.enrollment_error = ""
                self.enrollment_message = ""
                self.enrollment_has_summary = False
                self.enrollment_summary = {
                    "added": [],
                    "already_enrolled": [],
                    "no_account": [],
                    "not_student": [],
                    "not_approved": [],
                    "invalid_lines": [],
                }
                if action == "add":
                    self.enrollment_email = email.strip().lower()
        faculty_id = int(account.id)
        detail = None
        summary = None
        error = ""
        detail_error = ""
        message = ""
        denied = False
        try:
            course_id = parse_course_id(route_id)
            if not route_path.startswith("/faculty/course/"):
                raise ValueError("Open a course before changing enrollment.")
            if action == "add":
                summary = await asyncio.to_thread(
                    enroll_course_student, faculty_id, course_id, email
                )
                message = "Enrollment results are shown below. No accounts or account roles were changed."
            elif action == "bulk":
                summary = await asyncio.to_thread(
                    bulk_enroll_course_students,
                    faculty_id,
                    course_id,
                    filename,
                    data,
                )
                message = "Import complete. Review added students and skipped lines below."
            elif action == "remove":
                removed = await asyncio.to_thread(
                    remove_course_student, faculty_id, course_id, student_id
                )
                message = (
                    "Student removed from this course."
                    if removed
                    else "This student is no longer enrolled."
                )
            try:
                detail = await asyncio.to_thread(
                    get_faculty_course_detail, faculty_id, course_id
                )
            except PermissionError:
                raise
            except Exception as e:
                logging.exception(f"Error: {e}")
                detail_error = (
                    str(e)
                    if isinstance(e, ValueError)
                    else "Course details could not be refreshed. Try again."
                )
        except PermissionError as e:
            logging.exception(f"Error: {e}")
            denied = True
        except ValueError as e:
            logging.exception(f"Error: {e}")
            error = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            error = "Enrollment could not be completed. Please try again."
        finally:
            data = b""
        current, redirect_to = await check_dashboard_access(
            self, "faculty", background=True
        )
        async with self:
            if (
                epoch != self._courses_epoch
                or request != self._course_detail_request
            ):
                return ""
            allowed = (
                not denied
                and current is not None
                and current.id == faculty_id
                and await self._courses_session_matches(faculty_id, epoch)
            )
            if not allowed:
                self._clear_access()
                return redirect_to or "/"
            self.course_detail_loading = False
            self.enrollment_busy = False
            if (
                route_id != str(self.router.page.params.get("id", ""))
                or route_path != self.router.page.path
            ):
                self.course_detail = {"name": "", "code": "", "term": ""}
                self.enrolled_students = []
                self.course_detail_ready = False
                return ""
            if detail is not None:
                self.course_detail = {
                    "name": detail["name"],
                    "code": detail["code"],
                    "term": detail["term"],
                }
                self.enrolled_students = detail["students"]
                self.course_detail_ready = True
            if (
                detail_error
                or (action == "load" and error)
                or error == "Course not found or unavailable to your account."
            ):
                self.course_detail = {"name": "", "code": "", "term": ""}
                self.enrolled_students = []
                self.course_detail_ready = False
                self.course_detail_error = detail_error or error
            if action != "load":
                self.enrollment_error = error
                self.enrollment_message = message
                if summary is not None:
                    self.enrollment_summary = summary
                    self.enrollment_has_summary = True
                    if action == "add":
                        self.enrollment_email = ""
        return ""

    @rx.event(background=True)
    async def load_course_detail(self):
        redirect_to = await self._perform_course_action("load")
        async with self:
            if redirect_to:
                yield rx.redirect(redirect_to)

    @rx.event(background=True)
    async def add_course_student(self, form_data: dict[str, Any]):
        redirect_to = await self._perform_course_action(
            "add", email=str(form_data.get("email", ""))
        )
        async with self:
            if redirect_to:
                yield rx.redirect(redirect_to)

    @rx.event(background=True)
    async def remove_enrolled_student(self, student_id: int):
        redirect_to = await self._perform_course_action(
            "remove", student_id=student_id
        )
        async with self:
            if redirect_to:
                yield rx.redirect(redirect_to)

    @rx.event
    async def upload_course_emails(self, files: list[rx.UploadFile]):
        account, redirect_to = await check_dashboard_access(self, "faculty")
        if account is None:
            self._clear_access()
            yield rx.clear_selected_files("faculty_course_enrollment_txt")
            yield rx.redirect(redirect_to or "/")
            return
        if self.enrollment_busy:
            return
        self.enrollment_error = ""
        try:
            if len(files) != 1:
                raise ValueError("Select exactly one UTF-8 .txt file.")
            file = files[0]
            filename = str(file.name or "")
            if Path(filename).suffix.lower() != ".txt":
                raise ValueError("Choose a UTF-8 .txt file.")
            data = await file.read(BULK_EMAIL_MAX_BYTES + 1)
            if len(data) > BULK_EMAIL_MAX_BYTES:
                raise ValueError("The file exceeds 1 MB. Nothing was changed.")
            if not data:
                raise ValueError("The file contains no email addresses.")
            token = uuid4().hex
            self._pending_course_upload = (
                filename,
                data,
                str(self.router.page.params.get("id", "")),
                self._courses_epoch,
                token,
            )
            yield FacultyState.process_course_upload(token)
        except ValueError as e:
            logging.exception(f"Error: {e}")
            self.enrollment_error = str(e)
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.enrollment_error = (
                "The selected file could not be read. Please try again."
            )
        finally:
            for file in files:
                await file.close()
            yield rx.clear_selected_files("faculty_course_enrollment_txt")

    @rx.event(background=True)
    async def process_course_upload(self, token: str):
        redirect_to = await self._perform_course_action(
            "bulk", upload_token=token
        )
        async with self:
            if redirect_to:
                yield rx.redirect(redirect_to)

    @rx.event
    async def logout(self):
        login = await self.get_state(LoginState)
        login._clear_session()
        self._clear_access()
        return rx.redirect("/")
