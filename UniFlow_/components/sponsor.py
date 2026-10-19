import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.sponsor_state import SponsorState

# Sidebar options for this role. The first item is the dashboard home.
SPONSOR_NAV = [
    NavItem("Home", "house", "/sponsor", "Overview of your sponsor workspace."),
    NavItem("Submit project", "file-plus", "/sponsor/submit", "Propose a new project with a description and files."),
    NavItem("My projects", "folder", "/sponsor/projects", "Track the projects you have submitted."),
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
    return _page("/sponsor", home_content("Sponsor", SPONSOR_NAV, SponsorState.full_name))


def sponsor_submit() -> rx.Component:
    # T-4 / T-5 (Anthony): replace coming_soon with the submission form.
    return _page("/sponsor/submit", coming_soon("Sponsor", SPONSOR_NAV[1]))


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
