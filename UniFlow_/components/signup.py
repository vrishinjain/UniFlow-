import reflex as rx

from UniFlow_.states.signup_state import SignupState

INPUT_CLASS = (
    "h-12 w-full rounded-lg border border-[#D9DEDC] bg-white px-3.5 text-base "
    "text-[#172B3D] placeholder:text-[#929A9E] focus:border-[#28766F] "
    "focus:outline-hidden focus:ring-2 focus:ring-[#28766F]/20 "
    "disabled:cursor-not-allowed disabled:bg-[#F5F5F1]"
)
LABEL_CLASS = "mb-2 block text-sm font-medium text-[#172B3D]"
LINK_CLASS = "font-semibold text-[#246D67] underline underline-offset-2 hover:text-[#1C5752]"


def field(label: str, field_id: str, name: str, **input_props) -> rx.Component:
    return rx.el.div(
        rx.el.label(label, html_for=field_id, class_name=LABEL_CLASS),
        rx.el.input(
            id=field_id,
            name=name,
            required=True,
            disabled=SignupState.loading,
            class_name=INPUT_CLASS,
            **input_props,
        ),
        class_name="mb-5",
    )


def signup_form() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Request an account",
            class_name="text-2xl font-semibold tracking-tight text-[#172B3D]",
        ),
        rx.el.p(
            "An administrator reviews every request. You can sign in once it's approved.",
            class_name="mt-2 mb-7 text-sm leading-6 text-[#667078]",
        ),
        rx.el.form(
            field("Full name", "signup-name", "full_name", type="text", auto_complete="name"),
            field(
                "Email address", "signup-email", "email",
                type="email", auto_complete="email",
                custom_attrs={"autocapitalize": "none", "spellcheck": "false"},
            ),
            rx.el.div(
                rx.el.label("Account type", html_for="signup-type", class_name=LABEL_CLASS),
                rx.el.select(
                    rx.el.option("Choose one", value="", disabled=True),
                    rx.el.option("Student", value="student"),
                    rx.el.option("Faculty", value="faculty"),
                    rx.el.option("Sponsor", value="sponsor"),
                    rx.el.option("Program Admin", value="program_admin"),
                    id="signup-type",
                    name="account_type",
                    default_value="",
                    required=True,
                    disabled=SignupState.loading,
                    class_name=INPUT_CLASS,
                ),
                class_name="mb-5",
            ),
            field(
                "Password", "signup-password", "password",
                type="password", auto_complete="new-password",
                placeholder="At least 8 characters",
            ),
            field(
                "Confirm password", "signup-confirm", "confirm_password",
                type="password", auto_complete="new-password",
            ),
            rx.el.div(
                rx.cond(
                    SignupState.message != "",
                    rx.el.p(
                        SignupState.message,
                        class_name="rounded-lg border border-[#E3DDD2] bg-[#F8F5EF] px-3 py-3 text-sm leading-5 text-[#172B3D]",
                    ),
                    rx.fragment(),
                ),
                role="status",
                custom_attrs={"aria-live": "polite"},
                class_name="mb-4",
            ),
            rx.el.button(
                rx.cond(SignupState.loading, "Sending request...", "Send request"),
                type="submit",
                disabled=SignupState.loading,
                class_name=(
                    "flex h-12 w-full items-center justify-center rounded-lg bg-[#246D67] px-4 "
                    "text-sm font-semibold text-white transition-colors hover:bg-[#1C5752] "
                    "focus-visible:outline-2 focus-visible:outline-offset-4 "
                    "focus-visible:outline-[#28766F] disabled:cursor-wait disabled:bg-[#548B85]"
                ),
            ),
            on_submit=SignupState.request_account,
            on_focus=SignupState.clear_feedback,
        ),
        rx.el.p(
            "Already have an account? ",
            rx.el.a("Sign in", href="/", class_name=LINK_CLASS),
            class_name="mt-6 border-t border-[#E9EBE6] pt-5 text-center text-sm text-[#737C81]",
        ),
    )


def request_sent_card() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Request sent",
            class_name="text-2xl font-semibold tracking-tight text-[#172B3D]",
        ),
        rx.el.p(
            "We've sent your request for ",
            rx.el.span(SignupState.submitted_email, class_name="font-medium break-words text-[#172B3D]"),
            " to an administrator. Try signing in after it's approved.",
            class_name="mt-3 text-sm leading-6 text-[#667078]",
        ),
        rx.el.a(
            "Back to sign in",
            href="/",
            class_name=(
                "mt-7 flex h-12 w-full items-center justify-center rounded-lg border "
                "border-[#BFCFC9] bg-white text-sm font-semibold text-[#246D67] "
                "hover:bg-[#F0F6F3]"
            ),
        ),
        role="status",
    )


def signup_portal() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            rx.el.p(
                "UniFlow",
                class_name="mb-9 text-center text-2xl font-semibold tracking-tight text-[#172B3D]",
            ),
            rx.el.div(
                rx.cond(SignupState.submitted, request_sent_card(), signup_form()),
                class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 sm:p-9",
            ),
            class_name="w-full max-w-[440px]",
        ),
        class_name="flex min-h-dvh w-full items-center justify-center bg-[#F7F6EF] px-5 py-12 font-['Inter',sans-serif] text-[#172B3D]",
    )
