import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.faculty_state import FacultyState


FACULTY_NAV = [
    NavItem("Home", "house", "/faculty", "Overview of your faculty workspace."),
    NavItem(
        "Submitted projects",
        "folder-open",
        "/faculty/projects",
        "Review projects that sponsors have submitted.",
    ),
    NavItem(
        "My students",
        "users",
        "/faculty/students",
        "See the students you supervise.",
    ),
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
    return _page(
        "/faculty",
        home_content("Faculty", FACULTY_NAV, FacultyState.full_name),
    )


def _project_row(project: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(project["title"]),
        rx.table.cell(project["sponsor_name"]),
        rx.table.cell(project["created_at"]),
        rx.table.cell(project["status"]),
    )


def _projects_content() -> rx.Component:
    return rx.vstack(
        rx.heading("Submitted Projects", size="6"),
        rx.text("Projects submitted by sponsors."),
        rx.cond(
            FacultyState.projects.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Project Title"),
                        rx.table.column_header_cell("Sponsor"),
                        rx.table.column_header_cell("Submitted Date"),
                        rx.table.column_header_cell("Status"),
                    )
                ),
                rx.table.body(
                    rx.foreach(FacultyState.projects, _project_row)
                ),
                width="100%",
            ),
            rx.text("No submitted projects found."),
        ),
        spacing="4",
        align="start",
        width="100%",
    )


def faculty_projects() -> rx.Component:
    return _page("/faculty/projects", _projects_content())


def faculty_students() -> rx.Component:
    return _page(
        "/faculty/students",
        coming_soon("Faculty", FACULTY_NAV[2]),
    )


FACULTY_PAGES = [
    (faculty_home, "/faculty", "Faculty Dashboard"),
    (faculty_projects, "/faculty/projects", "Submitted projects"),
    (faculty_students, "/faculty/students", "My students"),
]
