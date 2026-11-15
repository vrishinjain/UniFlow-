import reflex as rx
import reflex_enterprise as rxe

from UniFlow_.components.admin import ADMIN_NAV
from UniFlow_.components.dashboard_layout import dashboard_layout, page_header
from UniFlow_.components.faculty import FACULTY_NAV
from UniFlow_.components.student import STUDENT_NAV
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.workspace_state import WorkspaceState
from UniFlow_.workspace_services import (
    WorkspaceMember,
    WorkspaceTicket,
    TICKET_STATUSES,
)
from UniFlow_.components.workspace_ticket_dialogs import ticket_dialogs
from UniFlow_.components.workspace_milestones import (
    milestones_section,
    milestone_filter,
    milestone_dialog,
)


_ACTION = "inline-flex w-fit items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]"


def workspace_member(member: WorkspaceMember) -> rx.Component:
    return rx.el.li(
        rx.icon("user", class_name="h-5 w-5 shrink-0 text-[#246D67]"),
        rx.el.div(
            rx.el.p(
                member["full_name"],
                class_name="break-words text-sm font-semibold text-[#172B3D]",
            ),
            rx.el.p(
                f"{member['role_label']} · #{member['id']}",
                class_name="mt-1 text-xs text-[#667078]",
            ),
            class_name="min-w-0",
        ),
        key=member["id"],
        class_name="flex min-w-0 items-center gap-3 rounded-lg border border-[#E2E4DC] bg-white p-3",
    )


def assignee_option(member: WorkspaceMember) -> rx.Component:
    return rx.el.option(
        member["option_label"], value=member["id"], key=member["id"]
    )


def assignee_filter() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.label(
                "Filter by assignee",
                html_for="workspace-assignee",
                class_name="mb-2 block text-sm font-medium text-[#172B3D]",
            ),
            rx.el.div(
                rx.el.select(
                    rx.el.option("All assignees", value=""),
                    rx.foreach(WorkspaceState.team, assignee_option),
                    id="workspace-assignee",
                    value=WorkspaceState.selected_assignee,
                    on_change=WorkspaceState.set_assignee,
                    class_name="w-full appearance-none rounded-lg border border-[#E2E4DC] bg-white py-2.5 pl-3 pr-10 text-sm text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67]",
                ),
                rx.icon(
                    "chevron-down",
                    class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-[#667078]",
                ),
                class_name="relative w-full",
            ),
            class_name="w-full sm:w-72",
        ),
        rx.cond(
            WorkspaceState.selected_assignee != "",
            rx.el.button(
                rx.icon("x", class_name="h-4 w-4"),
                "Clear filter",
                on_click=WorkspaceState.clear_assignee,
                aria_label="Clear assignee filter",
                type="button",
                class_name="flex w-fit items-center gap-2 rounded-lg border border-[#E2E4DC] bg-white px-3 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
            ),
            rx.fragment(),
        ),
        class_name="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-end",
    )


@rx.memo
def ticket_drag_handle(ticket_id: rx.Var[str]) -> rx.Component:
    return rxe.dnd.draggable(
        rx.el.button(
            rx.icon("grip-vertical", class_name="h-4 w-4 text-[#667078]"),
            type="button",
            aria_label="Drag ticket, or press Enter to pick up for a keyboard move",
            aria_pressed=WorkspaceState.keyboard_ticket_id == ticket_id,
            disabled=WorkspaceState.mutation_pending,
            on_click=WorkspaceState.keyboard_pickup(ticket_id),
            class_name="cursor-grab rounded-md bg-white p-1.5 text-[#667078] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] active:cursor-grabbing disabled:cursor-wait disabled:opacity-50",
        ),
        type="WorkspaceTicket",
        item={"id": f"ticket:{ticket_id}"},
        can_drag=(
            ~WorkspaceState.mutation_pending
            & ~WorkspaceState.dialog_open
            & ~WorkspaceState.delete_open
            & ~WorkspaceState.milestone_dialog_open
        ),
        class_name="w-fit shrink-0",
    )


