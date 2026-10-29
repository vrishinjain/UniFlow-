import reflex as rx

from UniFlow_.components.dashboard_layout import dashboard_layout, page_header
from UniFlow_.components.student import STUDENT_NAV
from UniFlow_.states.student_projects_state import (
    StudentProject,
    StudentProjectsState,
)


def student_project_card(project: rx.Var[StudentProject]) -> rx.Component:
    return rx.el.a(
        rx.el.h2(
            project["title"],
            class_name="break-words text-lg font-semibold text-[#172B3D] group-hover:text-[#246D67]",
        ),
        rx.el.p(
            project["description"],
            class_name="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[#4A5560]",
        ),
        href="/student/projects/" + project["id"].to(str),
        key=project["id"],
        class_name="group block rounded-2xl border border-[#E2E4DC] bg-white p-6 transition-colors hover:border-[#BFCFC9] hover:bg-[#FBFCF9] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
    )


def student_projects_portal() -> rx.Component:
    return dashboard_layout(
        role_label="Student",
        nav=STUDENT_NAV,
        active="/student/projects",
        authorized=StudentProjectsState.authorized,
        content=rx.el.div(
            rx.cond(
                StudentProjectsState.loading,
                rx.el.p(
                    "Loading projects…",
                    role="status",
                    class_name="py-12 text-center text-sm text-[#4A5560]",
                ),
                rx.cond(
                    StudentProjectsState.error != "",
                    rx.el.p(
                        StudentProjectsState.error,
                        role="alert",
                        class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6 text-sm text-[#4A5560]",
                    ),
                    rx.cond(
                        StudentProjectsState.projects.length() > 0,
                        rx.el.div(
                            page_header("Student dashboard", "Projects"),
                            rx.el.div(
                                rx.foreach(
                                    StudentProjectsState.projects,
                                    student_project_card,
                                ),
                                class_name="grid w-full gap-4 sm:grid-cols-2",
                            ),
                            class_name="w-full",
                        ),
                        rx.el.p(
                            "No projects have been shared with your courses yet.",
                            class_name="text-sm leading-6 text-[#4A5560]",
                        ),
                    ),
                ),
            ),
        ),
    )
