import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.student_state import StudentState

# Sidebar options for this role. The first item is the dashboard home.
STUDENT_NAV = [
    NavItem("Home", "house", "/student", "Overview of your student workspace."),
    NavItem(
        "My project",
        "folder",
        "/student/project",
        "See the project you are assigned to.",
    ),
    NavItem(
        "Browse projects",
        "search",
        "/student/browse",
        "Explore available capstone and research projects.",
    ),
]


def _page(route: str, content: rx.Component) -> rx.Component:
    return dashboard_layout(
        role_label="Student",
        nav=STUDENT_NAV,
        active=route,
        authorized=StudentState.authorized,
        content=content,
    )


def student_welcome_card() -> rx.Component:
    return rx.el.div(
        home_content("Student", STUDENT_NAV, StudentState.full_name),
        rx.el.a(
            "Projects",
            href="/student/projects",
            class_name="mt-4 flex w-fit items-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-3.5 py-2 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
        ),
    )


def student_home() -> rx.Component:
    return _page("/student", student_welcome_card())


def student_project() -> rx.Component:
    # Later sprint.
    return _page("/student/project", coming_soon("Student", STUDENT_NAV[1]))


def student_browse() -> rx.Component:
    # Later sprint.
    return _page("/student/browse", coming_soon("Student", STUDENT_NAV[2]))


# (page function, route, browser tab title). UniFlow_.py registers each one
# with StudentState's on_load check, so every page is protected the same way.

STUDENT_PAGES = [
    (student_home, "/student", "Student Dashboard"),
    (student_project, "/student/project", "My project"),
    (student_browse, "/student/browse", "Browse projects"),
]
