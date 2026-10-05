import reflex as rx

from UniFlow_.states.admin_state import AdminState, SampleUser


def summary_card(
    label: str, count: rx.Var[int], icon: str, description: str
) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(label, class_name="text-sm font-medium text-slate-600"),
            rx.el.div(
                rx.icon(
                    icon, class_name="h-5 w-5 text-teal-700", aria_hidden=True
                ),
                class_name="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50",
            ),
            class_name="flex items-center justify-between gap-3",
        ),
        rx.el.p(
            count,
            class_name="mt-3 text-4xl font-semibold tracking-tight text-slate-900",
        ),
        rx.el.p(description, class_name="mt-2 text-xs text-slate-500"),
        class_name="w-full rounded-2xl border border-slate-200 bg-white p-5 sm:p-6",
    )


def status_badge(status: rx.Var[str]) -> rx.Component:
    return rx.el.span(
        rx.icon(
            rx.match(
                status,
                ("Pending", "clock-3"),
                ("Active", "circle-check"),
                ("Rejected", "circle-x"),
                "circle-help",
            ),
            class_name="h-3.5 w-3.5",
            aria_hidden=True,
        ),
        status,
        class_name=rx.match(
            status,
            (
                "Pending",
                "inline-flex w-fit items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800",
            ),
            (
                "Active",
                "inline-flex w-fit items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800",
            ),
            (
                "Rejected",
                "inline-flex w-fit items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700",
            ),
            "inline-flex w-fit items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700",
        ),
    )


def user_row(user: SampleUser) -> rx.Component:
    return rx.el.tr(
        rx.el.th(
            rx.el.div(
                rx.el.span(
                    user["initials"],
                    aria_hidden=True,
                    class_name="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600",
                ),
                rx.el.span(
                    user["name"], class_name="font-medium text-slate-900"
                ),
                class_name="flex items-center gap-3",
            ),
            scope="row",
            class_name="px-4 py-4 text-left",
        ),
        rx.el.td(user["email"], class_name="px-4 py-4 text-slate-500"),
        rx.el.td(user["role"], class_name="px-4 py-4 text-slate-600"),
        rx.el.td(status_badge(user["status"]), class_name="px-4 py-4"),
        rx.el.td(
            rx.cond(
                user["status"] == "Pending",
                rx.el.div(
                    rx.el.button(
                        rx.icon(
                            "check", class_name="h-3.5 w-3.5", aria_hidden=True
                        ),
                        "Approve",
                        type="button",
                        aria_label=f"Approve sample user {user['name']}",
                        on_click=AdminState.approve_user(user["id"]),
                        class_name="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700",
                    ),
                    rx.el.button(
                        rx.icon(
                            "x", class_name="h-3.5 w-3.5", aria_hidden=True
                        ),
                        "Reject",
                        type="button",
                        aria_label=f"Reject sample user {user['name']}",
                        on_click=AdminState.reject_user(user["id"]),
                        class_name="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700",
                    ),
                    class_name="flex items-center gap-2",
                ),
                rx.el.span(
                    rx.el.span(
                        "—", aria_hidden=True, class_name="text-slate-400"
                    ),
                    rx.el.span("No actions available", class_name="sr-only"),
                ),
            ),
            class_name="sticky right-0 z-10 bg-white px-4 py-4",
        ),
        key=user["id"],
        class_name="border-b border-slate-100 bg-white text-sm last:border-b-0 even:bg-slate-50/40 hover:bg-slate-50",
    )


def column_header(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(
                icon, class_name="h-3.5 w-3.5 text-slate-400", aria_hidden=True
            ),
            label,
            class_name="flex items-center gap-2",
        ),
        scope="col",
        class_name=rx.cond(
            label == "Actions",
            "sticky right-0 z-20 bg-slate-50 px-4 py-3.5 text-left text-xs font-medium text-slate-500",
            "bg-slate-50 px-4 py-3.5 text-left text-xs font-medium text-slate-500",
        ),
    )


def user_management() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.h2(
                        "User Management",
                        id="user-management-heading",
                        class_name="text-lg font-semibold text-slate-900",
                    ),
                    rx.el.span(
                        f"{AdminState.total_users} sample users",
                        class_name="w-fit rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600",
                    ),
                    class_name="flex flex-wrap items-center gap-3",
                ),
                rx.el.p(
                    "Review university access requests and manage sample user statuses.",
                    class_name="mt-2 text-sm text-slate-500",
                ),
            ),
            rx.el.div(
                rx.icon(
                    "clock-3",
                    class_name="h-4 w-4 text-teal-700",
                    aria_hidden=True,
                ),
                rx.cond(
                    AdminState.pending_users > 0,
                    f"{AdminState.pending_users} awaiting review",
                    "All requests reviewed",
                ),
                class_name="flex items-center gap-2 text-xs font-medium text-slate-600",
            ),
            class_name="flex flex-col justify-between gap-4 border-b border-slate-200 p-6 sm:flex-row sm:items-center",
        ),
        rx.el.p(
            "Swipe or scroll horizontally to see all columns.",
            id="table-scroll-hint",
            class_name="px-6 pt-4 text-xs text-slate-500 lg:hidden",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.caption(
                    "Sample university users. Approve or reject pending requests; changes are in memory only.",
                    class_name="sr-only",
                ),
                rx.el.thead(
                    rx.el.tr(
                        column_header("Name", "user-round"),
                        column_header("Email", "mail"),
                        column_header("Role", "graduation-cap"),
                        column_header("Status", "circle-dot"),
                        column_header("Actions", "list-checks"),
                    ),
                    class_name="border-b border-slate-200 bg-slate-50",
                ),
                rx.el.tbody(
                    rx.cond(
                        AdminState.total_users > 0,
                        rx.foreach(AdminState.users, user_row),
                        rx.el.tr(
                            rx.el.td(
                                rx.icon(
                                    "users",
                                    class_name="mx-auto mb-3 h-7 w-7 text-slate-400",
                                    aria_hidden=True,
                                ),
                                rx.el.p(
                                    "No sample users to display",
                                    class_name="font-medium text-slate-700",
                                ),
                                rx.el.p(
                                    "User counts are zero when the list is empty.",
                                    class_name="mt-1 text-sm text-slate-500",
                                ),
                                col_span=5,
                                class_name="px-4 py-14 text-center",
                            ),
                        ),
                    ),
                ),
                class_name="table-auto w-full min-w-[880px] whitespace-nowrap",
            ),
            role="region",
            aria_label="Sample user management table",
            aria_describedby="table-scroll-hint",
            tab_index=0,
            class_name="w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-teal-700",
        ),
        rx.el.div(
            rx.el.span(
                f"Showing all {AdminState.total_users} sample users",
                class_name="text-xs text-slate-500",
            ),
            rx.el.span(
                "Pending requests can be approved or rejected.",
                class_name="text-xs text-slate-500",
            ),
            class_name="flex flex-wrap justify-between gap-2 border-t border-slate-200 bg-white px-6 py-4",
        ),
        aria_labelledby="user-management-heading",
        class_name="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white",
    )


