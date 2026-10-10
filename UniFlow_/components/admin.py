import reflex as rx

from UniFlow_.states.admin_state import AdminState, ApprovedUser, PendingRequest
from UniFlow_.components.bulk_email_import import bulk_email_import


def request_row(request: PendingRequest) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.el.h3(
                request["full_name"],
                class_name="break-words text-base font-semibold text-[#172B3D]",
            ),
            rx.el.p(
                request["email"],
                class_name="mt-1 break-all text-sm text-[#667078]",
            ),
            rx.el.p(
                rx.el.span("◷", custom_attrs={"aria-hidden": "true"}),
                rx.el.time(
                    request["date_label"], date_time=request["date_iso"]
                ),
                class_name="mt-3 flex items-center gap-2 text-xs text-[#737C81]",
            ),
            class_name="min-w-0 flex-1",
        ),
        rx.el.div(
            rx.el.label(
                "Requested role",
                html_for=f"request-role-{request['id']}",
                class_name="mb-2 block text-xs font-medium text-[#667078]",
            ),
            rx.el.div(
                rx.el.select(
                    rx.el.option("Student", value="student"),
                    rx.el.option("Faculty", value="faculty"),
                    rx.el.option("Sponsor", value="sponsor"),
                    rx.el.option("Program admin", value="program_admin"),
                    rx.el.option("System admin", value="system_admin"),
                    id=f"request-role-{request['id']}",
                    value=request["role"],
                    key=f"{request['id']}-{AdminState.revision}",
                    on_change=lambda role: AdminState.change_role(
                        request["id"], role
                    ),
                    disabled=AdminState.loading | ~AdminState.authorized,
                    custom_attrs={
                        "aria-label": f"Account role for {request['full_name']}"
                    },
                    class_name="h-11 w-full appearance-none rounded-lg border border-[#D9DEDC] bg-white pl-3 pr-10 text-sm text-[#172B3D] focus:border-[#28766F] focus:outline-hidden focus:ring-2 focus:ring-[#28766F]/20 disabled:cursor-not-allowed disabled:bg-[#F5F5F1]",
                ),
                rx.el.span(
                    "⌄",
                    custom_attrs={"aria-hidden": "true"},
                    class_name="pointer-events-none absolute right-3 top-2.5 text-lg leading-6 text-[#667078]",
                ),
                class_name="relative w-full",
            ),
            class_name="w-full sm:w-48 sm:shrink-0",
        ),
        rx.el.div(
            rx.el.button(
                rx.el.span("✓", custom_attrs={"aria-hidden": "true"}),
                "Approve",
                type="button",
                on_click=lambda: AdminState.decide(request["id"], "approve"),
                disabled=AdminState.loading | ~AdminState.authorized,
                custom_attrs={
                    "aria-label": f"Approve request for {request['full_name']}"
                },
                class_name="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-not-allowed disabled:bg-[#548B85]",
            ),
            rx.el.button(
                rx.el.span("×", custom_attrs={"aria-hidden": "true"}),
                "Reject",
                type="button",
                on_click=lambda: AdminState.decide(request["id"], "reject"),
                disabled=AdminState.loading | ~AdminState.authorized,
                custom_attrs={
                    "aria-label": f"Reject request for {request['full_name']}"
                },
                class_name="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg border border-[#D9DEDC] bg-white px-4 text-sm font-semibold text-[#172B3D] transition-colors hover:bg-[#F8F5EF] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-not-allowed disabled:text-[#929A9E]",
            ),
            class_name="flex w-full gap-2 sm:w-auto sm:shrink-0 sm:self-end",
        ),
        key=request["id"],
        class_name="flex flex-col gap-5 border-b border-[#E9EBE6] bg-white p-5 last:border-b-0 sm:flex-row sm:flex-wrap sm:items-center lg:flex-nowrap sm:p-6",
    )


