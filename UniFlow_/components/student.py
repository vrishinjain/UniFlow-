import reflex as rx

from UniFlow_.states.student_state import StudentState


def student_welcome_card() -> rx.Component:
    return rx.el.section(
        rx.icon("graduation-cap", class_name="mb-6 h-8 w-8 text-[#246D67]"),
        rx.el.p(
            "STUDENT DASHBOARD",
            class_name="text-[11px] font-semibold tracking-[0.18em] text-[#246D67]",
        ),
        rx.el.h1(
            f"Welcome, {StudentState.full_name}",
            class_name="mt-3 break-words text-2xl font-semibold tracking-tight text-[#172B3D]",
        ),
        rx.el.button(
            rx.icon("log-out", class_name="h-4 w-4"),
            "Sign out",
            type="button",
            on_click=StudentState.logout,
            class_name="mt-7 flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
        ),
        class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 sm:p-9",
    )


def student_portal() -> rx.Component:
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
                StudentState.authorized,
                student_welcome_card(),
                rx.el.p(
                    "Verifying access…",
                    role="status",
                    custom_attrs={"aria-live": "polite"},
                    class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-9 text-center text-sm text-[#667078]",
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
