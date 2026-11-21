import reflex as rx

from UniFlow_.components.dashboard_layout import page_header
from UniFlow_.states.workspace_list_state import WorkspaceListState
from UniFlow_.workspace_list_services import WorkspaceListing


def workspace_card(workspace: WorkspaceListing) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.el.h2(
                workspace["title"],
                class_name="break-words text-base font-semibold text-[#172B3D]",
            ),
            rx.el.p(
                workspace["sponsor_name"],
                class_name="mt-1 text-sm text-[#667078]",
            ),
            rx.el.p(
                rx.icon("book-open", class_name="h-4 w-4 shrink-0"),
                workspace["courses"],
                class_name="mt-3 flex items-center gap-2 text-xs text-[#667078]",
            ),
            rx.el.p(
                rx.icon("users", class_name="h-4 w-4 shrink-0"),
                rx.cond(
                    workspace["student_count"] == 1,
                    "1 student",
                    f"{workspace['student_count']} students",
                ),
                class_name="mt-1 flex items-center gap-2 text-xs text-[#667078]",
            ),
            class_name="min-w-0",
        ),
        rx.el.a(
            rx.icon("folder-kanban", class_name="h-4 w-4"),
            "Open workspace",
            href=workspace["href"],
            aria_label=f"Open workspace for {workspace['title']}",
            class_name="inline-flex w-fit shrink-0 items-center gap-2 rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
        ),
        key=workspace["project_id"],
        class_name="flex flex-col gap-4 rounded-2xl border border-[#E2E4DC] bg-white p-6 sm:flex-row sm:items-center sm:justify-between",
    )


def workspace_list_content(eyebrow: str, description: str, retry) -> rx.Component:
    """Shared body for the faculty and admin Project workspaces pages."""
    s = WorkspaceListState
    return rx.el.div(
        page_header(eyebrow, "Project workspaces", description),
        rx.cond(
            s.loading,
            rx.el.p(
                "Loading workspaces…",
                role="status",
                class_name="py-12 text-center text-sm text-[#667078]",
            ),
            rx.cond(
                s.error != "",
                rx.el.div(
                    rx.el.p(s.error, role="alert", class_name="text-sm text-red-700"),
                    rx.el.button(
                        "Try again",
                        type="button",
                        on_click=retry,
                        class_name="mt-4 rounded-lg bg-[#246D67] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
                    ),
                    class_name="rounded-2xl border border-[#E2E4DC] bg-white p-6",
                ),
                rx.cond(
                    s.workspaces.length() == 0,
                    rx.el.p(
                        "No workspaces yet. A workspace appears here once an accepted project has students assigned.",
                        class_name="rounded-2xl border border-[#E2E4DC] bg-white px-6 py-12 text-center text-sm text-[#667078]",
                    ),
                    rx.el.ul(
                        rx.foreach(s.workspaces, workspace_card),
                        class_name="flex flex-col gap-4",
                    ),
                ),
            ),
        ),
    )
