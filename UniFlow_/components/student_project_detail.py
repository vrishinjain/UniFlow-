import reflex as rx

from UniFlow_.components.dashboard_layout import dashboard_layout, page_header
from UniFlow_.components.student import STUDENT_NAV
from UniFlow_.states.student_project_detail_state import (
    StudentProjectAttachment,
    StudentProjectDetailState,
)


def student_project_attachment(
    file: rx.Var[StudentProjectAttachment],
) -> rx.Component:
    return rx.el.li(
        rx.icon("file-text", class_name="h-5 w-5 shrink-0 text-[#246D67]"),
        rx.el.div(
            rx.el.p(
                file["filename"],
                class_name="break-words text-sm font-medium text-[#172B3D]",
            ),
            rx.el.p(
                "Uploaded: ",
                file["uploaded_at"],
                class_name="mt-1 text-xs text-[#4A5560]",
            ),
            class_name="min-w-0 flex-1",
        ),
        class_name="flex items-start gap-3 py-4",
    )


def student_project_detail_portal() -> rx.Component:
    return dashboard_layout(
        role_label="Student",
        nav=STUDENT_NAV,
        active="/student/projects",
        authorized=StudentProjectDetailState.authorized,
        content=rx.el.div(
            rx.el.a(
                rx.icon("arrow-left", class_name="h-4 w-4"),
                "Back to projects",
                href="/student/projects",
                class_name="mb-6 flex w-fit items-center gap-2 rounded-lg text-sm font-semibold text-[#246D67] hover:text-[#172B3D] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
            ),
            page_header(
                "Student projects", StudentProjectDetailState.project["title"]
            ),
            rx.el.section(
                rx.el.h2(
                    "Description",
                    class_name="text-lg font-semibold text-[#172B3D]",
                ),
                rx.el.p(
                    rx.cond(
                        StudentProjectDetailState.project["description"] != "",
                        StudentProjectDetailState.project["description"],
                        "No description provided.",
                    ),
                    class_name="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[#4A5560]",
                ),
                class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
            ),
            rx.el.section(
                rx.el.h2(
                    "Attachments",
                    class_name="text-lg font-semibold text-[#172B3D]",
                ),
                rx.cond(
                    StudentProjectDetailState.files.length() > 0,
                    rx.el.ul(
                        rx.foreach(
                            StudentProjectDetailState.files,
                            student_project_attachment,
                        ),
                        class_name="mt-2 divide-y divide-[#E2E4DC]",
                    ),
                    rx.el.p(
                        "No attachments were uploaded for this project.",
                        class_name="mt-3 text-sm leading-6 text-[#4A5560]",
                    ),
                ),
                class_name="mt-4 rounded-2xl border border-[#E2E4DC] bg-white p-6",
            ),
            class_name="w-full",
        ),
    )
