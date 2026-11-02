"""Shared dashboard shell used by every role: sidebar, top bar and main area.

How to use it for a new page:
    1. Add a NavItem to the role's *_NAV list (in that role's component file).
    2. Write a function that returns the page content (start with page_header()).
    3. Add it to the role's *_PAGES list. UniFlow_.py registers it automatically.
"""

from typing import NamedTuple

import reflex as rx

from UniFlow_.states.login_state import LoginState


class NavItem(NamedTuple):
    label: str
    icon: str
    href: str
    description: str = ""


_ACTIVE_LINK = "flex items-center gap-3 rounded-lg bg-[#EAF3EF] px-3 py-2.5 text-sm font-semibold text-[#1C5752]"
_LINK = "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[#4A5560] transition-colors hover:bg-[#F0F2EC] hover:text-[#172B3D]"
_ACTIVE_CHIP = "flex shrink-0 items-center gap-2 rounded-full bg-[#246D67] px-3.5 py-2 text-sm font-semibold text-white"
_CHIP = "flex shrink-0 items-center gap-2 rounded-full border border-[#D9DEDC] bg-white px-3.5 py-2 text-sm font-medium text-[#4A5560]"


def _sidebar_link(item: NavItem, active: str) -> rx.Component:
    is_active = item.href == active
    return rx.el.a(
        rx.icon(item.icon, class_name="h-4 w-4 shrink-0"),
        item.label,
        href=item.href,
        custom_attrs={"aria-current": "page"} if is_active else {},
        class_name=_ACTIVE_LINK if is_active else _LINK,
    )


def _mobile_link(item: NavItem, active: str) -> rx.Component:
    is_active = item.href == active
    return rx.el.a(
        rx.icon(item.icon, class_name="h-4 w-4"),
        item.label,
        href=item.href,
        class_name=_ACTIVE_CHIP if is_active else _CHIP,
    )


def _sidebar(role_label: str, nav: list[NavItem], active: str) -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.el.p(
                "UniFlow",
                class_name="text-xl font-semibold tracking-tight text-[#172B3D]",
            ),
            rx.el.p(
                f"{role_label} portal",
                class_name="mt-1 text-xs font-medium tracking-wide text-[#667078]",
            ),
            class_name="px-3 pb-6",
        ),
        rx.el.nav(
            *[_sidebar_link(item, active) for item in nav],
            class_name="flex flex-col gap-1",
            custom_attrs={"aria-label": f"{role_label} navigation"},
        ),
        class_name="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-[#E2E4DC] bg-white px-3 py-7 md:flex",
    )


def _top_bar(role_label: str, nav: list[NavItem], active: str) -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "UniFlow",
                    class_name="text-lg font-semibold tracking-tight text-[#172B3D] md:hidden",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p(
                        LoginState.full_name,
                        class_name="truncate text-sm font-semibold text-[#172B3D]",
                    ),
                    rx.el.p(role_label, class_name="text-xs text-[#667078]"),
                    class_name="hidden min-w-0 text-right sm:block",
                ),
                rx.el.button(
                    rx.icon("log-out", class_name="h-4 w-4"),
                    "Sign out",
                    type="button",
                    on_click=LoginState.sign_out,
                    class_name="flex items-center gap-2 rounded-lg border border-[#BFCFC9] bg-white px-3.5 py-2 text-sm font-semibold text-[#246D67] hover:bg-[#F0F6F3] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#28766F]",
                ),
                class_name="flex items-center gap-4",
            ),
            class_name="flex items-center justify-between gap-4 px-5 py-4 sm:px-8",
        ),
        # Small screens: the sidebar is hidden, so show the links as a scrollable row.
        rx.el.nav(
            *[_mobile_link(item, active) for item in nav],
            class_name="flex gap-2 overflow-x-auto px-5 pb-4 md:hidden",
        ),
        class_name="border-b border-[#E2E4DC] bg-white",
    )


def dashboard_layout(
    *,
    role_label: str,
    nav: list[NavItem],
    active: str,
    authorized,
    content: rx.Component,
) -> rx.Component:
    """Wrap a page's content in the shared shell. `active` is the current route."""
    return rx.el.div(
        _sidebar(role_label, nav, active),
        rx.el.div(
            _top_bar(role_label, nav, active),
            rx.el.main(
                rx.cond(
                    authorized,
                    content,
                    rx.el.p(
                        "Verifying access…",
                        role="status",
                        custom_attrs={"aria-live": "polite"},
                        class_name="py-24 text-center text-sm text-[#667078]",
                    ),
                ),
                class_name="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-10",
            ),
            class_name="flex min-w-0 flex-1 flex-col",
        ),
        class_name="flex min-h-dvh w-full bg-[#F7F6EF] font-['Inter',sans-serif] text-[#172B3D]",
    )


def page_header(eyebrow: str, title, description: str = "") -> rx.Component:
    return rx.el.section(
        rx.el.p(
            eyebrow.upper(),
            class_name="text-[11px] font-semibold tracking-[0.18em] text-[#28766F]",
        ),
        rx.el.h1(
            title,
            class_name="mt-3 break-words text-3xl font-semibold tracking-tight text-[#172B3D]",
        ),
        rx.el.p(description, class_name="mt-3 max-w-2xl text-sm leading-6 text-[#667078]")
        if description
        else rx.fragment(),
        class_name="pb-8",
    )


def home_content(role_label: str, nav: list[NavItem], full_name) -> rx.Component:
    """Welcome heading plus a card for every other section of the dashboard."""
    cards = [
        rx.el.a(
            rx.icon(item.icon, class_name="h-6 w-6 text-[#246D67]"),
            rx.el.h2(item.label, class_name="mt-4 text-base font-semibold text-[#172B3D]"),
            rx.el.p(item.description, class_name="mt-1 text-sm leading-6 text-[#667078]"),
            href=item.href,
            class_name="block rounded-2xl border border-[#E2E4DC] bg-white p-6 transition-colors hover:border-[#BFCFC9] hover:bg-[#FBFCF9]",
        )
        for item in nav[1:]
    ]
    return rx.el.div(
        page_header(f"{role_label} dashboard", f"Welcome, {full_name}"),
        rx.el.div(*cards, class_name="grid gap-4 sm:grid-cols-2"),
    )


def coming_soon(eyebrow: str, item: NavItem) -> rx.Component:
    """Placeholder content for a section that a later task will build."""
    return rx.el.div(
        page_header(eyebrow, item.label, item.description),
        rx.el.div(
            rx.icon("clock", class_name="mx-auto h-8 w-8 text-[#28766F]"),
            rx.el.h2(
                "Coming soon",
                class_name="mt-4 text-base font-semibold text-[#172B3D]",
            ),
            rx.el.p(
                "This section is being built and will be available in an upcoming release.",
                class_name="mt-2 text-sm text-[#667078]",
            ),
            class_name="rounded-2xl border border-dashed border-[#D9DEDC] bg-white px-6 py-16 text-center",
        ),
    )
