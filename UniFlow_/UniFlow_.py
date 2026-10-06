import reflex as rx
from UniFlow_.components.signup import signup_portal
from UniFlow_.components.login import identity_portal
from UniFlow_.states.signup_state import SignupState


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


app.add_page(signup, route="/signup", title="Request an account · UniFlow", on_load=SignupState.reset_form)