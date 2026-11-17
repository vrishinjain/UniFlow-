import reflex as rx

from UniFlow_.components.workspace_ticket_dialogs import field
from UniFlow_.states.workspace_state import WorkspaceState
from UniFlow_.workspace_services import WorkspaceMilestone, WorkspaceTicket


_FIELD = "w-full rounded-lg border border-[#E2E4DC] bg-white px-3 py-2.5 text-sm text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60"
_ACTION = "rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246D67] disabled:cursor-wait disabled:opacity-60"
_CANCEL = "rounded-lg border border-[#E2E4DC] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60"


def milestone_cells(milestone: WorkspaceMilestone) -> rx.Component:
    return rx.fragment(
        rx.el.span(
            milestone["title"],
            class_name="break-words font-semibold text-[#172B3D]",
        ),
        rx.el.span(
            milestone["description"],
            class_name="whitespace-pre-wrap break-words text-[#667078]",
        ),
        rx.el.span(
            rx.el.span("Due date: ", class_name="text-[#667078] sm:sr-only"),
            rx.cond(
                milestone["due_date"] != "",
                milestone["due_date"],
                "No due date",
            ),
            class_name="text-[#172B3D]",
        ),
        rx.el.span(
            f"{milestone['done_count']}/{milestone['total_count']}",
            rx.el.span(" tickets done", class_name="text-[#667078] sm:sr-only"),
            aria_label=f"{milestone['done_count']} of {milestone['total_count']} tickets done",
            class_name="text-[#172B3D] sm:text-right",
        ),
    )


def milestone_row(milestone: WorkspaceMilestone) -> rx.Component:
    return rx.el.li(
        rx.cond(
            WorkspaceState.can_edit_milestones
            & (WorkspaceState.actor_role == "faculty"),
            rx.el.button(
                milestone_cells(milestone),
                type="button",
                on_click=WorkspaceState.open_edit_milestone(milestone["id"]),
                disabled=WorkspaceState.mutation_pending,
                aria_label=f"Edit milestone: {milestone['title']}",
                class_name="grid w-full min-w-0 grid-cols-1 gap-3 rounded-lg bg-white px-3 py-4 text-left text-sm hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_8rem_5rem] sm:gap-5",
            ),
            rx.el.div(
                milestone_cells(milestone),
                class_name="grid w-full min-w-0 grid-cols-1 gap-3 bg-white px-3 py-4 text-sm sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_8rem_5rem] sm:gap-5",
            ),
        ),
        key=milestone["id"],
        class_name="min-w-0 border-b border-[#E2E4DC] last:border-b-0",
    )


def milestones_section() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Milestones", class_name="mb-4 text-xl font-semibold text-[#172B3D]"
        ),
        rx.cond(
            WorkspaceState.milestones.length() > 0,
            rx.el.div(
                rx.el.div(
                    rx.el.span("Title"),
                    rx.el.span("Description"),
                    rx.el.span("Due date"),
                    rx.el.span("Done/total", class_name="text-right"),
                    aria_hidden=True,
                    class_name="hidden grid-cols-[minmax(0,1fr)_minmax(0,2fr)_8rem_5rem] gap-5 border-b border-[#E2E4DC] px-3 pb-3 text-xs font-semibold text-[#667078] sm:grid",
                ),
                rx.el.ul(
                    rx.foreach(WorkspaceState.milestones, milestone_row),
                    class_name="w-full min-w-0",
                ),
                class_name="w-full min-w-0",
            ),
            rx.el.p(
                "No milestones have been added to this project yet.",
                role="status",
                class_name="rounded-lg border border-dashed border-[#E2E4DC] bg-white px-4 py-6 text-sm text-[#667078]",
            ),
        ),
        rx.cond(
            WorkspaceState.can_edit_milestones
            & (WorkspaceState.actor_role == "faculty"),
            rx.el.button(
                rx.icon(
                    "circle-plus", class_name="h-5 w-5 shrink-0 text-[#246D67]"
                ),
                "New milestone",
                type="button",
                on_click=WorkspaceState.open_create_milestone,
                disabled=WorkspaceState.mutation_pending,
                class_name="mt-3 flex w-full items-center gap-3 rounded-lg bg-white px-3 py-4 text-left text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60",
            ),
            rx.fragment(),
        ),
        class_name="mb-6 w-full min-w-0 rounded-2xl border border-[#E2E4DC] bg-white p-4 sm:p-6",
    )


def milestone_filter() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.label(
                "Filter by milestone",
                html_for="workspace-milestone",
                class_name="mb-2 block text-sm font-medium text-[#172B3D]",
            ),
            rx.el.div(
                rx.el.select(
                    rx.el.option("All milestones", value=""),
                    rx.foreach(
                        WorkspaceState.milestones,
                        lambda item: rx.el.option(
                            item["title"], value=item["id"], key=item["id"]
                        ),
                    ),
                    id="workspace-milestone",
                    value=WorkspaceState.selected_milestone,
                    on_change=WorkspaceState.set_milestone,
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
            WorkspaceState.selected_milestone != "",
            rx.el.button(
                rx.icon("x", class_name="h-4 w-4"),
                "Clear filter",
                aria_label="Clear milestone filter",
                type="button",
                on_click=WorkspaceState.clear_milestone,
                class_name="flex w-fit items-center gap-2 rounded-lg border border-[#E2E4DC] bg-white px-3 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
            ),
            rx.fragment(),
        ),
        class_name="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-end",
    )


