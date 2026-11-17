import reflex as rx

from UniFlow_.states.workspace_state import WorkspaceState
from UniFlow_.workspace_services import WorkspaceMilestone, TICKET_PRIORITIES


_FIELD = "w-full rounded-lg border border-[#E2E4DC] bg-white px-3 py-2.5 text-sm text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60"
_ACTION = "rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246D67] disabled:cursor-wait disabled:opacity-60"
_CANCEL = "rounded-lg border border-[#E2E4DC] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60"


def field(label: str, field_id: str, control: rx.Component) -> rx.Component:
    return rx.el.div(
        rx.el.label(
            label,
            html_for=field_id,
            class_name="mb-2 block text-sm font-medium text-[#172B3D]",
        ),
        control,
    )


def select_field(
    field_id: str, name: str, selected: rx.Var[str], options: rx.Component
) -> rx.Component:
    return rx.el.div(
        rx.el.select(
            options,
            id=field_id,
            name=name,
            default_value=selected,
            key=selected,
            disabled=WorkspaceState.saving,
            class_name="w-full appearance-none rounded-lg border border-[#E2E4DC] bg-white py-2.5 pl-3 pr-10 text-sm text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60",
        ),
        rx.icon(
            "chevron-down",
            class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-[#667078]",
        ),
        class_name="relative",
    )


def milestone_option(milestone: WorkspaceMilestone) -> rx.Component:
    return rx.el.option(
        milestone["title"], value=milestone["id"], key=milestone["id"]
    )


def ticket_form() -> rx.Component:
    return rx.el.form(
        field(
            "Title (required)",
            "ticket-title",
            rx.el.input(
                id="ticket-title",
                name="title",
                required=True,
                max_length=200,
                default_value=WorkspaceState.form_title,
                key=WorkspaceState.form_title,
                disabled=WorkspaceState.saving,
                auto_focus=True,
                class_name=_FIELD,
            ),
        ),
        field(
            "Description (required)",
            "ticket-description",
            rx.el.textarea(
                id="ticket-description",
                name="description",
                required=True,
                max_length=20000,
                rows=5,
                default_value=WorkspaceState.form_description,
                key=WorkspaceState.form_description,
                disabled=WorkspaceState.saving,
                class_name=_FIELD,
            ),
        ),
        field(
            "Priority",
            "ticket-priority",
            select_field(
                "ticket-priority",
                "priority",
                WorkspaceState.form_priority,
                rx.fragment(
                    rx.cond(
                        ~rx.Var.create(list(TICKET_PRIORITIES)).contains(
                            WorkspaceState.form_priority
                        ),
                        rx.el.option(
                            "Choose priority",
                            value=WorkspaceState.form_priority,
                            disabled=True,
                        ),
                        rx.fragment(),
                    ),
                    rx.foreach(
                        list(TICKET_PRIORITIES),
                        lambda priority: rx.el.option(priority, value=priority),
                    ),
                ),
            ),
        ),
        field(
            "Assignee",
            "ticket-assignee",
            select_field(
                "ticket-assignee",
                "assignee",
                WorkspaceState.form_assignee,
                rx.fragment(
                    rx.el.option("Unassigned", value=""),
                    rx.cond(
                        (WorkspaceState.form_assignee != "")
                        & ~WorkspaceState.team.pluck("id").contains(
                            WorkspaceState.form_assignee
                        ),
                        rx.el.option(
                            "Assignee no longer eligible — choose another",
                            value=WorkspaceState.form_assignee,
                            disabled=True,
                        ),
                        rx.fragment(),
                    ),
                    rx.foreach(
                        WorkspaceState.team,
                        lambda member: rx.el.option(
                            member["option_label"],
                            value=member["id"],
                            key=member["id"],
                        ),
                    ),
                ),
            ),
        ),
        field(
            "Milestone",
            "ticket-milestone",
            select_field(
                "ticket-milestone",
                "milestone",
                WorkspaceState.form_milestone,
                rx.fragment(
                    rx.el.option("No milestone", value=""),
                    rx.foreach(WorkspaceState.milestones, milestone_option),
                ),
            ),
        ),
        rx.cond(
            WorkspaceState.mutation_error != "",
            rx.el.p(
                WorkspaceState.mutation_error,
                role="alert",
                id="ticket-form-error",
                class_name="text-sm text-red-700",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.el.button(
                "Cancel",
                type="button",
                on_click=WorkspaceState.close_dialog,
                disabled=WorkspaceState.saving,
                class_name=_CANCEL,
            ),
            rx.el.button(
                rx.cond(WorkspaceState.saving, "Saving…", "Save ticket"),
                type="submit",
                disabled=WorkspaceState.saving,
                class_name=_ACTION,
            ),
            class_name="flex justify-end gap-3 pt-2",
        ),
        on_submit=WorkspaceState.submit_ticket,
        reset_on_submit=False,
        aria_busy=WorkspaceState.saving,
        class_name="mt-5 flex flex-col gap-4",
    )


def ticket_dialogs() -> rx.Component:
    return rx.fragment(
        rx.radix.primitives.dialog.root(
            rx.radix.primitives.dialog.portal(
                rx.radix.primitives.dialog.overlay(
                    class_name="fixed inset-0 z-40 bg-black/40"
                ),
                rx.radix.primitives.dialog.content(
                    rx.radix.primitives.dialog.title(
                        rx.cond(
                            WorkspaceState.current_ticket_id == "",
                            "Create ticket",
                            "Edit ticket",
                        ),
                        class_name="text-xl font-semibold text-[#172B3D]",
                    ),
                    rx.radix.primitives.dialog.description(
                        "Title and description are required.",
                        class_name="mt-2 text-sm text-[#667078]",
                    ),
                    ticket_form(),
                    class_name="fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-[#E2E4DC] bg-white p-6 font-['Inter',sans-serif] text-[#172B3D] focus:outline-hidden",
                ),
            ),
            open=WorkspaceState.dialog_open,
            on_open_change=WorkspaceState.dialog_changed,
        ),
        rx.radix.primitives.dialog.root(
            rx.radix.primitives.dialog.portal(
                rx.radix.primitives.dialog.overlay(
                    class_name="fixed inset-0 z-40 bg-black/40"
                ),
                rx.radix.primitives.dialog.content(
                    rx.radix.primitives.dialog.title(
                        "Are you sure?",
                        class_name="text-xl font-semibold text-[#172B3D]",
                    ),
                    rx.radix.primitives.dialog.description(
                        f"Delete “{WorkspaceState.delete_title}”? This cannot be undone.",
                        class_name="mt-3 break-words text-sm leading-6 text-[#667078]",
                    ),
                    rx.cond(
                        WorkspaceState.mutation_error != "",
                        rx.el.p(
                            WorkspaceState.mutation_error,
                            role="alert",
                            class_name="mt-4 text-sm text-red-700",
                        ),
                        rx.fragment(),
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Cancel",
                            on_click=WorkspaceState.close_dialog,
                            disabled=WorkspaceState.saving,
                            auto_focus=True,
                            class_name=_CANCEL,
                        ),
                        rx.el.button(
                            rx.cond(
                                WorkspaceState.saving,
                                "Deleting…",
                                "Delete ticket",
                            ),
                            on_click=WorkspaceState.confirm_delete,
                            disabled=WorkspaceState.saving,
                            class_name="rounded-lg bg-red-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:opacity-60",
                        ),
                        class_name="mt-6 flex justify-end gap-3",
                    ),
                    class_name="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#E2E4DC] bg-white p-6 font-['Inter',sans-serif] text-[#172B3D] focus:outline-hidden",
                ),
            ),
            open=WorkspaceState.delete_open,
            on_open_change=WorkspaceState.dialog_changed,
        ),
    )