def ticket_menu(ticket: WorkspaceTicket) -> rx.Component:
    return rx.el.div(
        rx.el.button(
            rx.icon("menu", class_name="h-4 w-4"),
            aria_label=f"Actions for {ticket['title']}",
            aria_expanded=WorkspaceState.menu_ticket_id == ticket["id"],
            on_click=WorkspaceState.toggle_menu(ticket["id"]),
            disabled=WorkspaceState.mutation_pending,
            class_name="rounded-md bg-white p-1.5 text-[#667078] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-50",
        ),
        rx.cond(
            WorkspaceState.menu_ticket_id == ticket["id"],
            rx.el.div(
                rx.el.button(
                    "Edit ticket",
                    on_click=WorkspaceState.open_edit(ticket["id"]),
                    class_name="w-full rounded-md bg-white px-3 py-2 text-left text-sm text-[#172B3D] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67]",
                ),
                rx.el.button(
                    "Delete ticket",
                    on_click=WorkspaceState.open_delete(ticket["id"]),
                    class_name="w-full rounded-md bg-white px-3 py-2 text-left text-sm text-red-700 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-red-700",
                ),
                class_name="absolute right-0 top-9 z-10 flex w-40 flex-col gap-1 rounded-lg border border-[#E2E4DC] bg-white p-1",
            ),
            rx.fragment(),
        ),
        class_name="relative shrink-0",
    )


def ticket_status_control(ticket: WorkspaceTicket) -> rx.Component:
    return rx.el.div(
        rx.el.label(
            "Status",
            html_for=f"ticket-status-{ticket['id']}",
            class_name="mb-1 block text-xs font-medium text-[#667078]",
        ),
        rx.el.div(
            rx.el.select(
                rx.foreach(
                    list(TICKET_STATUSES),
                    lambda status: rx.el.option(status, value=status),
                ),
                id=f"ticket-status-{ticket['id']}",
                value=ticket["status"],
                disabled=WorkspaceState.mutation_pending,
                on_change=lambda status: WorkspaceState.change_status(
                    ticket["id"], status
                ),
                class_name="w-full appearance-none rounded-lg border border-[#E2E4DC] bg-white py-2 pl-3 pr-9 text-sm text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-2.5 h-4 w-4 text-[#667078]",
            ),
            class_name="relative",
        ),
        rx.cond(
            WorkspaceState.move_pending == ticket["id"],
            rx.el.p(
                "Moving…",
                role="status",
                class_name="mt-2 text-xs text-[#246D67]",
            ),
            rx.fragment(),
        ),
        class_name="mt-4",
    )


def workspace_ticket(ticket: WorkspaceTicket) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            ticket_drag_handle(ticket_id=ticket["id"]),
            rx.el.h4(
                ticket["title"],
                class_name="min-w-0 flex-1 break-words text-base font-semibold text-[#172B3D]",
            ),
            ticket_menu(ticket),
            class_name="flex items-start gap-2",
        ),
        rx.el.p(
            rx.cond(
                ticket["description"] != "",
                ticket["description"],
                "No description.",
            ),
            class_name="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[#667078]",
        ),
        rx.el.dl(
            rx.el.div(
                rx.el.dt(
                    "Priority", class_name="text-xs font-medium text-[#667078]"
                ),
                rx.el.dd(
                    ticket["priority"],
                    class_name=rx.cond(
                        ticket["priority"] == "Urgent",
                        "mt-1 w-fit rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700",
                        rx.cond(
                            ticket["priority"] == "High",
                            "mt-1 w-fit rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800",
                            rx.cond(
                                ticket["priority"] == "Medium",
                                "mt-1 w-fit rounded-full bg-[#EAF3EF] px-2.5 py-1 text-xs font-semibold text-[#246D67]",
                                "mt-1 w-fit rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700",
                            ),
                        ),
                    ),
                ),
                class_name="mt-4",
            ),
            rx.el.div(
                rx.el.dt(
                    "Assignee", class_name="text-xs font-medium text-[#667078]"
                ),
                rx.el.dd(
                    ticket["assignee_label"],
                    class_name="mt-1 break-words text-sm text-[#172B3D]",
                ),
                class_name="mt-3",
            ),
            rx.el.div(
                rx.el.dt(
                    "Milestone", class_name="text-xs font-medium text-[#667078]"
                ),
                rx.el.dd(
                    ticket["milestone_label"],
                    class_name="mt-1 break-words text-sm text-[#172B3D]",
                ),
                class_name="mt-3",
            ),
        ),
        ticket_status_control(ticket),
        key=f"ticket:{ticket['id']}",
        aria_busy=WorkspaceState.move_pending == ticket["id"],
        class_name="min-w-0 rounded-xl border border-[#E2E4DC] bg-white p-4",
    )


