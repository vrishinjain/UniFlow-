import reflex as rx

from UniFlow_.states.set_password_state import SetPasswordState

_INPUT_CLASS = (
    "h-12 w-full rounded-lg border border-[#D9DEDC] bg-white px-3.5 text-base "
    "text-[#172B3D] placeholder:text-[#929A9E] focus:border-[#28766F] "
    "focus:outline-hidden focus:ring-2 focus:ring-[#28766F]/20 "
    "disabled:cursor-not-allowed disabled:bg-[#F5F5F1]"
)


def _password_field(label: str, field_id: str, name: str) -> rx.Component:
    return rx.el.div(
        rx.el.label(
            label,
            html_for=field_id,
            class_name="mb-2 block text-sm font-medium text-[#172B3D]",
        ),
        rx.el.input(
            id=field_id,
            name=name,
            type="password",
            auto_complete="new-password",
            required=True,
            min_length=8,
            default_value="",
            key=SetPasswordState.form_revision,
            disabled=SetPasswordState.saving,
            class_name=_INPUT_CLASS,
        ),
        class_name="mb-5",
    )


def set_password_form() -> rx.Component:
    return rx.el.section(
        rx.icon("key-round", class_name="mb-6 h-8 w-8 text-[#246D67]"),
        rx.el.p(
            "FIRST SIGN-IN",
            class_name="text-[11px] font-semibold tracking-[0.18em] text-[#246D67]",
        ),
        rx.el.h1(
            "Set your own password",
            class_name="mt-3 text-2xl font-semibold tracking-tight text-[#172B3D]",
        ),
        rx.el.p(
            "Your account was created with a temporary password. "
            "Choose a new one to continue. It must be at least 8 characters.",
            class_name="mt-2 mb-7 text-sm leading-6 text-[#667078]",
        ),
        rx.el.form(
            _password_field("New password", "new-password", "new_password"),
            _password_field(
                "Confirm new password", "confirm-password", "confirm_password"
            ),
            rx.cond(
                SetPasswordState.message != "",
                rx.el.p(
                    SetPasswordState.message,
                    role="status",
                    class_name="mb-4 rounded-lg border border-[#E3DDD2] bg-[#F8F5EF] px-3 py-3 text-sm leading-5 text-[#172B3D]",
                ),
                rx.fragment(),
            ),
            rx.el.button(
                rx.cond(SetPasswordState.saving, "Saving…", "Save password"),
                type="submit",
                disabled=SetPasswordState.saving,
                class_name="flex h-12 w-full items-center justify-center rounded-lg bg-[#246D67] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#1C5752] disabled:cursor-wait disabled:bg-[#548B85]",
            ),
            on_submit=SetPasswordState.save_password,
        ),
        rx.el.button(
            "Sign out",
            type="button",
            on_click=SetPasswordState.sign_out,
            class_name="mt-4 w-full text-center text-sm font-semibold text-[#246D67] underline hover:text-[#1C5752]",
        ),
        class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 sm:p-9",
    )


def set_password_portal() -> rx.Component:
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
                SetPasswordState.authorized,
                set_password_form(),
                rx.el.p(
                    "Verifying access…",
                    role="status",
                    class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-9 text-center text-sm text-[#667078]",
                ),
            ),
            class_name="w-full max-w-[440px]",
        ),
        class_name="flex min-h-dvh w-full items-center justify-center bg-[#F7F6EF] px-5 py-12 font-['Inter',sans-serif] text-[#172B3D]",
    )
