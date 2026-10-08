import reflex as rx
from UniFlow_.components.signup import signup_portal
from UniFlow_.components.login import identity_portal
from UniFlow_.states.signup_state import SignupState
from UniFlow_.states.admin_state import AdminState
from UniFlow_.components.admin import admin_portal
from UniFlow_.components.student import student_portal
from UniFlow_.components.faculty import faculty_portal
from UniFlow_.components.program_admin import program_admin_portal
from UniFlow_.components.sponsor import sponsor_portal
from UniFlow_.states.student_state import StudentState
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.states.program_admin_state import ProgramAdminState
from UniFlow_.states.sponsor_state import SponsorState


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


def admin() -> rx.Component:
    return admin_portal()


app.add_page(
    admin,
    route="/admin",
    title="Admin page · UniFlow",
    on_load=AdminState.load_admin,
)

app.add_page(
    student_portal,
    route="/student",
    title="Student Dashboard · UniFlow",
    on_load=StudentState.load_student,
)
app.add_page(
    faculty_portal,
    route="/faculty",
    title="Faculty Dashboard · UniFlow",
    on_load=FacultyState.load_faculty,
)
app.add_page(
    program_admin_portal,
    route="/programadmin",
    title="Program Admin Dashboard · UniFlow",
    on_load=ProgramAdminState.load_program_admin,
)
app.add_page(
    sponsor_portal,
    route="/sponsor",
    title="Sponsor Dashboard · UniFlow",
    on_load=SponsorState.load_sponsor,
)
