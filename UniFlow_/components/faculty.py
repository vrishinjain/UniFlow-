import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.project_services import AttachmentMetadata


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


def _project_row(project: rx.Var[dict[str, str]]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.link(
                project["title"],
                href=f"/faculty/project/{project['id']}",
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
        rx.heading("Submitted Projects", size="6"),
        rx.text("Projects submitted by sponsors."),
        rx.cond(
            FacultyState.project_error != "",
            rx.el.p(
                FacultyState.project_error,
                role="alert",
                class_name="text-sm text-red-700",
            ),
        ),
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
                    rx.foreach(
                        FacultyState.projects,
                        _project_row,
                    )
                ),
                width="100%",
            ),
            rx.cond(
                FacultyState.project_error == "",
                rx.el.p(
                    "No submitted projects found.",
                    class_name="text-sm text-slate-600",
                ),
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


def _file_row(file: rx.Var[AttachmentMetadata]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(file["filename"]),
        rx.table.cell(f"{file['size_bytes']} bytes"),
        rx.table.cell(
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Download",
                type="button",
                on_click=FacultyState.download_file(file["id"]),
                aria_label=f"Download {file['filename']}",
                class_name="flex w-fit items-center gap-2 rounded-md border border-teal-600 bg-white px-3 py-1.5 text-sm font-medium text-teal-700 hover:bg-teal-50 focus-visible:ring-2 focus-visible:ring-teal-600",
            )
        ),
        key=file["id"],
    )


def _project_details_content() -> rx.Component:
    return rx.vstack(
        rx.link(
            "← Back to Submitted Projects",
            href="/faculty/projects",
        ),
        rx.heading("Project Details", size="6"),
        rx.cond(
            FacultyState.project_error != "",
            rx.text(
                FacultyState.project_error,
                color="red",
            ),
        ),
        rx.cond(
            FacultyState.selected_project.get("id", "") != "",
            rx.vstack(
                rx.heading(
                    FacultyState.selected_project["title"].to(str),
                    size="5",
                ),
                rx.text(
                    "Sponsor: ",
                    FacultyState.selected_project["sponsor_name"].to(str),
                ),
                rx.text(
                    "Submitted: ",
                    FacultyState.selected_project["created_at"].to(str),
                ),
                rx.text(
                    "Status: ",
                    FacultyState.selected_project["status"].to(str),
                ),
                rx.heading(
                    "Description",
                    size="4",
                ),
                rx.text(FacultyState.selected_project["description"].to(str)),
                rx.heading(
                    "Attachments",
                    size="4",
                ),
                rx.cond(
                    FacultyState.files.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Filename"),
                                rx.table.column_header_cell("Size"),
                                rx.table.column_header_cell("Action"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                FacultyState.files,
                                _file_row,
                            )
                        ),
                        width="100%",
                    ),
                    rx.text("No attachments uploaded."),
                ),
                spacing="3",
                align="start",
                width="100%",
            ),
            rx.cond(
                FacultyState.project_error == "",
                rx.el.p(
                    "Loading project details...",
                    role="status",
                    class_name="text-sm text-slate-600",
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
