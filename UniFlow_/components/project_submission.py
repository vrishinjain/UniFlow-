import reflex as rx

from UniFlow_.components.dashboard_layout import page_header
from UniFlow_.states.sponsor_state import SponsorState
from UniFlow_.utils.files import MAX_FILE_BYTES


def inline_error(message, error_id: str) -> rx.Component:
    return rx.el.div(
        rx.cond(
            message != "",
            rx.el.p(message, class_name="mt-2 text-sm text-red-700"),
            rx.fragment(),
        ),
        id=error_id,
        role="status",
        custom_attrs={"aria-live": "polite"},
    )


def submission_button(on_click: rx.event.EventType) -> rx.Component:
    return rx.el.button(
        rx.cond(
            SponsorState.loading,
            rx.icon("loader-circle", class_name="h-4 w-4 animate-spin"),
            rx.icon("send", class_name="h-4 w-4"),
        ),
        rx.cond(SponsorState.loading, "Submitting…", "Submit project"),
        type="button",
        on_click=on_click,
        disabled=SponsorState.loading | ~SponsorState.authorized,
        class_name="flex w-full items-center justify-center gap-2 rounded-lg bg-[#246D67] px-5 py-3 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F] disabled:cursor-not-allowed disabled:bg-[#548B85] sm:w-auto",
    )


def project_submission() -> rx.Component:
    return rx.el.div(
        page_header(
            "Sponsor",
            "Submit project",
            "Propose a project for university review. Describe your idea and optionally include supporting documents.",
        ),
        rx.el.section(
            rx.el.div(
                rx.icon("file-plus", class_name="h-5 w-5 text-[#246D67]"),
                rx.el.h2(
                    "Project details",
                    class_name="text-lg font-semibold text-[#172B3D]",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.p(
                "Title and description are required. Attachments are optional.",
                class_name="mt-2 text-sm text-[#667078]",
            ),
            rx.el.div(
                rx.el.label(
                    "Project title",
                    rx.el.span(" *", class_name="text-red-700"),
                    html_for="project_title",
                    class_name="block text-sm font-semibold text-[#172B3D]",
                ),
                rx.el.input(
                    id="project_title",
                    default_value=SponsorState.title,
                    on_change=SponsorState.update_title,
                    disabled=SponsorState.loading,
                    placeholder="Give your project a clear, descriptive title",
                    custom_attrs={
                        "aria-required": "true",
                        "aria-invalid": SponsorState.title_error != "",
                        "aria-describedby": "project_title_error",
                    },
                    class_name="mt-2 w-full rounded-lg border border-[#BFCFC9] bg-white px-4 py-3 text-sm text-[#172B3D] placeholder:text-[#667078] focus:border-[#246D67] focus:outline-2 focus:outline-[#246D67] disabled:cursor-not-allowed disabled:bg-[#F7F6EF]",
                ),
                inline_error(SponsorState.title_error, "project_title_error"),
                class_name="mt-6",
            ),
            rx.el.div(
                rx.el.label(
                    "Project description",
                    rx.el.span(" *", class_name="text-red-700"),
                    html_for="project_description",
                    class_name="block text-sm font-semibold text-[#172B3D]",
                ),
                rx.el.p(
                    "Include the problem, objectives, expected outcomes, and any requirements.",
                    id="project_description_help",
                    class_name="mt-1 text-xs leading-5 text-[#667078]",
                ),
                rx.el.textarea(
                    id="project_description",
                    default_value=SponsorState.description,
                    on_change=SponsorState.update_description,
                    disabled=SponsorState.loading,
                    rows=7,
                    placeholder="Tell us about your proposed project…",
                    custom_attrs={
                        "aria-required": "true",
                        "aria-invalid": SponsorState.description_error != "",
                        "aria-describedby": "project_description_help project_description_error",
                    },
                    class_name="mt-2 w-full resize-y rounded-lg border border-[#BFCFC9] bg-white px-4 py-3 text-sm leading-6 text-[#172B3D] placeholder:text-[#667078] focus:border-[#246D67] focus:outline-2 focus:outline-[#246D67] disabled:cursor-not-allowed disabled:bg-[#F7F6EF]",
                ),
                inline_error(
                    SponsorState.description_error, "project_description_error"
                ),
                class_name="mt-6",
            ),
            rx.el.div(
                rx.el.h3(
                    "Supporting documents (optional)",
                    id="project_files_label",
                    class_name="text-sm font-semibold text-[#172B3D]",
                ),
                rx.upload.root(
                    rx.icon(
                        "upload", class_name="mx-auto h-6 w-6 text-[#246D67]"
                    ),
                    rx.el.p(
                        "Click to select files or drop them here",
                        class_name="mt-3 text-sm font-semibold text-[#246D67]",
                    ),
                    rx.el.p(
                        "PDF, DOCX, or PPTX · maximum 3 files · 10 MB each",
                        class_name="mt-2 text-xs text-[#667078]",
                    ),
                    id="project_files",
                    multiple=True,
                    max_files=3,
                    max_size=MAX_FILE_BYTES,
                    accept={
                        "application/pdf": [".pdf", ".PDF"],
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
                            ".docx",
                            ".DOCX",
                        ],
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation": [
                            ".pptx",
                            ".PPTX",
                        ],
                    },
                    disabled=SponsorState.loading | ~SponsorState.authorized,
                    custom_attrs={
                        "aria-labelledby": "project_files_label",
                        "aria-describedby": "project_upload_error",
                    },
                    class_name="mt-3 w-full cursor-pointer rounded-xl border border-dashed border-[#BFCFC9] bg-[#F7F6EF] p-6 text-center transition-colors hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
                ),
                rx.el.ul(
                    rx.foreach(
                        rx.selected_files("project_files"),
                        lambda filename: rx.el.li(
                            rx.icon(
                                "file-text",
                                class_name="h-4 w-4 shrink-0 text-[#246D67]",
                            ),
                            rx.el.span(
                                filename,
                                class_name="min-w-0 break-all text-sm text-[#172B3D]",
                            ),
                            class_name="flex items-center gap-2 py-1",
                        ),
                    ),
                    class_name="mt-3 list-none p-0",
                ),
                rx.el.p(
                    "Check that every intended attachment appears above. If a file is rejected, follow the error below and select your documents again. Documents are also validated before saving.",
                    class_name="mt-2 text-xs leading-5 text-[#667078]",
                ),
                inline_error(SponsorState.upload_error, "project_upload_error"),
                class_name="mt-6",
            ),
            inline_error(
                SponsorState.submission_error, "project_submission_error"
            ),
            rx.el.div(
                rx.el.p(
                    rx.cond(
                        SponsorState.loading,
                        "Validating and saving your submission…",
                        "Your project and attachments will be saved together.",
                    ),
                    role="status",
                    custom_attrs={"aria-live": "polite"},
                    class_name="text-xs leading-5 text-[#667078]",
                ),
                rx.cond(
                    rx.selected_files("project_files").length() == 0,
                    submission_button(SponsorState.submit_without_files),
                    submission_button(
                        SponsorState.submit_project(
                            rx.upload_files(upload_id="project_files")
                        )
                    ),
                ),
                class_name="mt-8 flex flex-col gap-4 border-t border-[#E9EBE6] pt-6 sm:flex-row sm:items-center sm:justify-between",
            ),
            custom_attrs={"aria-busy": SponsorState.loading},
            class_name="w-full rounded-2xl border border-[#E2E4DC] bg-white p-5 sm:p-8",
        ),
    )
