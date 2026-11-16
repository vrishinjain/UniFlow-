import reflex as rx

from UniFlow_.components.student import _page
from UniFlow_.courses_services import EnrolledStudent
from UniFlow_.preference_services import (
    CoursePreferenceForm,
    StudentRanking,
    PreferenceSlot,
    ProjectOption,
)
from UniFlow_.states.preference_state import (
    CoursePreferencesState,
    StudentPreferencesState,
)
from UniFlow_.components.dashboard_layout import page_header

_BUTTON = "inline-flex w-fit items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67] disabled:cursor-not-allowed disabled:opacity-60"
_OUTLINE = "inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-4 py-2.5 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67] disabled:cursor-not-allowed disabled:opacity-60"
_CARD = "w-full min-w-0 rounded-2xl border border-[#E2E4DC] bg-white p-6 sm:p-8"


# ------------------------------------------------- faculty panel (#95) --


def _missing_student(student: EnrolledStudent) -> rx.Component:
    return rx.el.li(
        rx.el.span(student["full_name"], class_name="font-medium text-[#172B3D]"),
        rx.el.span(f" · {student['email']}", class_name="break-all text-[#667078]"),
        key=student["id"],
        class_name="py-2 text-sm",
    )


def _choice_cell(title) -> rx.Component:
    return rx.el.td(
        rx.cond(title != "", title, "—"),
        class_name="px-4 py-3 text-sm text-[#4A5560]",
    )


def _ranking_row(row: StudentRanking) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(row["full_name"], class_name="font-medium text-[#172B3D]"),
            rx.el.p(row["email"], class_name="break-all text-xs text-[#667078]"),
            class_name="px-4 py-3 text-sm",
        ),
        _choice_cell(row["choice_1"]),
        _choice_cell(row["choice_2"]),
        _choice_cell(row["choice_3"]),
        key=row["id"],
        class_name="border-t border-[#E2E4DC] bg-white even:bg-[#F7F6EF]",
    )


def _rankings_table() -> rx.Component:
    return rx.el.div(
        rx.el.h3(
            "Submitted rankings",
            class_name="mt-6 text-sm font-semibold text-[#172B3D]",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th("Student", scope="col", class_name="px-4 py-3 text-left"),
                        rx.el.th("1st choice", scope="col", class_name="px-4 py-3 text-left"),
                        rx.el.th("2nd choice", scope="col", class_name="px-4 py-3 text-left"),
                        rx.el.th("3rd choice", scope="col", class_name="px-4 py-3 text-left"),
                    ),
                    class_name="bg-[#F7F6EF] text-xs font-semibold text-[#4A5560]",
                ),
                rx.el.tbody(rx.foreach(CoursePreferencesState.rankings, _ranking_row)),
                class_name="w-full min-w-[640px] table-auto",
            ),
            class_name="mt-2 w-full overflow-x-auto rounded-xl border border-[#E2E4DC]",
        ),
    )


def course_preferences_panel() -> rx.Component:
    """Shown on the faculty course page, under the enrolled students."""
    s = CoursePreferencesState
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Project preferences",
                    class_name="text-xl font-semibold text-[#172B3D]",
                ),
                rx.el.p(
                    rx.cond(
                        s.preferences_open,
                        "Open: students in this course can rank projects.",
                        "Closed: students can't submit or change their rankings.",
                    ),
                    class_name="mt-2 text-sm text-[#667078]",
                ),
            ),
            rx.el.button(
                rx.cond(s.preferences_open, "Close preferences", "Open preferences"),
                type="button",
                on_click=s.toggle_preferences,
                disabled=s.busy | (s.loaded == False),
                class_name=rx.cond(s.preferences_open, _OUTLINE, _BUTTON),
            ),
            class_name="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
        ),
        rx.cond(
            s.error != "",
            rx.el.p(s.error, role="alert", class_name="mt-4 text-sm text-red-700"),
        ),
        rx.cond(
            s.loaded,
            rx.el.div(
                rx.el.p(
                    f"{s.submitted} of {s.enrolled} students have submitted.",
                    class_name="text-sm font-medium text-[#172B3D]",
                ),
                rx.cond(s.rankings.length() > 0, _rankings_table()),
                rx.cond(
                    s.missing.length() > 0,
                    rx.el.div(
                        rx.el.h3(
                            "Not submitted yet",
                            class_name="mt-4 text-sm font-semibold text-[#172B3D]",
                        ),
                        rx.el.ul(
                            rx.foreach(s.missing, _missing_student),
                            class_name="mt-1 max-h-60 divide-y divide-[#E2E4DC] overflow-y-auto",
                        ),
                    ),
                ),
                class_name="mt-5",
            ),
            rx.el.p(
                "Loading preference status…",
                role="status",
                class_name="mt-5 text-sm text-[#667078]",
            ),
        ),
        class_name=f"mt-6 {_CARD}",
    )


