import reflex as rx


def brand() -> rx.Component:
    return rx.el.div(
        rx.el.span(class_name="h-2.5 w-2.5 rounded-full bg-[#187F78]"),
        rx.el.span(
            "UniFlow",
            class_name="text-lg font-bold tracking-tight text-[#172B3B]",
        ),
        class_name="flex items-center gap-3",
    )


def role_link(number: str, label: str, destination: str) -> rx.Component:
    return rx.el.a(
        rx.el.span(
            number,
            class_name="w-9 shrink-0 text-sm font-semibold tabular-nums text-[#187F78]",
            aria_hidden="true",
        ),
        rx.el.span(
            label,
            class_name="min-w-0 flex-1 text-lg font-semibold tracking-tight text-[#172B3B] sm:text-xl",
        ),
        rx.el.span(
            "↗",
            class_name="inline-flex h-5 w-5 shrink-0 items-center justify-center text-xl leading-none text-[#187F78]",
            aria_hidden="true",
        ),
        href=destination,
        class_name="group flex min-h-20 w-full items-center gap-4 rounded-2xl border border-[#DEDCD3] bg-white px-5 py-5 transition-colors hover:border-[#187F78] hover:bg-[#F1F8F5] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#187F78] sm:gap-6 sm:px-7 sm:py-6",
    )


def index() -> rx.Component:
    return rx.el.div(
        rx.el.main(
            brand(),
            rx.el.div(
                rx.el.p(
                    "ACADEMIC PROGRAM PORTAL",
                    class_name="mb-5 text-xs font-bold tracking-[0.18em] text-[#187F78]",
                ),
                rx.el.h1(
                    "Find your place in the program.",
                    class_name="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-[#172B3B] sm:text-5xl",
                ),
                rx.el.p(
                    "Select your role to continue.",
                    class_name="mt-5 text-base leading-relaxed text-[#526372] sm:text-lg",
                ),
                class_name="mt-20 mb-12 sm:mt-28 sm:mb-14",
            ),
            rx.el.nav(
                role_link("01", "Students", "/students"),
                role_link("02", "Faculty advisors", "/faculty-advisors"),
                role_link("03", "Project sponsors", "/project-sponsors"),
                role_link(
                    "04", "Program administrators", "/program-administrators"
                ),
                role_link(
                    "05", "System administrators", "/system-administrators"
                ),
                aria_label="Choose your role",
                class_name="flex flex-col gap-3 sm:gap-4",
            ),
            class_name="mx-auto w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-12",
        ),
        class_name="min-h-dvh bg-[#F8F6F0] font-['Inter'] text-[#172B3B]",
    )


def role_page(role: str, welcome: str) -> rx.Component:
    return rx.el.div(
        rx.el.main(
            brand(),
            rx.el.div(
                rx.el.p(
                    "ACADEMIC PROGRAM PORTAL",
                    class_name="mb-5 text-xs font-bold tracking-[0.18em] text-[#187F78]",
                ),
                rx.el.h1(
                    role,
                    class_name="text-4xl font-semibold leading-tight tracking-tight text-[#172B3B] sm:text-5xl",
                ),
                rx.el.p(
                    welcome,
                    class_name="mt-6 text-lg leading-relaxed text-[#526372] sm:text-xl",
                ),
                rx.el.a(
                    rx.el.span(
                        "←",
                        class_name="inline-flex h-4 w-4 items-center justify-center text-base leading-none",
                        aria_hidden="true",
                    ),
                    "Back to directory",
                    href="/",
                    class_name="mt-12 inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-semibold text-[#187F78] underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#187F78]",
                ),
                class_name="mt-20 rounded-2xl border border-[#DEDCD3] bg-white px-6 py-10 sm:mt-28 sm:px-10 sm:py-14",
            ),
            class_name="mx-auto w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-12",
        ),
        class_name="min-h-dvh bg-[#F8F6F0] font-['Inter'] text-[#172B3B]",
    )


def students_page() -> rx.Component:
    return role_page("Students", "Welcome, student.")


def faculty_advisors_page() -> rx.Component:
    return role_page("Faculty advisors", "Welcome, faculty advisor.")


def project_sponsors_page() -> rx.Component:
    return role_page("Project sponsors", "Welcome, project sponsor.")


def program_administrators_page() -> rx.Component:
    return role_page(
        "Program administrators", "Welcome, program administrator."
    )


def system_administrators_page() -> rx.Component:
    return role_page("System administrators", "Welcome, system administrator.")


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(
            rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, route="/", title="UniFlow | Role directory")
app.add_page(students_page, route="/students", title="Students | UniFlow")
app.add_page(
    faculty_advisors_page,
    route="/faculty-advisors",
    title="Faculty advisors | UniFlow",
)
app.add_page(
    project_sponsors_page,
    route="/project-sponsors",
    title="Project sponsors | UniFlow",
)
app.add_page(
    program_administrators_page,
    route="/program-administrators",
    title="Program administrators | UniFlow",
)
app.add_page(
    system_administrators_page,
    route="/system-administrators",
    title="System administrators | UniFlow",
)
