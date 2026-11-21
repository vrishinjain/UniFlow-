import reflex as rx

from UniFlow_.chat_services import ChatMessage, MAX_MESSAGE_LENGTH
from UniFlow_.states.chat_state import ChatState


_ACTION = "inline-flex w-fit items-center justify-center gap-2 rounded-lg bg-[#246D67] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#1C5752] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#246D67] disabled:cursor-not-allowed disabled:opacity-50"
_SECONDARY = "inline-flex w-fit items-center gap-2 rounded-lg border border-[#E2E4DC] bg-white px-3 py-2 text-sm font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246D67] disabled:opacity-60"
_SMALL_DANGER = "rounded-md bg-red-700 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:opacity-60"
_SMALL_CANCEL = "rounded-md border border-[#E2E4DC] bg-white px-2.5 py-1 text-xs font-semibold text-[#246D67] hover:bg-[#EAF3EF] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246D67]"

_COUNTER_FROM = MAX_MESSAGE_LENGTH - 200


def role_badge(message: ChatMessage) -> rx.Component:
    return rx.el.span(
        message["sender_role_label"],
        class_name=rx.cond(
            message["sender_role_label"] == "Student",
            "w-fit rounded-full border border-[#E2E4DC] bg-white px-2 py-0.5 text-[11px] font-semibold text-[#667078]",
            "w-fit rounded-full bg-[#EAF3EF] px-2 py-0.5 text-[11px] font-semibold text-[#246D67]",
        ),
    )


def delete_control(message: ChatMessage) -> rx.Component:
    return rx.cond(
        message["can_delete"],
        rx.cond(
            ChatState.confirm_delete_id == message["id"],
            rx.el.div(
                rx.el.span(
                    "Delete this message?",
                    class_name="text-xs text-[#172B3D]",
                ),
                rx.el.button(
                    rx.cond(
                        ChatState.deleting_id == message["id"],
                        "Deleting…",
                        "Delete",
                    ),
                    type="button",
                    on_click=ChatState.confirm_delete,
                    disabled=ChatState.deleting_id != "",
                    class_name=_SMALL_DANGER,
                ),
                rx.el.button(
                    "Cancel",
                    type="button",
                    on_click=ChatState.cancel_delete,
                    class_name=_SMALL_CANCEL,
                ),
                role="group",
                aria_label="Confirm message deletion",
                class_name="flex flex-wrap items-center gap-2",
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-4 w-4"),
                type="button",
                on_click=ChatState.request_delete(message["id"]),
                aria_label=f"Delete message from {message['sender_name']}",
                title="Delete message",
                class_name="shrink-0 rounded-md p-1.5 text-[#667078] hover:bg-red-50 hover:text-red-700 focus-visible:outline-2 focus-visible:outline-red-700",
            ),
        ),
        rx.fragment(),
    )


def chat_message(message: ChatMessage) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    message["sender_name"],
                    rx.cond(message["is_own"], " (you)", ""),
                    class_name="break-words text-sm font-semibold text-[#172B3D]",
                ),
                role_badge(message),
                rx.el.span(
                    message["time_label"],
                    class_name="text-xs text-[#667078]",
                ),
                class_name="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1",
            ),
            delete_control(message),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.cond(
            message["deleted"],
            rx.el.p(
                "Message deleted",
                class_name="mt-1.5 text-sm italic text-[#667078]",
            ),
            rx.el.p(
                message["body"],
                class_name="mt-1.5 whitespace-pre-wrap break-words text-sm leading-6 text-[#172B3D]",
            ),
        ),
        key=message["id"],
        class_name=rx.cond(
            message["is_own"],
            "min-w-0 shrink-0 rounded-xl border border-[#CFE3DC] bg-[#F4F9F7] px-4 py-3",
            "min-w-0 shrink-0 rounded-xl border border-[#E2E4DC] bg-white px-4 py-3",
        ),
    )


def chat_log() -> rx.Component:
    # flex-col-reverse: the first child sits at the bottom and the scroll
    # position stays pinned to the newest message, while a reader who has
    # scrolled up to older messages is not pulled back down.
    return rx.el.div(
        rx.cond(
            ChatState.loading,
            rx.el.p(
                "Loading chat…",
                role="status",
                class_name="m-auto animate-pulse text-sm text-[#667078]",
            ),
            rx.cond(
                ChatState.messages.length() == 0,
                rx.el.p(
                    "No messages yet. Say hello to your team.",
                    class_name="m-auto text-center text-sm text-[#667078]",
                ),
                rx.fragment(
                    rx.foreach(ChatState.messages_newest_first, chat_message),
                    rx.cond(
                        ChatState.has_older,
                        rx.el.button(
                            rx.cond(
                                ChatState.loading_older,
                                "Loading…",
                                "Load older messages",
                            ),
                            type="button",
                            on_click=ChatState.load_older,
                            disabled=ChatState.loading_older,
                            class_name="mx-auto shrink-0 " + _SECONDARY,
                        ),
                        rx.el.p(
                            "Start of the conversation",
                            class_name="shrink-0 text-center text-xs text-[#667078]",
                        ),
                    ),
                ),
            ),
        ),
        id="team-chat-log",
        role="log",
        aria_label="Team chat messages",
        aria_live="polite",
        tab_index=0,
        class_name="flex h-96 flex-col-reverse gap-3 overflow-y-auto rounded-xl border border-[#E2E4DC] bg-[#F7F6EF] p-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#246D67]",
    )


