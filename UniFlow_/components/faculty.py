import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.faculty_state import FacultyState

# Sidebar options for this role. The first item is the dashboard home.
FACULTY_NAV = [
    NavItem("Home", "house", "/faculty", "Overview of your faculty workspace."),
    NavItem("Submitted projects", "folder-open", "/faculty/projects", "Review projects that sponsors have submitted."),
    NavItem("My students", "users", "/faculty/students", "See the students you supervise."),
]


def _page(route: str, content: rx.Component) -> rx.Component:
    return dashboard_layout(
        role_label="Faculty",
        nav=FACULTY_NAV,
        active=route,
        authorized=FacultyState.authorized,
        content=content,
    )


def faculty_home() -> rx.Component:
    return _page("/faculty", home_content("Faculty", FACULTY_NAV, FacultyState.full_name))


def faculty_projects() -> rx.Component:
    # T-7 / T-8 (Keerthi): replace coming_soon with the project list.
    return _page("/faculty/projects", coming_soon("Faculty", FACULTY_NAV[1]))


def faculty_students() -> rx.Component:
    # Later sprint.
    return _page("/faculty/students", coming_soon("Faculty", FACULTY_NAV[2]))


# (page function, route, browser tab title). UniFlow_.py registers each one
# with FacultyState's on_load check, so every page is protected the same way.
FACULTY_PAGES = [
    (faculty_home, "/faculty", "Faculty Dashboard"),
    (faculty_projects, "/faculty/projects", "Submitted projects"),
    (faculty_students, "/faculty/students", "My students"),
]
