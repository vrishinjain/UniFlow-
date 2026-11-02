import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
    page_header,
)
from UniFlow_.project_services import SharedStudentProject, StudentProjectFile
from UniFlow_.states.student_state import (
    StudentState,
    StudentProjectsState,
    StudentProjectDetailState,
)

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
    NavItem("Projects", "folders", "/student/projects"),
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
        rx.el.div(
            rx.el.a(
                rx.icon("folders", class_name="h-4 w-4"),
                "Projects",
                href="/student/projects",
                class_name="flex w-fit items-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-3.5 py-2 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
            ),
            class_name="mb-6 flex justify-end",
        ),
        home_content("Student", STUDENT_NAV[:3], StudentState.full_name),
    )


def student_home() -> rx.Component:
    return _page("/student", student_welcome_card())


def student_project() -> rx.Component:
    # Later sprint.
    return _page("/student/project", coming_soon("Student", STUDENT_NAV[1]))


def student_browse() -> rx.Component:
    # Later sprint.
    return _page("/student/browse", coming_soon("Student", STUDENT_NAV[2]))


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


# (page function, route, browser tab title). UniFlow_.py registers each one
# with StudentState's on_load check, so every page is protected the same way.
STUDENT_PAGES = [
    (student_home, "/student", "Student Dashboard"),
    (student_project, "/student/project", "My project"),
    (student_browse, "/student/browse", "Browse projects"),
]
