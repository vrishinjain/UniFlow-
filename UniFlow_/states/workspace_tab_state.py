import reflex as rx


WORKSPACE_TABS = ("board", "chat")


class WorkspaceTabState(rx.State):
    """Which workspace tab is open: the sprint board (default) or the team chat.

    The chat is only mounted while its tab is open, so it only polls the
    database for new messages while someone is looking at it.
    """

    tab: str = "board"

    @rx.event
    def set_tab(self, tab: str):
        if tab in WORKSPACE_TABS:
            self.tab = tab

    def _clear_access(self):
        """Called by LoginState on sign-in and sign-out."""
        self.tab = "board"
