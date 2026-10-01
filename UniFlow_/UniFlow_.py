import reflex as rx

from UniFlow_.states.student_roster_state import StudentRosterState, StudentRow


def student_row(student: StudentRow, index: int) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            index + 1,
            class_name="w-24 border-b border-[#E9E7E0] px-5 py-4 text-sm font-medium tabular-nums text-[#74828C] sm:px-8",
        ),
        rx.el.th(
            student["name"],
            scope="row",
            class_name="border-b border-[#E9E7E0] px-5 py-4 text-left text-sm font-semibold text-[#142E3F] sm:px-8",
        ),
        key=student["id"],
        class_name="bg-white transition-colors hover:bg-[#F7FAF8] last:[&>td]:border-b-0 last:[&>th]:border-b-0",
    )


def roster_table() -> rx.Component:
    return rx.el.div(
        rx.el.table(
            rx.el.caption(
                "Student roster, ordered by student ID", class_name="sr-only"
            ),
            rx.el.thead(
                rx.el.tr(
                    rx.el.th(
                        "No.",
                        scope="col",
                        class_name="w-24 border-b border-[#E7E5DD] bg-[#F8F8F4] px-5 py-4 text-left text-xs font-semibold uppercase tracking-[0.14em] text-[#566976] sm:px-8",
                    ),
                    rx.el.th(
                        "Student name",
                        scope="col",
                        class_name="border-b border-[#E7E5DD] bg-[#F8F8F4] px-5 py-4 text-left text-xs font-semibold uppercase tracking-[0.14em] text-[#566976] sm:px-8",
                    ),
                ),
            ),
            rx.el.tbody(rx.foreach(StudentRosterState.students, student_row)),
            class_name="table-auto w-full border-collapse",
        ),
        class_name="w-full overflow-x-auto rounded-xl border border-[#E5E4DC] bg-white",
    )


def roster_content() -> rx.Component:
    return rx.el.div(
        rx.cond(
            StudentRosterState.loading,
            rx.el.div(
                rx.el.div(
                    class_name="h-5 w-36 animate-pulse rounded bg-[#E9EDE9]"
                ),
                rx.el.div(
                    class_name="h-5 w-52 animate-pulse rounded bg-[#E9EDE9]"
                ),
                rx.el.div(
                    class_name="h-5 w-44 animate-pulse rounded bg-[#E9EDE9]"
                ),
                role="status",
                aria_label="Loading student roster",
                class_name="flex flex-col gap-8 rounded-xl border border-[#E5E4DC] bg-white px-8 py-10",
            ),
            rx.cond(
                StudentRosterState.error != "",
                rx.el.div(
                    rx.el.p(
                        "Unable to load roster",
                        class_name="font-semibold text-[#142E3F]",
                    ),
                    rx.el.p(
                        StudentRosterState.error,
                        class_name="mt-2 text-sm leading-6 text-[#526674]",
                    ),
                    role="alert",
                    class_name="rounded-xl border border-[#E5E4DC] bg-white px-6 py-8 sm:px-8",
                ),
                rx.cond(
                    StudentRosterState.students.length() == 0,
                    rx.el.div(
                        rx.el.p(
                            "No students on record",
                            class_name="font-semibold text-[#142E3F]",
                        ),
                        rx.el.p(
                            "The roster is currently empty.",
                            class_name="mt-2 text-sm text-[#526674]",
                        ),
                        class_name="rounded-xl border border-[#E5E4DC] bg-white px-6 py-12 text-center",
                    ),
                    roster_table(),
                ),
            ),
        ),
        aria_live="polite",
        class_name="w-full",
    )


def index() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            rx.el.header(
                rx.el.div(
                    rx.el.span(
                        "A",
                        aria_hidden="true",
                        class_name="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded border border-[#167E79] text-xs font-bold leading-none text-[#167E79]",
                    ),
                    rx.el.span(
                        "ACADEMIC RECORDS",
                        class_name="text-xs font-bold tracking-[0.18em] text-[#142E3F]",
                    ),
                    class_name="flex items-center gap-3",
                ),
                class_name="border-b border-[#E5E4DC] pb-6",
            ),
            rx.el.section(
                rx.el.p(
                    "REGISTRAR  /  STUDENT DIRECTORY",
                    class_name="text-xs font-bold tracking-[0.18em] text-[#167E79]",
                ),
                rx.el.h1(
                    "Student roster",
                    class_name="mt-5 text-4xl font-semibold tracking-[-0.04em] text-[#142E3F] sm:text-5xl",
                ),
                rx.el.p(
                    "A complete list of students currently on record.",
                    class_name="mt-4 text-base leading-7 text-[#526674]",
                ),
                class_name="pt-14 pb-12 sm:pt-20 sm:pb-16",
            ),
            rx.el.section(
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "STUDENTS ON RECORD",
                            class_name="text-xs font-bold tracking-[0.14em] text-[#667884]",
                        ),
                        rx.el.div(
                            rx.el.span(
                                rx.cond(
                                    StudentRosterState.loading
                                    | (StudentRosterState.error != ""),
                                    "—",
                                    StudentRosterState.students.length(),
                                ),
                                class_name="text-3xl font-semibold tabular-nums tracking-tight text-[#142E3F]",
                            ),
                            rx.el.span(
                                "total students",
                                class_name="text-sm text-[#667884]",
                            ),
                            class_name="mt-2 flex items-baseline gap-3",
                        ),
                    ),
                    rx.el.button(
                        rx.el.span(
                            "↻",
                            aria_hidden="true",
                            class_name="inline-flex h-4 w-4 shrink-0 items-center justify-center text-lg font-medium leading-none",
                        ),
                        "Refresh roster",
                        type="button",
                        disabled=StudentRosterState.loading,
                        on_click=StudentRosterState.load_students,
                        class_name="inline-flex w-fit items-center justify-center gap-2 rounded-lg border border-[#CAD8D3] bg-white px-4 py-2.5 text-sm font-semibold text-[#166B68] transition-colors hover:border-[#167E79] hover:bg-[#EDF6F3] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#167E79] disabled:cursor-not-allowed disabled:opacity-50",
                    ),
                    class_name="mb-7 flex flex-wrap items-end justify-between gap-6",
                ),
                roster_content(),
                aria_label="Student roster",
                class_name="pb-20",
            ),
            class_name="mx-auto w-full max-w-4xl px-5 pt-7 sm:px-10 sm:pt-10",
        ),
        class_name="min-h-dvh w-full bg-[#F7F6F1] font-['Inter'] text-[#142E3F]",
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
app.add_page(
    index,
    route="/",
    on_load=StudentRosterState.load_students,
    title="Student Roster | Academic Records",
)
