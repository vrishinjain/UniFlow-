"""T-67: Sponsor project details page: review status, feedback, resubmit."""

import reflex as rx

from UniFlow_.sponsor_review_services import (
    DESCRIPTION_MAX_CHARS,
    TITLE_MAX_CHARS,
)
from UniFlow_.states.sponsor_project_state import SponsorProjectState


_CARD = "w-full rounded-2xl border border-[#E2E4DC] bg-white p-5 sm:p-8"
_LABEL = "block text-sm font-semibold text-[#172B3D]"
_INPUT = (
    "mt-2 w-full rounded-lg border border-[#C9CFCC] bg-white px-3 py-2 "
    "text-sm text-[#172B3D] focus:outline-2 focus:outline-[#246D67]"
)


def status_badge(status, label) -> rx.Component:
    """Colored badge; also used in the My projects table."""
    return rx.el.span(
        label,
        class_name=rx.match(
            status,
            (
                "accepted",
                "inline-block w-fit rounded-full bg-[#EAF3EF] px-3 py-1 text-xs font-semibold text-[#246D67]",
            ),
            (
                "revision_requested",
                "inline-block w-fit rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800",
            ),
            (
                "rejected",
                "inline-block w-fit rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700",
            ),
            "inline-block w-fit rounded-full bg-[#EEF1F4] px-3 py-1 text-xs font-semibold text-[#4A5560]",
        ),
    )


def _notice(title: str, body, tone: str) -> rx.Component:
    tones = {
        "amber": "border-amber-200 bg-amber-50 text-amber-900",
        "red": "border-red-200 bg-red-50 text-red-800",
        "green": "border-[#CDE1D7] bg-[#EAF3EF] text-[#1C5752]",
        "gray": "border-[#E2E4DC] bg-[#F7F6EF] text-[#4A5560]",
    }
    return rx.el.div(
        rx.el.p(title, class_name="text-sm font-semibold"),
        rx.el.p(body, class_name="mt-1 whitespace-pre-wrap text-sm"),
        role="status",
        class_name=f"rounded-xl border p-4 {tones[tone]}",
    )


def _feedback_text():
    return rx.cond(
        SponsorProjectState.project["feedback"] != "",
        SponsorProjectState.project["feedback"],
        "No notes were left.",
    )


def _resubmit_form() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "Edit and resubmit",
            class_name="text-lg font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            "Update your project based on the feedback, then resubmit it for "
            "review. Your attachments stay the same.",
            class_name="mt-1 text-sm text-[#667078]",
        ),
        rx.el.div(
            rx.el.label("Title", html_for="resubmit-title", class_name=_LABEL),
            rx.el.input(
                id="resubmit-title",
                value=SponsorProjectState.edit_title,
                on_change=SponsorProjectState.set_edit_title,
                max_length=TITLE_MAX_CHARS,
                disabled=SponsorProjectState.saving,
                class_name=_INPUT,
            ),
            class_name="mt-6",
        ),
        rx.el.div(
            rx.el.label(
                "Description",
                html_for="resubmit-description",
                class_name=_LABEL,
            ),
            rx.el.textarea(
                id="resubmit-description",
                value=SponsorProjectState.edit_description,
                on_change=SponsorProjectState.set_edit_description,
                max_length=DESCRIPTION_MAX_CHARS,
                rows=8,
                disabled=SponsorProjectState.saving,
                class_name=_INPUT,
            ),
            class_name="mt-4",
        ),
        rx.cond(
            SponsorProjectState.form_error != "",
            rx.el.p(
                SponsorProjectState.form_error,
                role="alert",
                class_name="mt-4 text-sm text-red-700",
            ),
        ),
        rx.el.button(
            rx.cond(
                SponsorProjectState.saving,
                "Resubmitting…",
                "Resubmit for review",
            ),
            on_click=SponsorProjectState.resubmit,
            disabled=SponsorProjectState.saving,
            class_name="mt-6 rounded-lg bg-[#246D67] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1C5752] disabled:opacity-60",
        ),
        class_name=f"mt-6 {_CARD}",
    )


def _status_section() -> rx.Component:
    status = SponsorProjectState.project["status"]
    return rx.match(
        status,
        (
            "revision_requested",
            rx.el.div(
                _notice("Faculty requested changes", _feedback_text(), "amber"),
                _resubmit_form(),
            ),
        ),
        (
            "rejected",
            _notice(
                "This project was rejected",
                _feedback_text(),
                "red",
            ),
        ),
        (
            "accepted",
            _notice(
                "This project was accepted",
                "Faculty accepted your project and shared it with their courses.",
                "green",
            ),
        ),
        _notice(
            "Waiting for faculty review",
            "You'll see faculty feedback here once your project is reviewed.",
            "gray",
        ),
    )


def sponsor_project_content() -> rx.Component:
    return rx.el.div(
        rx.el.a(
            "← Back to My projects",
            href="/sponsor/projects",
            class_name="text-sm font-medium text-[#246D67] hover:underline",
        ),
        rx.cond(
            ~SponsorProjectState.loaded,
            rx.el.p(
                "Loading your project…",
                role="status",
                class_name=f"mt-6 {_CARD} text-sm text-[#667078]",
            ),
            rx.cond(
                SponsorProjectState.page_error != "",
                rx.el.p(
                    SponsorProjectState.page_error,
                    role="alert",
                    class_name=f"mt-6 {_CARD} text-sm text-red-700",
                ),
                rx.el.div(
                    rx.cond(
                        SponsorProjectState.form_message != "",
                        rx.el.div(
                            _notice(
                                "Resubmitted",
                                SponsorProjectState.form_message,
                                "green",
                            ),
                            class_name="mb-6",
                        ),
                    ),
                    rx.el.section(
                        rx.el.div(
                            rx.el.h1(
                                SponsorProjectState.project["title"],
                                class_name="break-words text-2xl font-semibold text-[#172B3D]",
                            ),
                            status_badge(
                                SponsorProjectState.project["status"],
                                SponsorProjectState.project["status_label"],
                            ),
                            class_name="flex flex-wrap items-center gap-3",
                        ),
                        rx.el.p(
                            SponsorProjectState.project["description"],
                            class_name="mt-4 whitespace-pre-wrap text-sm leading-6 text-[#172B3D]",
                        ),
                        class_name=_CARD,
                    ),
                    rx.el.div(_status_section(), class_name="mt-6"),
                    class_name="mt-6",
                ),
            ),
        ),
        class_name="w-full min-w-0",
    )
