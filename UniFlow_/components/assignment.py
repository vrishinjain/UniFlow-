import reflex as rx

from UniFlow_.states.assignment_state import AssignmentState, UPLOAD_ID
from UniFlow_.course_assignment_services import (
    ASSIGNMENT_MAX_BYTES,
    SkippedAssignmentLine,
)


_PRIMARY = "inline-flex w-fit items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]"
_SECONDARY = "inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]"


def _skipped_row(row: SkippedAssignmentLine) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            row["line"], class_name="px-4 py-3 align-top text-sm text-[#172B3D]"
        ),
        rx.el.td(
            row["text"],
            class_name="max-w-md whitespace-pre-wrap break-all px-4 py-3 align-top text-sm text-[#172B3D]",
        ),
        rx.el.td(
            row["reason"],
            class_name="px-4 py-3 align-top text-sm text-[#667078]",
        ),
        key=row["line"],
        class_name="border-t border-[#E2E4DC] bg-white even:bg-[#F7F6EF]",
    )


def _skipped_table() -> rx.Component:
    return rx.cond(
        AssignmentState.skipped_rows.length() > 0,
        rx.el.div(
            rx.el.div(
                rx.el.table(
                    rx.el.caption(
                        "Skipped assignment rows", class_name="sr-only"
                    ),
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th(
                                "Line",
                                scope="col",
                                class_name="px-4 py-3 text-left",
                            ),
                            rx.el.th(
                                "Text",
                                scope="col",
                                class_name="px-4 py-3 text-left",
                            ),
                            rx.el.th(
                                "Reason",
                                scope="col",
                                class_name="px-4 py-3 text-left",
                            ),
                        ),
                        class_name="bg-[#F7F6EF] text-xs font-semibold text-[#172B3D]",
                    ),
                    rx.el.tbody(
                        rx.foreach(AssignmentState.skipped_rows, _skipped_row)
                    ),
                    class_name="table-auto w-full min-w-[560px]",
                ),
                class_name="max-h-96 w-full overflow-auto",
            ),
            class_name="mt-4 w-full overflow-hidden rounded-xl border border-[#E2E4DC]",
        ),
    )


def _replacement_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(
                "Replace course assignments?",
                class_name="text-xl font-semibold text-[#172B3D]",
            ),
            rx.alert_dialog.description(
                f"This course already has {AssignmentState.existing_count} assignments. Importing will replace all of them. Continue?",
                class_name="mt-2 text-sm text-[#667078]",
            ),
            rx.cond(
                AssignmentState.import_error != "",
                rx.el.p(
                    AssignmentState.import_error,
                    role="alert",
                    class_name="mt-3 text-sm text-red-700",
                ),
            ),
            rx.cond(
                AssignmentState.import_message != "",
                rx.el.p(
                    AssignmentState.import_message,
                    role="status",
                    class_name="mt-3 text-sm text-[#246D67]",
                ),
            ),
            rx.el.div(
                rx.el.button(
                    "Cancel",
                    type="button",
                    on_click=AssignmentState.cancel_import,
                    disabled=AssignmentState.busy,
                    class_name=_SECONDARY,
                ),
                rx.el.button(
                    rx.cond(
                        AssignmentState.import_busy, "Replacing…", "Replace"
                    ),
                    type="button",
                    on_click=AssignmentState.replace_assignments,
                    disabled=AssignmentState.busy,
                    class_name=_PRIMARY,
                ),
                class_name="mt-6 flex flex-wrap justify-end gap-3",
            ),
            class_name="w-full max-w-lg rounded-2xl border border-[#E2E4DC] bg-white p-6 font-['Inter'] text-[#172B3D] sm:p-8",
        ),
        open=AssignmentState.replacement_open,
    )