def approved_user_row(user: ApprovedUser) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.el.h3(
                user["full_name"],
                class_name="break-words text-sm font-semibold text-[#172B3D]",
            ),
            rx.el.p(
                user["email"],
                class_name="mt-1 break-all text-sm text-[#667078]",
            ),
            class_name="min-w-0 flex-1",
        ),
        rx.el.span(
            user["role"],
            class_name="w-fit shrink-0 rounded-full bg-[#EAF3EF] px-3 py-1 text-xs font-semibold text-[#246D67]",
        ),
        key=user["id"],
        class_name="flex items-center justify-between gap-4 border-b border-[#E9EBE6] px-5 py-4 last:border-b-0 sm:px-6",
    )


def admin_dashboard() -> rx.Component:
    return rx.el.div(
        rx.el.header(
            rx.el.div(
                rx.el.p(
                    "UniFlow",
                    class_name="text-2xl font-semibold tracking-tight text-[#172B3D]",
                ),
                rx.el.p(
                    "University identity portal",
                    class_name="mt-1 text-sm text-[#667078]",
                ),
            ),
            rx.el.button(
                rx.el.span("↪", custom_attrs={"aria-hidden": "true"}),
                "Sign out",
                type="button",
                on_click=AdminState.logout,
                class_name="flex items-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
            ),
            class_name="flex items-center justify-between gap-4 border-b border-[#E2E4DC] pb-7",
        ),
        rx.el.section(
            rx.el.p(
                "SYSTEM ADMINISTRATION",
                class_name="text-[11px] font-semibold tracking-[0.18em] text-[#28766F]",
            ),
            rx.el.h1(
                "Account requests",
                class_name="mt-3 text-3xl font-semibold tracking-tight text-[#172B3D]",
            ),
            rx.el.p(
                "Review university account requests and confirm each person's role before approving access.",
                class_name="mt-3 text-sm leading-6 text-[#667078]",
            ),
            class_name="py-9 sm:py-12",
        ),
        bulk_email_import(),
        rx.el.section(
            rx.el.div(
                rx.el.div(
                    rx.el.h2(
                        "Pending requests",
                        class_name="text-lg font-semibold text-[#172B3D]",
                    ),
                    rx.el.p(
                        "Role changes are saved immediately. Approvals and rejections are final.",
                        class_name="mt-1 text-xs leading-5 text-[#667078]",
                    ),
                ),
                rx.el.button(
                    rx.el.span("↻", custom_attrs={"aria-hidden": "true"}),
                    "Refresh",
                    type="button",
                    on_click=AdminState.refresh_requests,
                    disabled=AdminState.loading,
                    class_name="flex shrink-0 items-center gap-2 rounded-lg border border-[#D9DEDC] bg-white px-3 py-2 text-sm font-medium text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-wait disabled:text-[#929A9E]",
                ),
                class_name="flex items-center justify-between gap-4 border-b border-[#E9EBE6] p-5 sm:p-6",
            ),
            rx.el.div(
                rx.cond(
                    AdminState.message != "",
                    rx.el.p(
                        AdminState.message,
                        class_name=rx.cond(
                            AdminState.error,
                            "mx-5 my-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:mx-6",
                            "mx-5 my-4 rounded-lg border border-[#CDE1D7] bg-[#EAF3EF] px-4 py-3 text-sm text-[#246D67] sm:mx-6",
                        ),
                    ),
                    rx.fragment(),
                ),
                role="status",
                custom_attrs={"aria-live": "polite", "aria-atomic": "true"},
            ),
            rx.cond(
                AdminState.loading,
                rx.el.div(
                    rx.el.p(
                        "Updating requests…",
                        class_name="text-sm text-[#667078]",
                    ),
                    rx.el.div(
                        class_name="mt-4 h-20 animate-pulse rounded-lg bg-[#F5F5F1]"
                    ),
                    role="status",
                    class_name="p-6",
                ),
                rx.cond(
                    AdminState.requests.length() > 0,
                    rx.el.ul(
                        rx.foreach(AdminState.requests, request_row),
                        class_name="m-0 w-full list-none p-0",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "▤",
                            custom_attrs={"aria-hidden": "true"},
                            class_name="mx-auto block text-3xl leading-8 text-[#28766F]",
                        ),
                        rx.el.h3(
                            rx.cond(
                                AdminState.error,
                                "Requests unavailable",
                                "You're all caught up",
                            ),
                            class_name="mt-4 text-base font-semibold text-[#172B3D]",
                        ),
                        rx.el.p(
                            rx.cond(
                                AdminState.error,
                                "Use Refresh to try loading the list again.",
                                "There are no pending account requests to review.",
                            ),
                            class_name="mt-2 text-sm text-[#667078]",
                        ),
                        class_name="px-6 py-14 text-center",
                    ),
                ),
            ),
            custom_attrs={"aria-busy": AdminState.loading},
            class_name="w-full overflow-hidden rounded-2xl border border-[#E2E4DC] bg-white",
        ),
        rx.el.section(
            rx.el.div(
                rx.el.div(
                    rx.el.h2(
                        "Approved users",
                        class_name="text-lg font-semibold text-[#172B3D]",
                    ),
                    rx.el.p(
                        "Accounts with active access, including system administrators.",
                        class_name="mt-1 text-xs leading-5 text-[#667078]",
                    ),
                ),
                class_name="border-b border-[#E9EBE6] p-5 sm:p-6",
            ),
            rx.cond(
                AdminState.loading,
                rx.el.div(
                    rx.el.p(
                        "Loading approved users…",
                        class_name="text-sm text-[#667078]",
                    ),
                    rx.el.div(
                        class_name="mt-4 h-16 animate-pulse rounded-lg bg-[#F5F5F1]"
                    ),
                    role="status",
                    class_name="p-6",
                ),
                rx.cond(
                    AdminState.approved_error,
                    rx.el.div(
                        rx.el.h3(
                            "Approved users unavailable",
                            class_name="text-base font-semibold text-[#172B3D]",
                        ),
                        rx.el.p(
                            "Use Refresh to try loading the list again.",
                            class_name="mt-2 text-sm text-[#667078]",
                        ),
                        role="status",
                        class_name="px-6 py-10 text-center",
                    ),
                    rx.cond(
                        AdminState.approved_users.length() > 0,
                        rx.el.ul(
                            rx.foreach(
                                AdminState.approved_users, approved_user_row
                            ),
                            class_name="m-0 w-full list-none p-0",
                        ),
                        rx.el.div(
                            rx.el.span(
                                "✓",
                                custom_attrs={"aria-hidden": "true"},
                                class_name="mx-auto block text-2xl leading-7 text-[#28766F]",
                            ),
                            rx.el.h3(
                                "No approved users yet",
                                class_name="mt-3 text-base font-semibold text-[#172B3D]",
                            ),
                            rx.el.p(
                                "Active accounts will appear here.",
                                class_name="mt-2 text-sm text-[#667078]",
                            ),
                            class_name="px-6 py-10 text-center",
                        ),
                    ),
                ),
            ),
            custom_attrs={"aria-busy": AdminState.loading},
            class_name="mt-6 w-full overflow-hidden rounded-2xl border border-[#E2E4DC] bg-white",
        ),
        rx.el.footer(
            "One university. Your connection.",
            class_name="mt-8 text-center text-xs tracking-wide text-[#7B8385]",
        ),
        class_name="mx-auto w-full max-w-6xl",
    )


def admin_portal() -> rx.Component:
    return rx.el.main(
        rx.cond(
            AdminState.authorized,
            admin_dashboard(),
            rx.el.div(
                rx.el.span(
                    "✓",
                    custom_attrs={"aria-hidden": "true"},
                    class_name="mx-auto block text-2xl leading-7 text-[#28766F]",
                ),
                rx.el.p(
                    "Verifying access…",
                    class_name="mt-4 text-sm text-[#667078]",
                ),
                role="status",
                class_name="mx-auto py-24 text-center",
            ),
        ),
        class_name="min-h-dvh w-full bg-[#F7F6EF] px-5 py-7 font-['Inter',sans-serif] text-[#172B3D] sm:px-8 sm:py-9",
    )
