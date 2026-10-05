"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from UniFlow_.user_model import User
from rxconfig import config


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


app = rx.App(theme=rx.theme(appearance="light"))
app.add_page(index)