def _assignment_upload() -> rx.Component:
    return rx.el.div(
        rx.el.p(
            "Import one UTF-8 .txt file up to 1 MB. Use student@example.edu joins Exact project title on each line. Blank lines are ignored; invalid rows are skipped and reported. The last literal ‘ joins ’ separates the email and title.",
            class_name="mt-2 text-sm text-[#667078]",
        ),
        rx.el.p(
            "Assignment text file (.txt)",
            id="assignment-upload-label",
            class_name="mt-5 text-sm font-medium text-[#172B3D]",
        ),
        rx.upload.root(
            rx.icon("upload", class_name="mx-auto h-6 w-6 text-[#246D67]"),
            rx.el.button(
                "Select .txt file",
                type="button",
                disabled=AssignmentState.busy
                | AssignmentState.replacement_open,
                aria_label="Select assignment text file, maximum 1 MB",
                class_name=_SECONDARY,
            ),
            rx.el.p(
                "Or drop one .txt file here",
                class_name="mt-2 text-xs text-[#667078]",
            ),
            id=UPLOAD_ID,
            accept={"text/plain": [".txt"]},
            max_files=1,
            max_size=ASSIGNMENT_MAX_BYTES,
            multiple=False,
            disabled=AssignmentState.busy | AssignmentState.replacement_open,
            custom_attrs={"aria-labelledby": "assignment-upload-label"},
            class_name="mt-2 w-full cursor-pointer rounded-xl border border-dashed border-[#BFCFC9] bg-[#F7F6EF] p-5 text-center text-[#172B3D] hover:bg-[#F0F6F3] focus-within:outline-2 focus-within:outline-[#246D67]",
        ),
        rx.el.div(
            rx.foreach(
                rx.selected_files(UPLOAD_ID),
                lambda filename: rx.el.p(
                    filename, class_name="break-all text-sm text-[#172B3D]"
                ),
            ),
            aria_live="polite",
            class_name="mt-3",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("upload", class_name="h-4 w-4"),
                rx.cond(
                    AssignmentState.import_busy,
                    "Importing assignments…",
                    "Import assignments",
                ),
                type="button",
                on_click=AssignmentState.upload_assignments(
                    rx.upload_files(upload_id=UPLOAD_ID)
                ),
                disabled=AssignmentState.busy
                | AssignmentState.replacement_open
                | (rx.selected_files(UPLOAD_ID).length() != 1),
                class_name=_PRIMARY,
            ),
            rx.el.button(
                "Cancel",
                type="button",
                on_click=AssignmentState.cancel_import,
                disabled=AssignmentState.busy,
                class_name=_SECONDARY,
            ),
            class_name="mt-4 flex flex-wrap gap-3",
        ),
        rx.cond(
            AssignmentState.import_busy,
            rx.el.p(
                "Validating and saving assignments…",
                role="status",
                class_name="mt-3 animate-pulse text-sm text-[#246D67]",
            ),
        ),
        rx.cond(
            AssignmentState.import_error != "",
            rx.el.p(
                AssignmentState.import_error,
                role="alert",
                class_name="mt-3 text-sm text-red-700",
            ),
        ),
        rx.cond(
            AssignmentState.import_message != "",
            rx.el.p(
                AssignmentState.import_message,
                role="status",
                class_name="mt-3 text-sm text-[#246D67]",
            ),
        ),
        _skipped_table(),
        _replacement_dialog(),
        class_name="mt-6 w-full min-w-0",
    )


def assignment_section() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Project assignment",
            class_name="text-xl font-semibold text-[#172B3D]",
        ),
        rx.el.p(
            "Export enrolled students’ submitted preferences as a CSV with their email and up to three project choices.",
            class_name="mt-2 text-sm text-[#667078]",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                rx.cond(
                    AssignmentState.export_busy,
                    "Exporting preferences…",
                    "Export preferences",
                ),
                type="button",
                on_click=AssignmentState.export_preferences,
                disabled=AssignmentState.busy
                | AssignmentState.replacement_open,
                class_name="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
            ),
            class_name="mt-5 flex flex-wrap gap-3",
        ),
        rx.cond(
            AssignmentState.export_busy,
            rx.el.p(
                "Preparing preferences export…",
                role="status",
                class_name="mt-3 animate-pulse text-sm text-[#246D67]",
            ),
        ),
        rx.cond(
            AssignmentState.export_error != "",
            rx.el.p(
                AssignmentState.export_error,
                role="alert",
                class_name="mt-3 text-sm text-red-700",
            ),
        ),
        _assignment_upload(),
        on_mount=AssignmentState.initialize_import,
        key=AssignmentState.import_context_key,
        custom_attrs={"aria-busy": AssignmentState.busy},
        class_name="mt-6 w-full min-w-0 rounded-2xl border border-[#E2E4DC] bg-white p-6 sm:p-8",
    )
