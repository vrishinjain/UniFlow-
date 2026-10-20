
import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.faculty_state import FacultyState


FACULTY_NAV = [
    NavItem(
        "Home",
        "house",
        "/faculty",
        "Overview of your faculty workspace.",
    ),
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
        home_content(
            "Faculty",
            FACULTY_NAV,
            FacultyState.full_name,
        ),
    )


def _project_row(project: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.link(
                project["title"],
                href="/faculty/project/" + project["id"].to(str),
                color="blue",
                text_decoration="underline",
            )
        ),
        rx.table.cell(project["sponsor_name"]),
        rx.table.cell(project["created_at"]),
        rx.table.cell(project["status"]),
    )


def _projects_content() -> rx.Component:
    return rx.vstack(
        rx.heading(
            "Submitted Projects",
            size="6",
        ),
        rx.text(
            "Projects submitted by sponsors."
        ),
        rx.cond(
            FacultyState.projects.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            "Project Title"
                        ),
                        rx.table.column_header_cell(
                            "Sponsor"
                        ),
                        rx.table.column_header_cell(
                            "Submitted Date"
                        ),
                        rx.table.column_header_cell(
                            "Status"
                        ),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        FacultyState.projects,
                        _project_row,
                    )
                ),
                width="100%",
            ),
            rx.text(
                "No submitted projects found."
            ),
        ),
        spacing="4",
        align="start",
        width="100%",
    )


def faculty_projects() -> rx.Component:
    return _page(
        "/faculty/projects",
        _projects_content(),
    )


def _file_row(file: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            file["filename"]
        ),
        rx.table.cell(
            rx.text(
                file["size_bytes"].to(str),
                " bytes",
            )
        ),
        rx.table.cell(
            rx.button(
                "Download",
                size="2",
                variant="outline",
                on_click=lambda: FacultyState.download_file(
                    file["id"].to(str)
                ),
            )
        ),
    )


def _project_details_content() -> rx.Component:
    return rx.vstack(
        rx.link(
            "← Back to Submitted Projects",
            href="/faculty/projects",
        ),
        rx.heading(
            "Project Details",
            size="6",
        ),
        rx.cond(
            FacultyState.project_error != "",
            rx.text(
                FacultyState.project_error,
                color="red",
            ),
            rx.cond(
                FacultyState.selected_project.contains("id"),
                rx.vstack(
                    rx.heading(
                        FacultyState.selected_project["title"],
                        size="5",
                    ),
                    rx.text(
                        "Sponsor: ",
                        FacultyState.selected_project[
                            "sponsor_name"
                        ],
                    ),
                    rx.text(
                        "Submitted: ",
                        FacultyState.selected_project[
                            "created_at"
                        ],
                    ),
                    rx.text(
                        "Status: ",
                        FacultyState.selected_project[
                            "status"
                        ],
                    ),
                    rx.heading(
                        "Description",
                        size="4",
                    ),
                    rx.text(
                        FacultyState.selected_project[
                            "description"
                        ]
                    ),
                    rx.heading(
                        "Attachments",
                        size="4",
                    ),
                    rx.cond(
                        FacultyState.selected_project[
                            "files"
                        ].length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(
                                        "Filename"
                                    ),
                                    rx.table.column_header_cell(
                                        "Size"
                                    ),
                                    rx.table.column_header_cell(
                                        "Action"
                                    ),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    FacultyState.selected_project[
                                        "files"
                                    ],
                                    _file_row,
                                )
                            ),
                            width="100%",
                        ),
                        rx.text(
                            "No attachments uploaded."
                        ),
                    ),
                    spacing="3",
                    align="start",
                    width="100%",
                ),
                rx.text(
                    "Loading project details..."
                ),
            ),
        ),
        spacing="4",
        align="start",
        width="100%",
    )


def faculty_project_details() -> rx.Component:
    return _page(
        "/faculty/projects",
        _project_details_content(),
    )


def faculty_students() -> rx.Component:
    return _page(
        "/faculty/students",
        coming_soon(
            "Faculty",
            FACULTY_NAV[2],
        ),
    )


FACULTY_PAGES = [
    (
        faculty_home,
        "/faculty",
        "Faculty Dashboard",
    ),
    (
        faculty_projects,
        "/faculty/projects",
        "Submitted projects",
    ),
    (
        faculty_project_details,
        "/faculty/project/[id]",
        "Project Details",
    ),
    (
        faculty_students,
        "/faculty/students",
        "My students",
    ),
]
