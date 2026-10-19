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
    NavItem("My project", "folder", "/student/project", "See the project you are assigned to."),
    NavItem("Browse projects", "search", "/student/browse", "Explore available capstone and research projects."),
]


def _page(route: str, content: rx.Component) -> rx.Component:
    return dashboard_layout(
        role_label="Student",
        nav=STUDENT_NAV,
        active=route,
        authorized=StudentState.authorized,
        content=content,
    )


def student_home() -> rx.Component:
    return _page("/student", home_content("Student", STUDENT_NAV, StudentState.full_name))


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
