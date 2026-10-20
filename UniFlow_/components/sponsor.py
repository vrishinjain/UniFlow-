import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
    page_header,
)
from UniFlow_.states.sponsor_state import SponsorState

# Sidebar options for this role. The first item is the dashboard home.
SPONSOR_NAV = [
    NavItem("Home", "house", "/sponsor", "Overview of your sponsor workspace."),
    NavItem(
        "Submit project",
        "file-plus",
        "/sponsor/submit",
        "Propose a new project with a description and files.",
    ),
    NavItem(
        "My projects",
        "folder",
        "/sponsor/projects",
        "Track the projects you have submitted.",
    ),
]


def _page(route: str, content: rx.Component) -> rx.Component:
    return dashboard_layout(
        role_label="Sponsor",
        nav=SPONSOR_NAV,
        active=route,
        authorized=SponsorState.authorized,
        content=content,
    )


def sponsor_home() -> rx.Component:
    return _page(
        "/sponsor", home_content("Sponsor", SPONSOR_NAV, SponsorState.full_name)
    )


def sponsor_submit() -> rx.Component:
    # T-4 / T-5 (Anthony): replace coming_soon with the submission form.
    return _page("/sponsor/submit", coming_soon("Sponsor", SPONSOR_NAV[1]))


def _project_row(project) -> rx.Component:
    return rx.el.tr(
        rx.el.th(
            project["title"],
            scope="row",
            class_name="break-words px-6 py-4 text-left text-sm font-semibold text-[#172B3D]",
        ),
        rx.el.td(
            rx.el.span(
                project["status"],
                class_name="inline-flex w-fit rounded-full bg-[#EAF3EF] px-3 py-1 text-xs font-semibold text-[#246D67]",
            ),
            class_name="px-6 py-4",
        ),
        rx.el.td(
            rx.el.time(
                project["submitted_date"],
                custom_attrs={"datetime": project["submitted_at"]},
                class_name="whitespace-nowrap text-sm text-[#4A5560]",
            ),
            class_name="px-6 py-4",
        ),
        key=project["id"],
        class_name="border-t border-[#E2E4DC] bg-white even:bg-[#FBFCF9] hover:bg-[#F0F6F3]",
    )


def _projects_table() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.table(
                rx.el.caption(
                    "Your submitted projects, newest first",
                    class_name="sr-only",
                ),
                rx.el.thead(
                    rx.el.tr(
                        rx.el.th(
                            rx.el.span(
                                rx.icon("file-text", class_name="h-4 w-4"),
                                "Title",
                                class_name="flex items-center gap-2",
                            ),
                            scope="col",
                            class_name="w-1/2 px-6 py-4 text-left text-xs font-semibold text-[#4A5560]",
                        ),
                        rx.el.th(
                            rx.el.span(
                                rx.icon("circle-check", class_name="h-4 w-4"),
                                "Status",
                                class_name="flex items-center gap-2",
                            ),
                            scope="col",
                            class_name="px-6 py-4 text-left text-xs font-semibold text-[#4A5560]",
                        ),
                        rx.el.th(
                            rx.el.span(
                                rx.icon("calendar", class_name="h-4 w-4"),
                                "Submitted date",
                                class_name="flex items-center gap-2 whitespace-nowrap",
                            ),
                            scope="col",
                            class_name="px-6 py-4 text-left text-xs font-semibold text-[#4A5560]",
                        ),
                        class_name="bg-[#FBFCF9]",
                    ),
                ),
                rx.el.tbody(rx.foreach(SponsorState.projects, _project_row)),
                class_name="table-auto w-full min-w-[540px] bg-white text-[#172B3D]",
            ),
            tab_index=0,
            aria_label="My projects table; scroll horizontally on small screens",
            class_name="w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#246D67]",
        ),
        class_name="w-full overflow-hidden rounded-2xl border border-[#E2E4DC] bg-white",
    )


def sponsor_projects() -> rx.Component:
    return _page(
        "/sponsor/projects",
        rx.el.div(
            page_header(
                "Sponsor",
                "My projects",
                "Track the projects you have submitted.",
            ),
            rx.match(
                SponsorState.projects_view,
                (
                    "loading",
                    rx.el.div(
                        rx.icon(
                            "loader-circle",
                            class_name="h-5 w-5 animate-spin text-[#246D67]",
                        ),
                        rx.el.p(
                            "Loading projects…",
                            class_name="text-sm text-[#4A5560]",
                        ),
                        role="status",
                        class_name="flex items-center justify-center gap-3 rounded-2xl border border-[#E2E4DC] bg-white px-6 py-16",
                    ),
                ),
                (
                    "error",
                    rx.el.div(
                        rx.icon(
                            "circle-alert",
                            class_name="mx-auto h-6 w-6 text-red-600",
                        ),
                        rx.el.p(
                            SponsorState.projects_error,
                            role="alert",
                            class_name="mt-3 text-sm text-[#172B3D]",
                        ),
                        rx.el.button(
                            rx.icon("refresh-cw", class_name="h-4 w-4"),
                            "Try again",
                            type="button",
                            on_click=SponsorState.load_my_projects,
                            class_name="mx-auto mt-5 flex items-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-4 py-2 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67]",
                        ),
                        class_name="rounded-2xl border border-[#E2E4DC] bg-white px-6 py-12 text-center",
                    ),
                ),
                (
                    "empty",
                    rx.el.div(
                        rx.icon(
                            "folder",
                            class_name="mx-auto h-8 w-8 text-[#246D67]",
                        ),
                        rx.el.p(
                            "No projects yet",
                            class_name="mt-4 text-base font-semibold text-[#172B3D]",
                        ),
                        role="status",
                        class_name="rounded-2xl border border-[#E2E4DC] bg-white px-6 py-16 text-center",
                    ),
                ),
                _projects_table(),
            ),
            class_name="w-full",
        ),
    )


# (page function, route, browser tab title). UniFlow_.py registers each one
# with SponsorState's on_load check, so every page is protected the same way.
SPONSOR_PAGES = [
    (sponsor_home, "/sponsor", "Sponsor Dashboard"),
    (sponsor_submit, "/sponsor/submit", "Submit project"),
    (sponsor_projects, "/sponsor/projects", "My projects"),
]
