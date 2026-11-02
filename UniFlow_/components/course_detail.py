import reflex as rx

from UniFlow_.courses_services import EnrolledStudent
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.user_services import BULK_EMAIL_MAX_BYTES, CourseEmailEntry


_BUTTON = "inline-flex items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67] disabled:cursor-not-allowed disabled:opacity-60"
_OUTLINE = "inline-flex items-center justify-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67] disabled:cursor-not-allowed disabled:opacity-60"
_CARD = "mt-6 w-full min-w-0 rounded-2xl border border-[#E2E4DC] bg-white p-6 sm:p-8"
_UPLOAD_ID = "faculty_course_enrollment_txt"


def _student_row(student: EnrolledStudent) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            student["full_name"],
            class_name="px-4 py-4 text-sm font-medium text-[#172B3D]",
        ),
        rx.el.td(
            student["email"],
            class_name="break-all px-4 py-4 text-sm text-[#4A5560]",
        ),
        rx.el.td(
            rx.el.button(
                "Remove",
                type="button",
                aria_label=f"Remove {student['full_name']} ({student['email']}) from this course",
                on_click=FacultyState.remove_enrolled_student(student["id"]),
                disabled=FacultyState.enrollment_busy,
                class_name=_OUTLINE,
            ),
            class_name="px-4 py-4 text-right",
        ),
        key=student["id"],
        class_name="border-t border-[#E2E4DC] bg-white even:bg-[#F7F6EF] hover:bg-[#F0F6F3]",
    )


def _enrolled_students() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            f"Enrolled students ({FacultyState.enrolled_students.length()})",
            class_name="text-xl font-semibold text-[#172B3D]",
        ),
        rx.cond(
            FacultyState.enrolled_students.length() > 0,
            rx.el.div(
                rx.el.div(
                    rx.el.table(
                        rx.el.caption(
                            "Students enrolled in this course",
                            class_name="sr-only",
                        ),
                        rx.el.thead(
                            rx.el.tr(
                                rx.el.th(
                                    "Name",
                                    scope="col",
                                    class_name="px-4 py-3 text-left",
                                ),
                                rx.el.th(
                                    "Email",
                                    scope="col",
                                    class_name="px-4 py-3 text-left",
                                ),
                                rx.el.th(
                                    "Action",
                                    scope="col",
                                    class_name="px-4 py-3 text-right",
                                ),
                            ),
                            class_name="bg-[#F7F6EF] text-xs font-semibold text-[#4A5560]",
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                FacultyState.enrolled_students, _student_row
                            )
                        ),
                        class_name="table-auto w-full min-w-[520px]",
                    ),
                    class_name="w-full overflow-x-auto",
                ),
                class_name="mt-5 w-full overflow-hidden rounded-xl border border-[#E2E4DC]",
            ),
            rx.el.p(
                "No students are enrolled yet. Add a student by email below.",
                class_name="mt-4 text-sm text-[#667078]",
            ),
        ),
        class_name=_CARD,
    )


def _single_enrollment() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Add student by email",
            class_name="text-xl font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            "Only approved (active) student accounts can be enrolled. Account roles and status stay unchanged.",
            class_name="mt-2 text-sm leading-6 text-[#667078]",
        ),
        rx.el.form(
            rx.el.label(
                "Student email",
                html_for="enrollment-email",
                class_name="mb-2 block text-sm font-medium text-[#172B3D]",
            ),
            rx.el.div(
                rx.el.input(
                    id="enrollment-email",
                    name="email",
                    type="email",
                    required=True,
                    max_length=254,
                    placeholder="student@example.edu",
                    default_value=FacultyState.enrollment_email,
                    key=FacultyState.enrollment_email,
                    disabled=FacultyState.enrollment_busy,
                    class_name="w-full min-w-0 flex-1 rounded-lg border border-[#BFCFC9] bg-white px-3 py-2.5 text-sm text-[#172B3D] placeholder:text-[#667078] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60",
                ),
                rx.el.button(
                    "Add student",
                    type="submit",
                    disabled=FacultyState.enrollment_busy,
                    class_name=_BUTTON,
                ),
                class_name="flex flex-col gap-3 sm:flex-row",
            ),
            on_submit=FacultyState.add_course_student,
            class_name="mt-5",
        ),
        class_name=_CARD,
    )