# ------------------------------------------------- student page (#94) --


def _option(project: ProjectOption) -> rx.Component:
    return rx.el.option(project["title"], value=project["id"])


def _slot_select(form: CoursePreferenceForm, slot: PreferenceSlot) -> rx.Component:
    # No id on purpose: Reflex makes a ref for every id, and ids built inside
    # rx.foreach break form submission. The label wraps the select instead.
    return rx.el.label(
        rx.el.span(
            slot["label"],
            class_name="mb-1 block text-sm font-medium text-[#172B3D]",
        ),
        rx.el.select(
            rx.el.option("Choose a project", value=""),
            rx.foreach(form["options"], _option),
            name=f"choice_{slot['rank']}",
            required=True,
            default_value=slot["selected"],
            key=f"{StudentPreferencesState.form_revision}-{form['course_id']}-{slot['rank']}",
            disabled=StudentPreferencesState.saving_course_id != "",
            class_name="w-full rounded-lg border border-[#BFCFC9] bg-white px-3 py-2.5 text-sm text-[#172B3D] focus-visible:outline-2 focus-visible:outline-[#246D67]",
        ),
        class_name="block",
    )


def _slot_readonly(slot: PreferenceSlot) -> rx.Component:
    return rx.el.li(
        rx.el.span(f"{slot['label']}: ", class_name="font-medium text-[#172B3D]"),
        rx.cond(
            slot["selected_title"] != "",
            rx.el.span(slot["selected_title"], class_name="text-[#4A5560]"),
            rx.el.span("—", class_name="text-[#667078]"),
        ),
        class_name="py-1.5 text-sm",
    )


def _course_form(form: CoursePreferenceForm) -> rx.Component:
    return rx.el.section(
        rx.el.p(
            form["course_label"],
            class_name="text-xs font-semibold uppercase tracking-wide text-[#28766F]",
        ),
        rx.cond(
            form["slot_count"] == 0,
            rx.el.p(
                "No projects have been shared with this course yet.",
                class_name="mt-3 text-sm text-[#667078]",
            ),
            rx.cond(
                form["preferences_open"],
                rx.el.form(
                    rx.el.input(
                        type="hidden",
                        name="course_id",
                        value=form["course_id"],
                    ),
                    rx.el.p(
                        "Rank the projects you'd most like to work on. Each project can only be picked once.",
                        class_name="mt-2 text-sm text-[#667078]",
                    ),
                    rx.el.div(
                        rx.foreach(
                            form["slots"], lambda slot: _slot_select(form, slot)
                        ),
                        class_name="mt-4 grid gap-4 sm:grid-cols-3",
                    ),
                    rx.el.button(
                        rx.cond(
                            StudentPreferencesState.saving_course_id
                            == form["course_id"],
                            "Saving…",
                            rx.cond(
                                form["submitted"],
                                "Update preferences",
                                "Submit preferences",
                            ),
                        ),
                        type="submit",
                        disabled=StudentPreferencesState.saving_course_id != "",
                        class_name=f"mt-5 {_BUTTON}",
                    ),
                    on_submit=StudentPreferencesState.save_preferences,
                ),
                rx.el.div(
                    rx.el.p(
                        "Preferences are closed for this course.",
                        class_name="mt-2 text-sm font-medium text-[#172B3D]",
                    ),
                    rx.cond(
                        form["submitted"],
                        rx.el.ul(
                            rx.foreach(form["slots"], _slot_readonly),
                            class_name="mt-3",
                        ),
                        rx.el.p(
                            "You didn't submit a ranking.",
                            class_name="mt-2 text-sm text-[#667078]",
                        ),
                    ),
                ),
            ),
        ),
        key=form["course_id"],
        class_name=_CARD,
    )


def student_preferences_portal() -> rx.Component:
    s = StudentPreferencesState
    return _page(
        "/student/preferences",
        rx.el.div(
            page_header("Student", "Project preferences"),
            rx.cond(
                s.message != "",
                rx.el.p(
                    s.message,
                    role="status",
                    class_name="mb-6 rounded-lg border border-[#BFCFC9] bg-[#F0F6F3] p-4 text-sm text-[#1C5752]",
                ),
            ),
            rx.cond(
                s.error != "",
                rx.el.p(
                    s.error,
                    role="alert",
                    class_name="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700",
                ),
            ),
            rx.cond(
                s.loading | (s.authorized == False),
                rx.el.p(
                    "Loading preferences…",
                    role="status",
                    class_name="py-12 text-center text-sm text-[#667078]",
                ),
                rx.cond(
                    s.forms.length() == 0,
                    rx.el.p(
                        "You aren't enrolled in any course yet.",
                        class_name=f"{_CARD} text-center text-sm text-[#667078]",
                    ),
                    rx.el.div(
                        rx.foreach(s.forms, _course_form),
                        class_name="flex flex-col gap-6",
                    ),
                ),
            ),
        ),
    )