def workspace_column(
    column: rx.Var[dict[str, str | list[WorkspaceTicket]]],
) -> rx.Component:
    return rxe.dnd.drop_target(
        rx.el.section(
            rx.el.div(
                rx.el.h3(
                    column["status"].to(str),
                    class_name="text-sm font-semibold text-[#172B3D]",
                ),
                rx.el.span(
                    column["tickets"].to(list[WorkspaceTicket]).length(),
                    aria_label="Ticket count",
                    class_name="w-fit rounded-full border border-[#E2E4DC] bg-white px-2.5 py-1 text-xs font-semibold text-[#667078]",
                ),
                class_name="mb-4 flex items-center justify-between gap-3",
            ),
            rx.cond(
                column["tickets"].to(list[WorkspaceTicket]).length() > 0,
                rx.el.div(
                    rx.foreach(
                        column["tickets"].to(list[WorkspaceTicket]),
                        workspace_ticket,
                    ),
                    class_name="flex flex-col gap-3",
                ),
                rx.el.p(
                    WorkspaceState.empty_column_message,
                    class_name="rounded-xl border border-dashed border-[#E2E4DC] bg-white px-4 py-8 text-center text-sm leading-6 text-[#667078]",
                ),
            ),
            rx.cond(
                WorkspaceState.keyboard_ticket_id != "",
                rx.el.button(
                    "Move here",
                    aria_label=f"Move selected ticket to {column['status'].to(str)}",
                    on_click=WorkspaceState.keyboard_drop(
                        column["status"].to(str)
                    ),
                    disabled=WorkspaceState.mutation_pending,
                    class_name="mt-4 w-full rounded-lg bg-[#246D67] px-3 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246D67] disabled:opacity-60",
                ),
                rx.fragment(),
            ),
            class_name="min-h-72 min-w-0 rounded-2xl border border-[#E2E4DC] bg-[#F0F2EC] p-4",
        ),
        accept=["WorkspaceTicket"],
        on_drop=lambda item: WorkspaceState.drop_ticket(
            item, f"column:{column['status'].to(str)}"
        ),
        key=f"column:{column['status'].to(str)}",
        class_name="h-full min-w-0 rounded-2xl focus-within:ring-1 focus-within:ring-[#246D67]",
    )


def workspace_content() -> rx.Component:
    return rx.el.div(
        page_header("Project workspace", WorkspaceState.title),
        rx.el.section(
            rx.el.h2(
                "Project team",
                class_name="text-lg font-semibold text-[#172B3D]",
            ),
            rx.cond(
                WorkspaceState.team.length() > 0,
                rx.el.ul(
                    rx.foreach(WorkspaceState.team, workspace_member),
                    class_name="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3",
                ),
                rx.el.p(
                    "No eligible team members.",
                    class_name="mt-3 text-sm text-[#667078]",
                ),
            ),
            class_name="mb-8 rounded-2xl border border-[#E2E4DC] bg-white p-6",
        ),
        milestones_section(),
        rx.el.div(
            milestone_filter(),
            assignee_filter(),
            class_name="mb-8 flex w-full flex-wrap items-end gap-4",
        ),
        ticket_dialogs(),
        milestone_dialog(),
        rx.el.p(
            WorkspaceState.announcement,
            role="status",
            aria_live="polite",
            class_name="sr-only text-[#172B3D]",
        ),
        rx.cond(
            (WorkspaceState.mutation_error != "")
            & ~WorkspaceState.dialog_open
            & ~WorkspaceState.delete_open
            & ~WorkspaceState.milestone_dialog_open,
            rx.el.p(
                WorkspaceState.mutation_error,
                role="alert",
                class_name="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700",
            ),
            rx.fragment(),
        ),
        rx.el.section(
            rx.el.div(
                rx.el.h2(
                    "Sprint board",
                    class_name="text-xl font-semibold text-[#172B3D]",
                ),
                rx.el.button(
                    rx.icon("plus", class_name="h-4 w-4"),
                    "Create ticket",
                    type="button",
                    on_click=WorkspaceState.open_create,
                    disabled=WorkspaceState.mutation_pending,
                    class_name=_ACTION,
                ),
                class_name="mb-5 flex flex-wrap items-center justify-between gap-4",
            ),
            rx.cond(
                WorkspaceState.tickets.length() == 0,
                rx.el.p(
                    "No tickets have been added to this project yet.",
                    role="status",
                    class_name="mb-5 rounded-xl border border-[#E2E4DC] bg-white p-4 text-sm text-[#667078]",
                ),
                rx.cond(
                    WorkspaceState.visible_tickets.length() == 0,
                    rx.el.p(
                        WorkspaceState.empty_filter_message,
                        role="status",
                        class_name="mb-5 rounded-xl border border-[#E2E4DC] bg-white p-4 text-sm text-[#667078]",
                    ),
                    rx.fragment(),
                ),
            ),
            rx.el.div(
                rx.el.div(
                    rx.foreach(WorkspaceState.board_columns, workspace_column),
                    class_name="grid w-full min-w-[1008px] grid-cols-4 items-stretch gap-4",
                ),
                tab_index=0,
                role="region",
                aria_label="Sprint board, scroll horizontally for all status columns",
                class_name="w-full min-w-0 overflow-x-auto rounded-2xl pb-4 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
            ),
        ),
        class_name="w-full min-w-0",
    )