def milestone_ticket_option(ticket: WorkspaceTicket) -> rx.Component:
    return rx.el.li(
        rx.el.button(
            rx.cond(
                WorkspaceState.milestone_ticket_ids.contains(ticket["id"]),
                rx.icon(
                    "square-check", class_name="h-5 w-5 shrink-0 text-[#246D67]"
                ),
                rx.icon("square", class_name="h-5 w-5 shrink-0 text-[#667078]"),
            ),
            rx.el.span(
                rx.el.span(
                    ticket["title"],
                    class_name="block break-words font-medium text-[#172B3D]",
                ),
                rx.el.span(
                    f"Currently: {ticket['milestone_label']}",
                    class_name="mt-1 block break-words text-xs text-[#667078]",
                ),
                class_name="min-w-0",
            ),
            role="checkbox",
            aria_checked=WorkspaceState.milestone_ticket_ids.contains(
                ticket["id"]
            ),
            type="button",
            disabled=WorkspaceState.mutation_pending,
            on_click=WorkspaceState.toggle_milestone_ticket(ticket["id"]),
            class_name="flex w-full items-start gap-3 rounded-lg bg-white p-3 text-left text-sm hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60",
        ),
        key=ticket["id"],
    )


def milestone_form() -> rx.Component:
    return rx.el.form(
        field(
            "Title (required)",
            "milestone-title",
            rx.el.input(
                id="milestone-title",
                name="title",
                required=True,
                max_length=200,
                default_value=WorkspaceState.milestone_title,
                key=WorkspaceState.milestone_title,
                disabled=WorkspaceState.mutation_pending,
                auto_focus=True,
                class_name=_FIELD,
            ),
        ),
        field(
            "Description (required)",
            "milestone-description",
            rx.el.textarea(
                id="milestone-description",
                name="description",
                required=True,
                max_length=20000,
                rows=5,
                default_value=WorkspaceState.milestone_description,
                key=WorkspaceState.milestone_description,
                disabled=WorkspaceState.mutation_pending,
                class_name=_FIELD,
            ),
        ),
        field(
            "Due date (required)",
            "milestone-due-date",
            rx.el.input(
                id="milestone-due-date",
                name="due_date",
                type="date",
                required=True,
                min=WorkspaceState.server_today,
                default_value=WorkspaceState.milestone_due_date,
                key=WorkspaceState.milestone_due_date,
                disabled=WorkspaceState.mutation_pending,
                class_name=_FIELD,
            ),
        ),
        rx.el.div(
            rx.el.p(
                "Linked tickets",
                class_name="mb-2 text-sm font-medium text-[#172B3D]",
            ),
            rx.el.p(
                "Select any project tickets. Selecting a linked ticket moves it here; unchecking removes only this milestone’s existing links.",
                class_name="mb-3 text-xs leading-5 text-[#667078]",
            ),
            rx.cond(
                WorkspaceState.tickets.length() > 0,
                rx.el.details(
                    rx.el.summary(
                        f"Choose tickets · {WorkspaceState.milestone_ticket_ids.length()} selected",
                        class_name="cursor-pointer rounded-lg bg-white px-3 py-2.5 text-sm font-medium text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67]",
                    ),
                    rx.el.ul(
                        rx.foreach(
                            WorkspaceState.tickets, milestone_ticket_option
                        ),
                        aria_label="Project tickets to link to this milestone",
                        class_name="max-h-64 overflow-y-auto border-t border-[#E2E4DC] bg-white p-1",
                    ),
                    class_name="rounded-lg border border-[#E2E4DC] bg-white",
                ),
                rx.el.p(
                    "No tickets in this project to link yet.",
                    role="status",
                    class_name="rounded-lg border border-dashed border-[#E2E4DC] bg-white p-4 text-sm text-[#667078]",
                ),
            ),
        ),
        rx.cond(
            WorkspaceState.mutation_error != "",
            rx.el.p(
                WorkspaceState.mutation_error,
                role="alert",
                id="milestone-form-error",
                class_name="text-sm text-red-700",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.el.button(
                "Cancel",
                type="button",
                on_click=WorkspaceState.close_dialog,
                disabled=WorkspaceState.mutation_pending,
                class_name=_CANCEL,
            ),
            rx.el.button(
                rx.cond(WorkspaceState.saving, "Saving…", "Save milestone"),
                type="submit",
                disabled=WorkspaceState.mutation_pending,
                class_name=_ACTION,
            ),
            class_name="flex justify-end gap-3 pt-2",
        ),
        on_submit=WorkspaceState.submit_milestone,
        reset_on_submit=False,
        aria_busy=WorkspaceState.saving,
        class_name="mt-5 flex flex-col gap-4",
    )


def milestone_dialog() -> rx.Component:
    return rx.radix.primitives.dialog.root(
        rx.radix.primitives.dialog.portal(
            rx.radix.primitives.dialog.overlay(
                class_name="fixed inset-0 z-40 bg-black/40"
            ),
            rx.radix.primitives.dialog.content(
                rx.radix.primitives.dialog.title(
                    rx.cond(
                        WorkspaceState.current_milestone_id == "",
                        "Create milestone",
                        "Edit milestone",
                    ),
                    class_name="text-xl font-semibold text-[#172B3D]",
                ),
                rx.radix.primitives.dialog.description(
                    "Title, description and a due date of today or later are required.",
                    class_name="mt-2 text-sm text-[#667078]",
                ),
                milestone_form(),
                class_name="fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-[#E2E4DC] bg-white p-6 font-['Inter',sans-serif] text-[#172B3D] focus:outline-hidden",
            ),
        ),
        open=WorkspaceState.milestone_dialog_open,
        on_open_change=WorkspaceState.dialog_changed,
    )
