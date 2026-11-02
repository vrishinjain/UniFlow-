import reflex as rx

from UniFlow_.components.dashboard_layout import (
    NavItem,
    coming_soon,
    dashboard_layout,
    home_content,
)
from UniFlow_.states.program_admin_state import ProgramAdminState

# Sidebar options for this role. The first item is the dashboard home.
PROGRAM_ADMIN_NAV = [
    NavItem("Home", "house", "/programadmin", "Overview of your program administration workspace."),
    NavItem("All projects", "folder-open", "/programadmin/projects", "See every project in the program and its status."),
    NavItem("Users", "users", "/programadmin/users", "See the people in your program."),
]


def _page(route: str, content: rx.Component) -> rx.Component:
    return dashboard_layout(
        role_label="Program admin",
        nav=PROGRAM_ADMIN_NAV,
        active=route,
        authorized=ProgramAdminState.authorized,
        content=content,
    )


def program_admin_home() -> rx.Component:
    return _page("/programadmin", home_content("Program admin", PROGRAM_ADMIN_NAV, ProgramAdminState.full_name))


def program_admin_projects() -> rx.Component:
    # Later sprint.
    return _page("/programadmin/projects", coming_soon("Program admin", PROGRAM_ADMIN_NAV[1]))


def program_admin_users() -> rx.Component:
    # Later sprint.
    return _page("/programadmin/users", coming_soon("Program admin", PROGRAM_ADMIN_NAV[2]))


# (page function, route, browser tab title). UniFlow_.py registers each one
# with ProgramAdminState's on_load check, so every page is protected the same way.
PROGRAM_ADMIN_PAGES = [
    (program_admin_home, "/programadmin", "Program admin Dashboard"),
    (program_admin_projects, "/programadmin/projects", "All projects"),
    (program_admin_users, "/programadmin/users", "Users"),
]
