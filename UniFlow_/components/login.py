import reflex as rx

from UniFlow_.states.login_state import LoginState


def login_form() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                "UNIVERSITY IDENTITY",
                class_name="text-[11px] font-semibold tracking-[0.18em] text-[#28766F]",
            ),
            rx.el.h1(
                "Sign in to UniFlow",
                class_name="mt-3 text-2xl font-semibold tracking-tight text-[#172B3D]",
            ),
            rx.el.p(
                "Use your university account to sign in.",
                class_name="mt-2 text-sm leading-6 text-[#667078]",
            ),
            class_name="mb-7",
        ),
        rx.el.form(
            rx.el.div(
                rx.el.label(
                    "Email address",
                    html_for="login-email",
                    class_name="mb-2 block text-sm font-medium text-[#172B3D]",
                ),
                rx.el.input(
                    id="login-email",
                    name="email",
                    type="email",
                    auto_complete="username",
                    placeholder="you@university.edu",
                    required=True,
                    default_value=LoginState.email,
                    key=LoginState.email,
                    disabled=LoginState.loading,
                    custom_attrs={
                        "autocapitalize": "none",
                        "spellcheck": "false",
                    },
                    class_name="h-12 w-full rounded-lg border border-[#D9DEDC] bg-white px-3.5 text-base text-[#172B3D] placeholder:text-[#929A9E] focus:border-[#28766F] focus:outline-hidden focus:ring-2 focus:ring-[#28766F]/20 disabled:cursor-not-allowed disabled:bg-[#F5F5F1]",
                ),
                class_name="mb-5",
            ),
            rx.el.div(
                rx.el.label(
                    "Password",
                    html_for="login-password",
                    class_name="mb-2 block text-sm font-medium text-[#172B3D]",
                ),
                rx.el.input(
                    id="login-password",
                    name="password",
                    type="password",
                    auto_complete="current-password",
                    placeholder="Enter your password",
                    required=True,
                    default_value="",
                    key=LoginState.password_revision,
                    disabled=LoginState.loading,
                    custom_attrs={"aria-describedby": "login-feedback"},
                    class_name="h-12 w-full rounded-lg border border-[#D9DEDC] bg-white px-3.5 text-base text-[#172B3D] placeholder:text-[#929A9E] focus:border-[#28766F] focus:outline-hidden focus:ring-2 focus:ring-[#28766F]/20 disabled:cursor-not-allowed disabled:bg-[#F5F5F1]",
                ),
                class_name="mb-2",
            ),
            rx.el.div(
                rx.cond(
                    LoginState.message != "",
                    rx.el.p(
                        LoginState.message,
                        class_name="rounded-lg border border-[#E3DDD2] bg-[#F8F5EF] px-3 py-3 text-sm leading-5 text-[#172B3D]",
                    ),
                    rx.fragment(),
                ),
                id="login-feedback",
                role="status",
                custom_attrs={"aria-live": "polite", "aria-atomic": "true"},
                class_name="my-4 text-[#172B3D]",
            ),
            rx.el.button(
                rx.cond(
                    LoginState.loading,
                    rx.el.span("Signing in…", class_name="animate-pulse"),
                    rx.el.span(
                        "Sign in",
                        rx.el.span(" →", custom_attrs={"aria-hidden": "true"}),
                    ),
                ),
                type="submit",
                disabled=LoginState.loading,
                class_name="flex h-12 w-full items-center justify-center rounded-lg bg-[#246D67] px-4 text-sm font-semibold text-white transition-colors hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-wait disabled:bg-[#548B85]",
            ),
            on_submit=LoginState.sign_in,
            on_focus=LoginState.clear_feedback,
            custom_attrs={"aria-busy": LoginState.loading},
        ),
            rx.el.p(
                "Don't have an account? ",
                rx.el.a(
                    "Request one",
                    href="/signup",
                    class_name="font-semibold text-[#246D67] underline hover:text-[#1C5752]",
                ),
            class_name="mt-6 border-t border-[#E9EBE6] pt-5 text-center text-sm leading-5 text-[#737C81]",
        ),
        class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 sm:p-9",
    )


def signed_in_card() -> rx.Component:
    return rx.el.section(
        rx.el.span(
            "✓",
            custom_attrs={"aria-hidden": "true"},
            class_name="mb-6 inline-flex h-11 w-11 items-center justify-center rounded-full bg-[#EAF3EF] text-xl text-[#246D67]",
        ),
        rx.el.p(
            "SIGNED IN",
            class_name="text-[11px] font-semibold tracking-[0.18em] text-[#28766F]",
        ),
        rx.el.h1(
            rx.cond(
                LoginState.full_name != "",
                f"Welcome, {LoginState.full_name}",
                "Welcome to UniFlow",
            ),
            class_name="mt-3 break-words text-2xl font-semibold tracking-tight text-[#172B3D]",
        ),
        rx.el.p(
            "You’re signed in to your university account.",
            class_name="mt-3 text-sm leading-6 text-[#667078]",
        ),
        rx.el.p(
            LoginState.email,
            class_name="mt-4 break-all rounded-lg bg-[#F6F7F3] px-4 py-3 text-sm text-[#172B3D]",
        ),
        rx.el.button(
            "Sign out",
            type="button",
            on_click=LoginState.sign_out,
            class_name="mt-7 h-12 w-full rounded-lg border border-[#BFCFC9] bg-white text-sm font-semibold text-[#246D67] transition-colors hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
        ),
        role="status",
        custom_attrs={"aria-live": "polite"},
        class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-7 sm:p-9",
    )


def identity_portal() -> rx.Component:
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
            rx.cond(LoginState.signed_in, signed_in_card(), login_form()),
            rx.el.footer(
                "One university. Your connection.",
                class_name="mt-7 text-center text-xs tracking-wide text-[#7B8385]",
            ),
            class_name="w-full max-w-[440px]",
        ),
        class_name="flex min-h-dvh w-full items-center justify-center bg-[#F7F6EF] px-5 py-12 font-['Inter',sans-serif] text-[#172B3D]",
    )
