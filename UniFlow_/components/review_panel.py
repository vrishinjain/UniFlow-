"""T-65: Review panel shown on the faculty project details page."""

import reflex as rx

from UniFlow_.review_services import NOTES_MAX_CHARS
from UniFlow_.states.faculty_state import FacultyState
from UniFlow_.states.review_state import ReviewState


def _history_row(entry: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(entry["label"], weight="bold"),
            rx.text(entry["created_at"], color="gray", size="2"),
            spacing="3",
            align="center",
        ),
        rx.text("By ", entry["reviewer"], color="gray", size="2"),
        rx.cond(
            entry["notes"] != "",
            rx.text(entry["notes"], margin_top="4px", white_space="pre-wrap"),
        ),
        border="1px solid #D9DEDC",
        border_radius="8px",
        padding="12px",
        width="100%",
    )


def _reject_button() -> rx.Component:
    """Reject is final, so it asks for confirmation first."""
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button(
                "Reject",
                color_scheme="red",
                variant="soft",
                disabled=ReviewState.saving,
            )
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Reject this project?"),
            rx.alert_dialog.description(
                "Rejecting is final. The sponsor will see your reason "
                "and cannot resubmit this project."
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="soft", color_scheme="gray")
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Reject project",
                        color_scheme="red",
                        on_click=ReviewState.reject,
                    )
                ),
                spacing="3",
                justify="end",
                margin_top="16px",
            ),
        ),
    )


def _review_form() -> rx.Component:
    return rx.vstack(
        rx.text(
            "Accept the project, ask the sponsor for changes, or reject it. "
            "Notes are required to request changes or reject.",
            color="gray",
            size="2",
        ),
        rx.text_area(
            placeholder="Notes for the sponsor",
            value=ReviewState.notes,
            on_change=ReviewState.set_notes,
            max_length=NOTES_MAX_CHARS,
            rows="4",
            width="100%",
        ),
        rx.hstack(
            rx.button(
                "Accept",
                color_scheme="green",
                on_click=ReviewState.accept,
                loading=ReviewState.saving,
            ),
            rx.button(
                "Request revision",
                variant="outline",
                on_click=ReviewState.request_revision,
                loading=ReviewState.saving,
            ),
            _reject_button(),
            spacing="3",
            wrap="wrap",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def review_panel() -> rx.Component:
    status = FacultyState.selected_project["status"]
    return rx.vstack(
        rx.heading("Review", size="4"),
        rx.cond(
            status == "pending",
            _review_form(),
            rx.text(
                "This project has already been reviewed. Current status: ",
                status,
                color="gray",
            ),
        ),
        rx.cond(
            ReviewState.review_error != "",
            rx.callout(
                ReviewState.review_error,
                icon="triangle_alert",
                color_scheme="red",
                width="100%",
            ),
        ),
        rx.cond(
            ReviewState.review_message != "",
            rx.callout(
                ReviewState.review_message,
                icon="circle_check",
                color_scheme="green",
                width="100%",
            ),
        ),
        rx.heading("Review history", size="4", margin_top="8px"),
        rx.cond(
            ReviewState.history.length() > 0,
            rx.vstack(
                rx.foreach(ReviewState.history, _history_row),
                spacing="3",
                width="100%",
            ),
            rx.text("No reviews yet.", color="gray"),
        ),
        spacing="3",
        align="start",
        width="100%",
    )
