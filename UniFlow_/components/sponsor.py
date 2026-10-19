import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.sponsor_state import SponsorState
from UniFlow_.components.project_submission import project_submission

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
        "/sponsor",
        rx.el.div(
            rx.cond(
                SponsorState.success_message != "",
                rx.el.div(
                    rx.icon(
                        "circle-check",
                        class_name="h-5 w-5 shrink-0 text-[#246D67]",
                    ),
                    rx.el.p(
                        SponsorState.success_message,
                        class_name="text-sm font-medium text-[#246D67]",
                    ),
                    role="status",
                    custom_attrs={"aria-live": "polite"},
                    class_name="mb-6 flex items-center gap-3 rounded-xl border border-[#CDE1D7] bg-[#EAF3EF] p-4",
                ),
                rx.fragment(),
            ),
            home_content("Sponsor", SPONSOR_NAV, SponsorState.full_name),
        ),
    )


def sponsor_submit() -> rx.Component:
    return _page("/sponsor/submit", project_submission())


def sponsor_projects() -> rx.Component:
    # T-6 (Anthony): replace coming_soon with the My projects list.
    return _page("/sponsor/projects", coming_soon("Sponsor", SPONSOR_NAV[2]))


# (page function, route, browser tab title). UniFlow_.py registers each one
# with SponsorState's on_load check, so every page is protected the same way.
SPONSOR_PAGES = [
    (sponsor_home, "/sponsor", "Sponsor Dashboard"),
    (sponsor_submit, "/sponsor/submit", "Submit project"),
    (sponsor_projects, "/sponsor/projects", "My projects"),
]
