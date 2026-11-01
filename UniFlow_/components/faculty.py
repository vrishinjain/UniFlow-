import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
    page_header,
)
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.courses_services import CourseRow
from UniFlow_.components.course_detail import course_detail_content


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
    NavItem(
        "Courses",
        "book-open",
        "/faculty/courses",
        "View and create your courses.",
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
                    rx.foreach(
                        FacultyState.projects,
                        _project_row,
                    )
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
    return _page(
        "/faculty/projects",
        _projects_content(),
    )


# ---------------------------------------------
# T-8: Display each project attachment
# ---------------------------------------------


def _file_row(file: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon("file"),
                rx.text(file["filename"]),
                spacing="2",
                align="center",
            )
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
                on_click=FacultyState.download_file(file["id"].to(str)),
                size="2",
                variant="outline",
            )
        ),
    )


def _attachments_content() -> rx.Component:
    return rx.vstack(
        rx.heading("Attachments", size="4"),
        rx.cond(
            FacultyState.files.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("File Name"),
                        rx.table.column_header_cell("File Size"),
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
            rx.text(
                "No attachments uploaded for this project.",
                color="gray",
            ),
        ),
        spacing="3",
        align="start",
        width="100%",
    )


# ---------------------------------------------
# T-8: Faculty project details page
# ---------------------------------------------


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
            rx.cond(
                FacultyState.selected_project.contains("id"),
                rx.vstack(
                    rx.heading(
                        FacultyState.selected_project["title"],
                        size="5",
                    ),
                    rx.text(
                        "Sponsor: ",
                        FacultyState.selected_project["sponsor_name"],
                    ),
                    rx.text(
                        "Submitted: ",
                        FacultyState.selected_project["created_at"],
                    ),
                    rx.text(
                        "Status: ",
                        FacultyState.selected_project["status"],
                    ),
                    rx.heading(
                        "Description",
                        size="4",
                    ),
                    rx.text(
                        FacultyState.selected_project["description"],
                    ),
                    rx.divider(),
                    _attachments_content(),
                    spacing="4",
                    align="start",
                    width="100%",
                ),
                rx.text("Loading project details..."),
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


def _course_card(course: CourseRow) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon("book-open", class_name="h-5 w-5 shrink-0 text-[#246D67]"),
            rx.el.span(
                course["code"],
                class_name="break-words text-sm font-semibold text-[#246D67]",
            ),
            rx.icon(
                "arrow-up-right",
                class_name="ml-auto h-4 w-4 shrink-0 text-[#667078]",
            ),
            class_name="flex items-center gap-3",
        ),
        rx.el.h2(
            course["name"],
            class_name="mt-4 break-words text-lg font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            course["term"], class_name="mt-2 break-words text-sm text-[#4A5560]"
        ),
        rx.el.p(
            f"Created {course['created_at']}",
            class_name="mt-4 text-xs text-[#667078]",
        ),
        href=f"/faculty/course/{course['id']}",
        key=course["id"],
        class_name="block min-w-0 rounded-2xl border border-[#E2E4DC] bg-white p-6 transition-colors hover:border-[#BFCFC9] hover:bg-[#FBFCF9] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
    )


