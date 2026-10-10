import reflex as rx

from UniFlow_.states.admin_state import AdminState
from UniFlow_.user_services import BulkEmailResult


def import_result_row(result: BulkEmailResult) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.el.p(
                result["email"],
                class_name="break-all text-sm font-semibold text-[#172B3D]",
            ),
            rx.el.span(
                result["outcome"],
                class_name="mt-2 block w-fit rounded-full bg-[#EAF3EF] px-3 py-1 text-xs font-medium text-[#246D67]",
            ),
            class_name="min-w-0 flex-1",
        ),
        rx.cond(
            result["password"] != "",
            rx.el.div(
                rx.el.p(
                    "Temporary password",
                    class_name="mb-1 text-xs text-[#667078]",
                ),
                rx.el.code(
                    result["password"],
                    class_name="block select-all break-all rounded-lg border border-[#D9DEDC] bg-[#F7F6EF] px-3 py-2 font-mono text-sm text-[#172B3D]",
                ),
                class_name="min-w-0 sm:w-80",
            ),
            rx.el.p(
                "Existing password unchanged",
                class_name="text-xs text-[#667078]",
            ),
        ),
        key=result["email"],
        class_name="flex flex-col justify-between gap-3 border-b border-[#E9EBE6] p-5 last:border-b-0 sm:flex-row sm:items-center sm:px-6",
    )


def bulk_email_import() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.icon("mail-plus", class_name="h-5 w-5 text-[#28766F]"),
                rx.el.h2(
                    "Bulk email import",
                    class_name="text-lg font-semibold text-[#172B3D]",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.p(
                "Create active student accounts from email addresses. Pending or rejected accounts are reactivated with their existing name and role; approved accounts stay unchanged.",
                class_name="mt-2 text-sm leading-6 text-[#667078]",
            ),
            rx.upload.root(
                rx.icon("upload", class_name="mx-auto h-6 w-6 text-[#28766F]"),
                rx.el.p(
                    "Click to select a file or drop it here",
                    class_name="mt-3 text-sm font-semibold text-[#246D67]",
                ),
                rx.el.p(
                    "UTF-8 .txt or one-column .csv · up to 1 MB and 500 addresses",
                    class_name="mt-2 text-xs text-[#667078]",
                ),
                id="admin_bulk_emails",
                multiple=False,
                disabled=AdminState.loading | ~AdminState.authorized,
                class_name="mt-5 w-full cursor-pointer rounded-xl border border-dashed border-[#BFCFC9] bg-[#F7F6EF] p-6 text-center transition-colors hover:bg-[#F0F6F3]",
            ),
            rx.el.p(
                "One email per line, with an optional first row of ‘email’. Matching is case-sensitive; surrounding spaces are trimmed. Invalid rows or duplicates reject the entire file before any changes.",
                class_name="mt-3 text-xs leading-5 text-[#667078]",
            ),
            rx.el.div(
                rx.foreach(
                    rx.selected_files("admin_bulk_emails"),
                    lambda filename: rx.el.p(
                        filename, class_name="break-all text-sm text-[#172B3D]"
                    ),
                ),
                class_name="mt-3",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("user-plus", class_name="h-4 w-4"),
                    rx.cond(
                        AdminState.importing, "Importing…", "Import and approve"
                    ),
                    type="button",
                    on_click=AdminState.import_emails(
                        rx.upload_files(upload_id="admin_bulk_emails")
                    ),
                    disabled=AdminState.loading
                    | ~AdminState.authorized
                    | (rx.selected_files("admin_bulk_emails").length() == 0),
                    class_name="flex items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 py-3 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-not-allowed disabled:bg-[#548B85]",
                ),
                rx.el.button(
                    "Clear selection",
                    type="button",
                    on_click=rx.clear_selected_files("admin_bulk_emails"),
                    disabled=AdminState.loading,
                    class_name="rounded-lg border border-[#D9DEDC] bg-white px-4 py-3 text-sm font-medium text-[#246D67] hover:bg-[#F0F6F3] disabled:cursor-not-allowed disabled:text-[#929A9E]",
                ),
                class_name="mt-4 flex flex-wrap gap-3",
            ),
            class_name="p-5 sm:p-6",
        ),
        rx.el.div(
            rx.cond(
                AdminState.import_message != "",
                rx.el.p(
                    AdminState.import_message,
                    class_name=rx.cond(
                        AdminState.import_error,
                        "mx-5 mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:mx-6",
                        "mx-5 mb-5 rounded-lg border border-[#CDE1D7] bg-[#EAF3EF] px-4 py-3 text-sm text-[#246D67] sm:mx-6",
                    ),
                ),
                rx.fragment(),
            ),
            role="status",
            custom_attrs={"aria-live": "polite"},
        ),
        rx.cond(
            AdminState.authorized & (AdminState.bulk_results.length() > 0),
            rx.el.div(
                rx.el.div(
                    rx.el.h3(
                        "Import results · one-time credentials",
                        class_name="text-base font-semibold text-[#172B3D]",
                    ),
                    rx.el.p(
                        "Securely share each temporary password with its account holder now. Passwords disappear on a new import, page reload, sign-out or access loss and cannot be recovered here.",
                        class_name="mt-2 text-xs leading-5 text-[#667078]",
                    ),
                    rx.el.p(
                        f"Already approved: {AdminState.already_approved_count} — no new password issued.",
                        class_name="mt-2 text-xs font-medium text-[#246D67]",
                    ),
                    rx.el.button(
                        "Dismiss credentials",
                        type="button",
                        on_click=AdminState.dismiss_import_results,
                        class_name="mt-3 rounded-lg border border-[#D9DEDC] bg-white px-3 py-2 text-xs font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
                    ),
                    class_name="border-b border-[#E9EBE6] p-5 sm:p-6",
                ),
                rx.el.ul(
                    rx.foreach(AdminState.bulk_results, import_result_row),
                    class_name="m-0 max-h-96 w-full list-none overflow-y-auto p-0",
                ),
                class_name="border-t border-[#E9EBE6] bg-white",
            ),
            rx.fragment(),
        ),
        custom_attrs={"aria-busy": AdminState.importing},
        class_name="mb-6 w-full overflow-hidden rounded-2xl border border-[#E2E4DC] bg-white",
    )