def admin_dashboard() -> rx.Component:
    return rx.el.div(
        rx.el.a(
            "Skip to dashboard",
            href="#admin-main",
            class_name="sr-only z-50 rounded-lg bg-white px-4 py-2 text-teal-800 focus:not-sr-only focus:absolute focus:left-4 focus:top-4",
        ),
        rx.el.header(
            rx.el.div(
                rx.el.a(
                    rx.el.div(
                        rx.icon(
                            "graduation-cap",
                            class_name="h-6 w-6 text-white",
                            aria_hidden=True,
                        ),
                        class_name="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700",
                    ),
                    rx.el.span(
                        "UniFlow",
                        class_name="text-xl font-semibold tracking-tight text-slate-900",
                    ),
                    href="/",
                    aria_label="UniFlow home",
                    class_name="flex items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700",
                ),
                rx.el.div(
                    rx.icon(
                        "shield-check",
                        class_name="h-4 w-4 text-teal-700",
                        aria_hidden=True,
                    ),
                    rx.el.span(
                        "Administration",
                        class_name="text-sm font-medium text-slate-600",
                    ),
                    class_name="flex items-center gap-2",
                ),
                class_name="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-4 sm:px-8 lg:px-10",
            ),
            class_name="border-b border-slate-200 bg-white",
        ),
        rx.el.main(
            rx.el.p(
                "UNIVERSITY OPERATIONS",
                class_name="mb-3 text-xs font-semibold tracking-[0.16em] text-teal-700",
            ),
            rx.el.h1(
                "Admin Dashboard",
                class_name="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl",
            ),
            rx.el.p(
                "Welcome back. Here's an overview of your university community and access requests.",
                class_name="mt-3 text-sm leading-6 text-slate-500 sm:text-base",
            ),
            rx.el.div(
                rx.icon(
                    "info",
                    class_name="mt-0.5 h-4 w-4 shrink-0 text-teal-700",
                    aria_hidden=True,
                ),
                rx.el.p(
                    rx.el.span(
                        "Sample workspace. ",
                        class_name="font-semibold text-slate-700",
                    ),
                    "All users below are fictional. Approvals and rejections update this session's in-memory sample only; nothing is saved to a database.",
                    class_name="text-xs leading-5 text-slate-600 sm:text-sm",
                ),
                class_name="mt-6 flex items-start gap-3 rounded-xl border border-teal-100 bg-teal-50/60 px-4 py-3",
            ),
            rx.el.section(
                summary_card(
                    "Total Users",
                    AdminState.total_users,
                    "users",
                    "All users in the sample directory",
                ),
                summary_card(
                    "Pending Users",
                    AdminState.pending_users,
                    "clock-3",
                    "Access requests awaiting review",
                ),
                summary_card(
                    "Active Users",
                    AdminState.active_users,
                    "user-check",
                    "Approved university members",
                ),
                summary_card(
                    "Rejected Users",
                    AdminState.rejected_users,
                    "user-x",
                    "Requests that were not approved",
                ),
                aria_label="Sample user summary",
                class_name="mt-7 grid w-full grid-cols-1 gap-4 min-[420px]:grid-cols-2 lg:grid-cols-4",
            ),
            user_management(),
            rx.el.p(
                AdminState.announcement,
                role="status",
                aria_live="polite",
                aria_atomic=True,
                class_name="mt-4 min-h-5 text-sm text-teal-800",
            ),
            rx.el.footer(
                rx.icon(
                    "graduation-cap",
                    class_name="h-4 w-4 text-slate-400",
                    aria_hidden=True,
                ),
                rx.el.p(
                    "UniFlow · University administration · Sample workspace",
                    class_name="text-xs text-slate-400",
                ),
                class_name="mt-8 flex items-center justify-center gap-2 pb-4",
            ),
            id="admin-main",
            class_name="mx-auto w-full max-w-7xl px-5 pt-9 pb-6 sm:px-8 lg:px-10 lg:pt-12",
        ),
        class_name="min-h-dvh w-full bg-slate-50 font-['Inter',system-ui,sans-serif] text-slate-900",
    )