def _bulk_enrollment() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Bulk enroll students",
            class_name="text-xl font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            "Upload one UTF-8 .txt file, up to 1 MB and 500 nonblank address lines. Use one email per line; an optional first ‘email’ header is accepted.",
            class_name="mt-2 text-sm leading-6 text-[#667078]",
        ),
        rx.upload.root(
            rx.icon("upload", class_name="mx-auto h-6 w-6 text-[#246D67]"),
            rx.el.button(
                "Select .txt file",
                type="button",
                disabled=FacultyState.enrollment_busy,
                class_name="mt-3 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-[#246D67] focus-visible:outline-2 focus-visible:outline-[#246D67]",
            ),
            rx.el.p(
                "Or drop your file here",
                class_name="mt-2 text-xs text-[#667078]",
            ),
            id=_UPLOAD_ID,
            accept={"text/plain": [".txt"]},
            max_files=1,
            max_size=BULK_EMAIL_MAX_BYTES,
            multiple=False,
            disabled=FacultyState.enrollment_busy,
            class_name="mt-5 w-full cursor-pointer rounded-xl border border-dashed border-[#BFCFC9] bg-[#F7F6EF] p-6 text-center hover:bg-[#F0F6F3]",
        ),
        rx.el.p(
            "Blank lines are skipped, emails are lowercased, and repeated emails are enrolled only once. Invalid lines are reported without rejecting valid addresses.",
            class_name="mt-3 text-xs leading-5 text-[#667078]",
        ),
        rx.el.div(
            rx.foreach(
                rx.selected_files(_UPLOAD_ID),
                lambda filename: rx.el.p(
                    filename, class_name="break-all text-sm text-[#172B3D]"
                ),
            ),
            class_name="mt-3",
        ),
        rx.el.div(
            rx.el.button(
                "Upload and enroll",
                type="button",
                on_click=FacultyState.upload_course_emails(
                    rx.upload_files(upload_id=_UPLOAD_ID)
                ),
                disabled=FacultyState.enrollment_busy
                | (rx.selected_files(_UPLOAD_ID).length() != 1),
                class_name=_BUTTON,
            ),
            rx.el.button(
                "Clear selection",
                type="button",
                on_click=rx.clear_selected_files(_UPLOAD_ID),
                disabled=FacultyState.enrollment_busy,
                class_name=_OUTLINE,
            ),
            class_name="mt-4 flex flex-wrap gap-3",
        ),
        class_name=_CARD,
    )


def _summary_entry(entry: CourseEmailEntry) -> rx.Component:
    return rx.el.li(
        rx.el.span(
            f"Line {entry['line']}: {entry['email']}",
            class_name="break-all text-sm text-[#172B3D]",
        ),
        rx.cond(
            entry["reason"] != "",
            rx.el.p(entry["reason"], class_name="mt-1 text-xs text-[#667078]"),
        ),
        class_name="py-2",
    )


def _summary_group(label: str, entries: list[CourseEmailEntry]) -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            f"{label} ({entries.length()})",
            class_name="text-sm font-semibold text-[#172B3D]",
        ),
        rx.cond(
            entries.length() > 0,
            rx.el.ul(
                rx.foreach(entries, _summary_entry),
                class_name="mt-2 max-h-60 list-none overflow-y-auto p-0",
            ),
            rx.el.p("None", class_name="mt-2 text-xs text-[#667078]"),
        ),
        class_name="min-w-0 rounded-xl border border-[#E2E4DC] bg-white p-4",
    )