def _course_form() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Add a course", class_name="text-xl font-semibold text-[#172B3D]"
        ),
        rx.el.form(
            rx.el.fieldset(
                rx.el.div(
                    rx.el.label(
                        "Course name",
                        html_for="course-name",
                        class_name="mb-2 block text-sm font-medium text-[#172B3D]",
                    ),
                    rx.el.input(
                        id="course-name",
                        name="name",
                        required=True,
                        max_length=200,
                        placeholder="Software Engineering",
                        default_value=FacultyState.course_name,
                        key=FacultyState.course_name,
                        class_name="w-full rounded-lg border border-[#BFCFC9] bg-white px-3 py-2.5 text-sm text-[#172B3D] placeholder:text-[#667078] focus-visible:outline-2 focus-visible:outline-[#246D67]",
                    ),
                    class_name="sm:col-span-2",
                ),
                rx.el.div(
                    rx.el.label(
                        "Course code",
                        html_for="course-code",
                        class_name="mb-2 block text-sm font-medium text-[#172B3D]",
                    ),
                    rx.el.input(
                        id="course-code",
                        name="code",
                        required=True,
                        max_length=50,
                        placeholder="CS 410",
                        default_value=FacultyState.course_code,
                        key=FacultyState.course_code,
                        class_name="w-full rounded-lg border border-[#BFCFC9] bg-white px-3 py-2.5 text-sm text-[#172B3D] placeholder:text-[#667078] focus-visible:outline-2 focus-visible:outline-[#246D67]",
                    ),
                ),
                rx.el.div(
                    rx.el.label(
                        "Term",
                        html_for="course-term",
                        class_name="mb-2 block text-sm font-medium text-[#172B3D]",
                    ),
                    rx.el.input(
                        id="course-term",
                        name="term",
                        required=True,
                        max_length=100,
                        placeholder="Fall 2026",
                        default_value=FacultyState.course_term,
                        key=FacultyState.course_term,
                        class_name="w-full rounded-lg border border-[#BFCFC9] bg-white px-3 py-2.5 text-sm text-[#172B3D] placeholder:text-[#667078] focus-visible:outline-2 focus-visible:outline-[#246D67]",
                    ),
                ),
                disabled=FacultyState.course_creating,
                class_name="grid min-w-0 gap-5 sm:grid-cols-2 disabled:opacity-60",
            ),
            rx.cond(
                FacultyState.course_error != "",
                rx.el.p(
                    FacultyState.course_error,
                    role="alert",
                    class_name="mt-4 text-sm text-red-700",
                ),
            ),
            rx.cond(
                FacultyState.course_success != "",
                rx.el.p(
                    FacultyState.course_success,
                    role="status",
                    class_name="mt-4 text-sm text-[#246D67]",
                ),
            ),
            rx.el.button(
                rx.cond(
                    FacultyState.course_creating, "Adding course…", "Add course"
                ),
                type="submit",
                disabled=FacultyState.course_creating,
                class_name="mt-6 inline-flex items-center justify-center rounded-lg bg-[#246D67] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67] disabled:cursor-wait disabled:opacity-60",
            ),
            key=FacultyState.course_form_revision,
            on_submit=FacultyState.create_course,
            class_name="mt-6",
        ),
        class_name="mt-8 rounded-2xl border border-[#E2E4DC] bg-white p-6 sm:p-8",
    )


def faculty_courses() -> rx.Component:
    return _page(
        "/faculty/courses",
        rx.el.div(
            page_header(
                "Faculty dashboard", "Courses", "View and create your courses."
            ),
            rx.cond(
                FacultyState.courses_loading,
                rx.el.p(
                    "Loading your courses…",
                    role="status",
                    class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6 text-sm text-[#667078] animate-pulse",
                ),
                rx.cond(
                    FacultyState.courses_error != "",
                    rx.el.p(
                        FacultyState.courses_error,
                        role="alert",
                        class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6 text-sm text-red-700",
                    ),
                    rx.cond(
                        FacultyState.courses.length() > 0,
                        rx.el.div(
                            rx.foreach(FacultyState.courses, _course_card),
                            class_name="grid w-full gap-4 sm:grid-cols-2",
                        ),
                        rx.el.p(
                            "You have no courses yet. Add your first course below.",
                            class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6 text-sm text-[#667078]",
                        ),
                    ),
                ),
            ),
            _course_form(),
            class_name="w-full min-w-0",
        ),
    )


def faculty_course_details() -> rx.Component:
    return _page("/faculty/courses", course_detail_content())


FACULTY_PAGES = [
    (
        faculty_course_details,
        "/faculty/course/[id]",
        "Course Details",
    ),
    (
        faculty_courses,
        "/faculty/courses",
        "Courses",
    ),
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
