import reflex as rx
from UniFlow_.components.signup import signup_portal
from UniFlow_.components.login import identity_portal
from UniFlow_.states.signup_state import SignupState
from UniFlow_.components.role_dashboard import role_dashboard
from UniFlow_.states.role_dashboard_state import RoleDashboardState


def index() -> rx.Component:
    return identity_portal()


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(
            rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""
        ),
        rx.el.link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        ),
    ],
)
app.add_page(index, route="/", title="Sign in · UniFlow")


def signup() -> rx.Component:
    return signup_portal()


app.add_page(
    signup,
    route="/signup",
    title="Request an account · UniFlow",
    on_load=SignupState.reset_form,
)


def student() -> rx.Component:
    return role_dashboard("student", "Student Dashboard")


def faculty() -> rx.Component:
    return role_dashboard("faculty", "Faculty Dashboard")


def programadmin() -> rx.Component:
    return role_dashboard("program_admin", "Program Admin Dashboard")


def sponsor() -> rx.Component:
    return role_dashboard("sponsor", "Sponsor Dashboard")


app.add_page(
    student,
    route="/student",
    title="Student Dashboard · UniFlow",
    on_load=RoleDashboardState.authorize("student"),
)
app.add_page(
    faculty,
    route="/faculty",
    title="Faculty Dashboard · UniFlow",
    on_load=RoleDashboardState.authorize("faculty"),
)
app.add_page(
    programadmin,
    route="/programadmin",
    title="Program Admin Dashboard · UniFlow",
    on_load=RoleDashboardState.authorize("program_admin"),
)
app.add_page(
    sponsor,
    route="/sponsor",
    title="Sponsor Dashboard · UniFlow",
    on_load=RoleDashboardState.authorize("sponsor"),
)
