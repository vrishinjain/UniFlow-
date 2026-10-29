import reflex as rx
from UniFlow_.components.signup import signup_portal
from UniFlow_.components.login import identity_portal
from UniFlow_.states.signup_state import SignupState
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.admin_state import AdminState
from UniFlow_.components.admin import ADMIN_PAGES
from UniFlow_.components.student import STUDENT_PAGES
from UniFlow_.components.student_projects import student_projects_portal
from UniFlow_.components.student_project_detail import (
    student_project_detail_portal,
)
from UniFlow_.components.faculty import FACULTY_PAGES
from UniFlow_.components.program_admin import PROGRAM_ADMIN_PAGES
from UniFlow_.components.sponsor import SPONSOR_PAGES
from UniFlow_.states.student_state import StudentState
from UniFlow_.states.student_projects_state import StudentProjectsState
from UniFlow_.states.student_project_detail_state import (
    StudentProjectDetailState,
)
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.states.program_admin_state import ProgramAdminState
from UniFlow_.states.sponsor_state import SponsorState
from UniFlow_.components.set_password import set_password_portal
from UniFlow_.states.set_password_state import SetPasswordState


def index() -> rx.Component:
    return identity_portal()


app = rx.App(
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
app.add_page(
    index,
    route="/",
    title="Sign in · UniFlow",
    on_load=LoginState.redirect_signed_in_user,
)


def signup() -> rx.Component:
    return signup_portal()


app.add_page(
    signup,
    route="/signup",
    title="Request an account · UniFlow",
    on_load=SignupState.reset_form,
)


# Dashboard pages. Each role's pages share that role's access check, so a user
# can only open pages for their own role. To add a page, edit the role's
# *_PAGES list in UniFlow_/components/<role>.py.
for pages, on_load in (
    (ADMIN_PAGES, AdminState.load_admin),
    (STUDENT_PAGES, StudentState.load_student),
    (FACULTY_PAGES, FacultyState.load_faculty),
    (PROGRAM_ADMIN_PAGES, ProgramAdminState.load_program_admin),
    (SPONSOR_PAGES, SponsorState.load_sponsor),
):
    for page, route, title in pages:
        page_on_load = (
            [SponsorState.load_sponsor, SponsorState.load_my_projects]
            if route == "/sponsor/projects"
            else on_load
        )
        app.add_page(
            page, route=route, title=f"{title} · UniFlow", on_load=page_on_load
        )

app.add_page(
    student_projects_portal,
    route="/student/projects",
    title="My Projects · UniFlow",
    on_load=StudentProjectsState.load_student_projects,
)

app.add_page(
    student_project_detail_portal,
    route="/student/projects/[project_id]",
    title="Project · UniFlow",
    on_load=StudentProjectDetailState.load_student_project_detail,
)

app.add_page(
    set_password_portal,
    route="/set-password",
    title="Set your password · UniFlow",
    on_load=SetPasswordState.load_set_password,
)
