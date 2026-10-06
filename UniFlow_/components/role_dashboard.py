import reflex as rx

from UniFlow_.states.role_dashboard_state import RoleDashboardState


def role_dashboard(role: str, title: str) -> rx.Component:
    return rx.el.main(
        rx.el.div(
            rx.el.header(
                rx.el.p(
                    "UniFlow",
                    class_name="text-2xl font-semibold tracking-tight text-[#172B3D]",
                ),
                rx.el.p(
                    "University identity portal",
                    class_name="mt-1 text-sm text-[#667078]",
                ),
                class_name="mb-9 text-center",
            ),
            rx.cond(
                rx.State.is_hydrated
                & RoleDashboardState.authorized
                & (RoleDashboardState.authorized_role == role),
                rx.el.section(
                    rx.icon(
                        "shield-check",
                        class_name="mb-6 h-11 w-11 rounded-full bg-[#EAF3EF] p-2.5 text-[#246D67]",
                    ),
                    rx.el.p(
                        title,
                        class_name="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#28766F]",
                    ),
                    rx.el.h1(
                        f"Welcome, {RoleDashboardState.full_name}",
                        class_name="mt-3 break-words text-2xl font-semibold tracking-tight text-[#172B3D]",
                    ),
                    rx.el.button(
                        rx.icon("log-out", class_name="h-4 w-4"),
                        "Logout",
                        type="button",
                        on_click=RoleDashboardState.logout,
                        class_name="mt-7 flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
                    ),
                    class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 sm:p-9",
                ),
                rx.el.div(
                    rx.el.p(
                        "Verifying your account…",
                        class_name="animate-pulse text-sm text-[#667078]",
                    ),
                    role="status",
                    custom_attrs={"aria-live": "polite"},
                    class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 text-center sm:p-9",
                ),
            ),
            rx.el.footer(
                "One university. Your connection.",
                class_name="mt-7 text-center text-xs tracking-wide text-[#7B8385]",
            ),
            class_name="w-full max-w-[440px]",
        ),
        class_name="flex min-h-dvh w-full items-center justify-center bg-[#F7F6EF] px-5 py-12 font-['Inter',sans-serif] text-[#172B3D]",
    )