def chat_composer() -> rx.Component:
    return rx.el.form(
        rx.el.label(
            "Message",
            html_for="team-chat-input",
            class_name="sr-only",
        ),
        rx.el.textarea(
            id="team-chat-input",
            name="body",
            value=ChatState.draft,
            on_change=ChatState.update_draft,
            enter_key_submit=True,
            rows=2,
            max_length=MAX_MESSAGE_LENGTH,
            placeholder="Message your team…",
            disabled=ChatState.channel_id == "",
            class_name="w-full resize-y rounded-lg border border-[#E2E4DC] bg-white px-3 py-2.5 text-sm leading-6 text-[#172B3D] placeholder:text-[#8A9298] focus-visible:outline-2 focus-visible:outline-[#246D67] disabled:opacity-60",
        ),
        rx.el.div(
            rx.el.p(
                "Enter to send · Shift+Enter for a new line",
                class_name="text-xs text-[#667078]",
            ),
            rx.el.div(
                rx.cond(
                    ChatState.draft_length > _COUNTER_FROM,
                    rx.el.span(
                        f"{ChatState.draft_length}/{MAX_MESSAGE_LENGTH}",
                        aria_live="polite",
                        class_name=rx.cond(
                            ChatState.draft_length > MAX_MESSAGE_LENGTH,
                            "text-xs font-semibold text-red-700",
                            "text-xs text-[#667078]",
                        ),
                    ),
                    rx.fragment(),
                ),
                rx.el.button(
                    rx.icon("send", class_name="h-4 w-4"),
                    rx.cond(ChatState.sending, "Sending…", "Send"),
                    type="submit",
                    disabled=~ChatState.can_send,
                    class_name=_ACTION,
                ),
                class_name="flex items-center gap-3",
            ),
            class_name="mt-2 flex flex-wrap items-center justify-between gap-3",
        ),
        on_submit=ChatState.send_message,
        reset_on_submit=False,
        class_name="mt-4",
    )


def chat_alerts() -> rx.Component:
    return rx.fragment(
        rx.cond(
            ChatState.error != "",
            rx.el.div(
                rx.el.p(ChatState.error, class_name="text-sm text-red-700"),
                rx.el.button(
                    "Try again",
                    type="button",
                    on_click=ChatState.resume_chat,
                    class_name=_SECONDARY,
                ),
                role="alert",
                class_name="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 p-3",
            ),
            rx.fragment(),
        ),
        rx.cond(
            ChatState.paused & (ChatState.error == ""),
            rx.el.div(
                rx.el.p(
                    ChatState.pause_reason,
                    class_name="text-sm text-[#172B3D]",
                ),
                rx.el.button(
                    rx.icon("refresh-cw", class_name="h-4 w-4"),
                    "Resume",
                    type="button",
                    on_click=ChatState.resume_chat,
                    class_name=_SECONDARY,
                ),
                role="status",
                class_name="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#E2E4DC] bg-[#F7F6EF] p-3",
            ),
            rx.fragment(),
        ),
    )


def live_indicator() -> rx.Component:
    return rx.cond(
        ChatState.live,
        rx.el.span(
            rx.el.span(class_name="h-2 w-2 rounded-full bg-[#246D67]"),
            "Live",
            title="New messages appear automatically",
            class_name="inline-flex items-center gap-1.5 text-xs font-medium text-[#246D67]",
        ),
        rx.fragment(),
    )


def workspace_chat() -> rx.Component:
    """Team chat card shown at the top of the project workspace."""
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Team chat",
                    id="team-chat-heading",
                    class_name="text-lg font-semibold text-[#172B3D]",
                ),
                rx.el.p(
                    "Visible to everyone on this project, including course faculty.",
                    class_name="mt-1 text-sm text-[#667078]",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                live_indicator(),
                rx.el.button(
                    rx.cond(
                        ChatState.collapsed,
                        rx.icon("chevron-down", class_name="h-4 w-4"),
                        rx.icon("chevron-up", class_name="h-4 w-4"),
                    ),
                    rx.cond(ChatState.collapsed, "Show chat", "Hide chat"),
                    type="button",
                    on_click=ChatState.toggle_collapsed,
                    aria_expanded=~ChatState.collapsed,
                    aria_controls="team-chat-body",
                    class_name=_SECONDARY,
                ),
                class_name="flex shrink-0 items-center gap-3",
            ),
            class_name="flex flex-wrap items-start justify-between gap-4",
        ),
        rx.cond(
            ChatState.collapsed,
            rx.fragment(),
            rx.el.div(
                chat_alerts(),
                # When the chat failed to load, show only the error and its
                # Try again button, not an empty log and composer behind it.
                rx.cond(
                    ChatState.error != "",
                    rx.fragment(),
                    rx.fragment(
                        chat_log(),
                        rx.cond(
                            ChatState.send_error != "",
                            rx.el.p(
                                ChatState.send_error,
                                role="alert",
                                class_name="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700",
                            ),
                            rx.fragment(),
                        ),
                        chat_composer(),
                    ),
                ),
                id="team-chat-body",
                class_name="mt-5",
            ),
        ),
        on_mount=ChatState.start_chat,
        on_unmount=ChatState.stop_chat,
        aria_labelledby="team-chat-heading",
        class_name="mb-8 rounded-2xl border border-[#E2E4DC] bg-white p-6",
    )