def workspace_public_surface() -> rx.Component:
    return rx.el.main(
        rx.el.section(
            rx.el.p(
                "UniFlow",
                class_name="mb-8 text-xl font-semibold text-[#172B3D]",
            ),
            rx.cond(
                WorkspaceState.loading,
                rx.el.div(
                    rx.el.h1(
                        "Loading workspace…",
                        class_name="text-2xl font-semibold text-[#172B3D]",
                    ),
                    rx.el.p(
                        "Checking project access.",
                        class_name="mt-3 text-sm text-[#667078]",
                    ),
                    role="status",
                    class_name="animate-pulse rounded-2xl border border-[#E2E4DC] bg-white p-8",
                ),
                rx.el.div(
                    rx.icon(
                        "lock-keyhole", class_name="mb-4 h-7 w-7 text-[#246D67]"
                    ),
                    rx.el.h1(
                        rx.cond(
                            WorkspaceState.error != "",
                            "Workspace unavailable",
                            "Access denied",
                        ),
                        class_name="text-2xl font-semibold text-[#172B3D]",
                    ),
                    rx.el.p(
                        rx.cond(
                            WorkspaceState.error != "",
                            WorkspaceState.error,
                            "You do not have access to this project workspace, or the project does not exist.",
                        ),
                        role="alert",
                        class_name="mt-3 text-sm leading-6 text-[#667078]",
                    ),
                    rx.el.div(
                        rx.el.a(
                            rx.cond(
                                LoginState.signed_in,
                                rx.cond(
                                    LoginState.must_change_password,
                                    "Set your password",
                                    "Back to dashboard",
                                ),
                                "Back to sign in",
                            ),
                            href=rx.cond(
                                LoginState.signed_in,
                                rx.cond(
                                    LoginState.must_change_password,
                                    "/set-password",
                                    rx.match(
                                        LoginState.role,
                                        ("student", "/student"),
                                        ("faculty", "/faculty"),
                                        ("system_admin", "/admin"),
                                        ("sponsor", "/sponsor"),
                                        "/",
                                    ),
                                ),
                                "/",
                            ),
                            class_name=_ACTION,
                        ),
                        rx.el.button(
                            rx.cond(
                                WorkspaceState.error != "",
                                "Try again",
                                "Check access again",
                            ),
                            on_click=WorkspaceState.load_workspace,
                            type="button",
                            class_name="w-fit rounded-lg border border-[#E2E4DC] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
                        ),
                        class_name="mt-6 flex flex-wrap gap-3",
                    ),
                    class_name="rounded-2xl border border-[#E2E4DC] bg-white p-8",
                ),
            ),
            class_name="mx-auto w-full max-w-2xl",
        ),
        class_name="min-h-dvh w-full bg-[#F7F6EF] px-5 py-12 font-['Inter',sans-serif] text-[#172B3D] sm:px-8",
    )


def workspace_portal() -> rx.Component:
    return rx.cond(
        WorkspaceState.authorized
        & LoginState.signed_in
        & ~LoginState.must_change_password
        & (WorkspaceState.selected_project_id == rx.State.project_id)
        & ~WorkspaceState.loading,
        rx.cond(
            WorkspaceState.actor_role == "student",
            dashboard_layout(
                role_label="Student",
                nav=STUDENT_NAV,
                active="/student/my-project",
                authorized=WorkspaceState.authorized,
                content=workspace_content(),
                wide=True,
            ),
            rx.cond(
                WorkspaceState.actor_role == "faculty",
                dashboard_layout(
                    role_label="Faculty",
                    nav=FACULTY_NAV,
                    active="",
                    authorized=WorkspaceState.authorized,
                    content=workspace_content(),
                ),
                dashboard_layout(
                    role_label="System admin",
                    nav=ADMIN_NAV,
                    active="",
                    authorized=WorkspaceState.authorized,
                    content=workspace_content(),
                ),
            ),
        ),
        workspace_public_surface(),
    )