def _enrollment_feedback() -> rx.Component:
    return rx.el.div(
        rx.cond(
            FacultyState.enrollment_busy,
            rx.el.p(
                "Updating enrollment…",
                role="status",
                class_name="mt-6 animate-pulse text-sm text-[#246D67]",
            ),
        ),
        rx.cond(
            FacultyState.enrollment_error != "",
            rx.el.p(
                FacultyState.enrollment_error,
                role="alert",
                class_name="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700",
            ),
        ),
        rx.cond(
            FacultyState.enrollment_message != "",
            rx.el.p(
                FacultyState.enrollment_message,
                role="status",
                class_name="mt-6 text-sm text-[#246D67]",
            ),
        ),
        rx.cond(
            FacultyState.enrollment_has_summary,
            rx.el.section(
                rx.el.h2(
                    "Enrollment results",
                    class_name="text-xl font-semibold text-[#172B3D]",
                ),
                rx.el.div(
                    _summary_group(
                        "Added", FacultyState.enrollment_summary["added"]
                    ),
                    _summary_group(
                        "Already enrolled",
                        FacultyState.enrollment_summary["already_enrolled"],
                    ),
                    _summary_group(
                        "No account",
                        FacultyState.enrollment_summary["no_account"],
                    ),
                    _summary_group(
                        "Not a student / ambiguous account",
                        FacultyState.enrollment_summary["not_student"],
                    ),
                    _summary_group(
                        "Not approved",
                        FacultyState.enrollment_summary["not_approved"],
                    ),
                    _summary_group(
                        "Invalid lines",
                        FacultyState.enrollment_summary["invalid_lines"],
                    ),
                    class_name="mt-5 grid w-full gap-4 sm:grid-cols-2",
                ),
                class_name=_CARD,
            ),
        ),
        class_name="w-full",
    )


def course_detail_content() -> rx.Component:
    return rx.el.div(
        rx.el.a(
            rx.icon("arrow-left", class_name="h-4 w-4"),
            "Back to Courses",
            href="/faculty/courses",
            class_name="mb-6 inline-flex items-center gap-2 rounded-lg text-sm font-semibold text-[#246D67] hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
        ),
        rx.cond(
            FacultyState.course_detail_loading,
            rx.el.p(
                "Loading course details…",
                role="status",
                class_name="animate-pulse rounded-2xl border border-[#E2E4DC] bg-white p-6 text-sm text-[#667078]",
            ),
            rx.cond(
                FacultyState.course_detail_error != "",
                rx.el.div(
                    rx.el.p(
                        FacultyState.course_detail_error,
                        role="alert",
                        class_name="mb-4 text-sm text-red-700",
                    ),
                    rx.el.button(
                        "Retry loading course",
                        type="button",
                        on_click=FacultyState.load_course_detail,
                        disabled=FacultyState.enrollment_busy,
                        class_name=_OUTLINE,
                    ),
                    class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
                ),
                rx.cond(
                    FacultyState.course_detail_ready,
                    rx.el.div(
                        rx.el.h1(
                            FacultyState.course_detail["name"],
                            class_name="break-words text-3xl font-semibold tracking-tight text-[#172B3D]",
                        ),
                        rx.el.p(
                            f"{FacultyState.course_detail['code']} · {FacultyState.course_detail['term']}",
                            class_name="mt-3 break-words text-sm font-medium text-[#4A5560]",
                        ),
                        _enrolled_students(),
                        _single_enrollment(),
                        _bulk_enrollment(),
                        class_name="w-full min-w-0",
                    ),
                    rx.el.p(
                        "Waiting for course details…",
                        role="status",
                        class_name="text-sm text-[#667078]",
                    ),
                ),
            ),
        ),
        _enrollment_feedback(),
        custom_attrs={
            "aria-busy": FacultyState.enrollment_busy
            | FacultyState.course_detail_loading
        },
        class_name="w-full min-w-0",
    )
