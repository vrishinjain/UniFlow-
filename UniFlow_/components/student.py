import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    dashboard_layout,
    home_content,
    page_header,
)
from UniFlow_.states.workspace_state import WorkspaceState
from UniFlow_.assignment_services import AssignedProject, Teammate
from UniFlow_.project_services import SharedStudentProject, StudentProjectFile
from UniFlow_.states.student_state import (
    StudentState,
    StudentMyProjectState,
    StudentProjectsState,
    StudentProjectDetailState,
)

# Sidebar options for this role. The first item is the dashboard home.
STUDENT_NAV = [
    NavItem("Home", "house", "/student", "Overview of your student workspace."),
    NavItem(
        "My project",
        "folder-kanban",
        "/student/my-project",
        "Your assigned project, teammates and workspace.",
    ),
    NavItem(
        "Course projects",
        "folder",
        "/student/projects",
        "See projects shared with your courses.",
    ),
    NavItem(
        "Preferences",
        "list-ordered",
        "/student/preferences",
        "Rank the projects you'd like to work on.",
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
    return home_content("Student", STUDENT_NAV, StudentState.full_name)


def student_home() -> rx.Component:
    return _page("/student", student_welcome_card())


def shared_project_card(project: SharedStudentProject) -> rx.Component:
    return rx.el.a(
        rx.icon("folder", class_name="h-6 w-6 text-[#246D67]"),
        rx.el.h2(
            project["title"],
            class_name="mt-4 break-words text-lg font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            project["description"],
            class_name="mt-2 line-clamp-4 whitespace-pre-wrap break-words text-sm leading-6 text-[#667078]",
        ),
        href=f"/student/projects/{project['id']}",
        key=project["id"],
        class_name="block rounded-2xl border border-[#E2E4DC] bg-white p-6 transition-colors hover:border-[#BFCFC9] hover:bg-[#FBFCF9] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
    )


def student_projects_portal() -> rx.Component:
    return _page(
        "/student/projects",
        rx.el.div(
            page_header("Student", "My Projects"),
            rx.cond(
                StudentProjectsState.loading,
                rx.el.p(
                    "Loading projects…",
                    role="status",
                    class_name="py-12 text-center text-sm text-[#667078]",
                ),
                rx.cond(
                    StudentProjectsState.authorized == False,
                    rx.el.p(
                        "Loading projects…",
                        role="status",
                        class_name="py-12 text-center text-sm text-[#667078]",
                    ),
                    rx.cond(
                        StudentProjectsState.error != "",
                        rx.el.div(
                            rx.el.p(
                                StudentProjectsState.error,
                                role="alert",
                                class_name="text-sm text-red-700",
                            ),
                            rx.el.button(
                                "Try again",
                                type="button",
                                on_click=StudentProjectsState.load_student_projects,
                                class_name="mt-4 rounded-lg bg-[#246D67] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
                            ),
                            class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
                        ),
                        rx.cond(
                            StudentProjectsState.projects.length() == 0,
                            rx.el.p(
                                "No projects have been shared with your courses yet.",
                                class_name="rounded-2xl border border-[#E2E4DC] bg-white px-6 py-12 text-center text-sm text-[#667078]",
                            ),
                            rx.el.div(
                                rx.foreach(
                                    StudentProjectsState.projects,
                                    shared_project_card,
                                ),
                                class_name="grid w-full gap-4 sm:grid-cols-2",
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def student_attachment(file: StudentProjectFile) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.icon("file-text", class_name="h-5 w-5 shrink-0 text-[#246D67]"),
            rx.el.div(
                rx.el.p(
                    file["filename"],
                    class_name="break-words text-sm font-semibold text-[#172B3D]",
                ),
                rx.el.p(
                    f"Uploaded {file['uploaded_at']}",
                    class_name="mt-1 text-xs text-[#667078]",
                ),
                class_name="min-w-0",
            ),
            class_name="flex min-w-0 items-center gap-3",
        ),
        rx.el.button(
            rx.icon("download", class_name="h-4 w-4"),
            rx.cond(
                StudentProjectDetailState.downloading_file_id == file["id"],
                "Downloading…",
                "Download",
            ),
            type="button",
            aria_label=f"Download {file['filename']}",
            disabled=StudentProjectDetailState.downloading_file_id != "",
            on_click=lambda: StudentProjectDetailState.download_file(
                file["id"]
            ),
            class_name="flex w-fit shrink-0 items-center gap-2 rounded-lg bg-[#246D67] px-3.5 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-wait disabled:opacity-60",
        ),
        key=file["id"],
        class_name="flex flex-col justify-between gap-4 py-4 sm:flex-row sm:items-center",
    )


def student_project_detail_content() -> rx.Component:
    return rx.el.div(
        page_header("Student project", StudentProjectDetailState.title),
        rx.el.section(
            rx.el.h2(
                "Description", class_name="text-lg font-semibold text-[#172B3D]"
            ),
            rx.el.p(
                StudentProjectDetailState.description,
                class_name="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-[#667078]",
            ),
            class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
        ),
        rx.el.section(
            rx.el.h2(
                "Attachments", class_name="text-lg font-semibold text-[#172B3D]"
            ),
            rx.cond(
                StudentProjectDetailState.files.length() > 0,
                rx.el.ul(
                    rx.foreach(
                        StudentProjectDetailState.files, student_attachment
                    ),
                    class_name="mt-3 divide-y divide-[#E2E4DC]",
                ),
                rx.el.p(
                    "No attachments.", class_name="mt-3 text-sm text-[#667078]"
                ),
            ),
            class_name="mt-6 rounded-2xl border border-[#E2E4DC] bg-white p-6",
        ),
    )


def student_project_detail_portal() -> rx.Component:
    return _page(
        "/student/projects",
        rx.el.div(
            rx.el.a(
                "← Back to Projects",
                href="/student/projects",
                class_name="mb-6 inline-flex rounded-sm text-sm font-semibold text-[#246D67] hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
            ),
            rx.cond(
                StudentProjectDetailState.error != "",
                rx.el.p(
                    StudentProjectDetailState.error,
                    role="alert",
                    class_name="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700",
                ),
                rx.fragment(),
            ),
            rx.cond(
                StudentProjectDetailState.loading,
                rx.el.p(
                    "Loading project…",
                    role="status",
                    class_name="py-12 text-center text-sm text-[#667078]",
                ),
                rx.cond(
                    StudentProjectDetailState.authorized == False,
                    rx.el.p(
                        "Loading project…",
                        role="status",
                        class_name="py-12 text-center text-sm text-[#667078]",
                    ),
                    rx.cond(
                        StudentProjectDetailState.ready,
                        student_project_detail_content(),
                        rx.el.button(
                            "Try again",
                            type="button",
                            on_click=StudentProjectDetailState.load_student_project_detail,
                            class_name="rounded-lg bg-[#246D67] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
                        ),
                    ),
                ),
            ),
        ),
    )


_BUTTON = "flex w-fit items-center gap-2 rounded-lg bg-[#246D67] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]"


def teammate_row(mate: Teammate) -> rx.Component:
    return rx.el.li(
        rx.icon("user", class_name="h-5 w-5 shrink-0 text-[#246D67]"),
        rx.el.div(
            rx.el.p(
                mate["full_name"],
                class_name="break-words text-sm font-semibold text-[#172B3D]",
            ),
            rx.el.p(
                mate["email"],
                class_name="break-words text-xs text-[#667078]",
            ),
            class_name="min-w-0",
        ),
        class_name="flex items-center gap-3 py-3",
    )


def assigned_project_card(project: AssignedProject) -> rx.Component:
    return rx.el.section(
        rx.el.p(
            project["course_label"],
            class_name="text-xs font-semibold uppercase tracking-wide text-[#28766F]",
        ),
        rx.el.h2(
            rx.el.a(
                project["title"],
                href=f"/project/{project['project_id']}/workspace",
                on_click=WorkspaceState.clear_workspace,
                class_name="rounded-sm text-[#172B3D] hover:text-[#246D67] hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
            ),
            class_name="mt-2 break-words text-xl font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            "Sponsor: ",
            project["sponsor_name"],
            class_name="mt-1 text-sm text-[#667078]",
        ),
        rx.el.p(
            project["description"],
            class_name="mt-4 whitespace-pre-wrap break-words text-sm leading-7 text-[#4A5560]",
        ),
        rx.el.h3(
            "Teammates",
            class_name="mt-6 text-base font-semibold text-[#172B3D]",
        ),
        rx.cond(
            project["teammates"].length() > 0,
            rx.el.ul(
                rx.foreach(project["teammates"], teammate_row),
                class_name="mt-2 divide-y divide-[#E2E4DC]",
            ),
            rx.el.p(
                "No teammates assigned yet.",
                class_name="mt-2 text-sm text-[#667078]",
            ),
        ),
        rx.el.a(
            rx.icon("layout-dashboard", class_name="h-4 w-4"),
            "Go to workspace",
            href=f"/project/{project['project_id']}/workspace",
            on_click=WorkspaceState.clear_workspace,
            class_name="mt-6 flex w-fit items-center gap-2 rounded-lg bg-[#246D67] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
        ),
        key=project["project_id"],
        class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
    )


def student_my_project_portal() -> rx.Component:
    return _page(
        "/student/my-project",
        rx.el.div(
            page_header("Student", "My project"),
            rx.cond(
                StudentMyProjectState.loading
                | (StudentMyProjectState.authorized == False),
                rx.el.p(
                    "Loading your project…",
                    role="status",
                    class_name="py-12 text-center text-sm text-[#667078]",
                ),
                rx.cond(
                    StudentMyProjectState.error != "",
                    rx.el.div(
                        rx.el.p(
                            StudentMyProjectState.error,
                            role="alert",
                            class_name="text-sm text-red-700",
                        ),
                        rx.el.button(
                            "Try again",
                            type="button",
                            on_click=StudentMyProjectState.load_my_project,
                            class_name=f"mt-4 {_BUTTON}",
                        ),
                        class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
                    ),
                    rx.cond(
                        StudentMyProjectState.assignments.length() == 0,
                        rx.el.div(
                            rx.el.p(
                                "Not assigned yet",
                                class_name="text-base font-semibold text-[#172B3D]",
                            ),
                            rx.el.p(
                                "Your faculty hasn't assigned you to a project. "
                                "Check back after project assignments are released.",
                                class_name="mt-2 text-sm text-[#667078]",
                            ),
                            class_name="rounded-2xl border border-[#E2E4DC] bg-white px-6 py-12 text-center",
                        ),
                        rx.el.div(
                            rx.foreach(
                                StudentMyProjectState.assignments,
                                assigned_project_card,
                            ),
                            class_name="flex flex-col gap-6",
                        ),
                    ),
                ),
            ),
        ),
    )


# (page function, route, browser tab title). UniFlow_.py registers each one
# with StudentState's on_load check, so every page is protected the same way.
STUDENT_PAGES = [
    (student_home, "/student", "Student Dashboard"),
]
