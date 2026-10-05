"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from UniFlow_.components.admin_dashboard import admin_dashboard
from UniFlow_.states.admin_state import AdminState


class State(rx.State):
    """The app state."""


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.vstack(
            rx.heading("Welcome to Reflex!", size="9"),
            rx.text(
                "Get started by editing ",
                rx.code(f"{config.app_name}/{config.app_name}.py"),
                "\n\n\n*****test 28 september 2026***** (anthony)\n\n",
                size="5",
                white_space="pre",
            ),
            rx.text("Logan was here"),
            rx.link(
                rx.button("Check out our docs!"),
                href="https://reflex.dev/docs/getting-started/introduction/",
                is_external=True,
            ),
            spacing="5",
            justify="center",
            min_height="85vh",
        ),
    )


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
app.add_page(index)
app.add_page(
    admin_dashboard,
    route="/admin",
    title="Admin Dashboard | UniFlow",
    on_load=AdminState.load_pending_users,
)
