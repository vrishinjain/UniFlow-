import reflex as rx

import ast
import inspect
import unittest
from datetime import datetime, timezone
from pathlib import Path

from UniFlow_.chat_services import (
    MAX_MESSAGE_LENGTH,
    delete_message,
    format_time_label,
    load_older_messages,
    open_project_chat,
    poll_messages,
    post_message,
    validate_chat_id,
    validate_message_body,
    validate_since,
)


ROOT = Path(__file__).resolve().parents[1]


class ChatValidationTests(unittest.TestCase):
    """No fixtures, mocks, database connections or SQL execution."""

    def test_message_body_normalization(self):
        self.assertEqual(
            validate_message_body("  hi\r\nthere\r  "), "hi\nthere"
        )
        self.assertEqual(validate_message_body("tab\tok"), "tab\tok")
        self.assertEqual(
            len(validate_message_body("a" * MAX_MESSAGE_LENGTH)),
            MAX_MESSAGE_LENGTH,
        )

    def test_message_body_rejections(self):
        for body in (
            None,
            1,
            [],
            "",
            "   ",
            "\n\n",
            "a" * (MAX_MESSAGE_LENGTH + 1),
            "bad\x00",
            "bell\x07",
            "del\x7f",
        ):
            with self.subTest(body=repr(body)[:40]), self.assertRaises(ValueError):
                validate_message_body(body)

    def test_ids_and_cursor(self):
        self.assertEqual(validate_chat_id("12"), 12)
        for value in (True, 0, -1, "0", "1.0", "١", "9" * 20, None, ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_chat_id(value)
        self.assertTrue(validate_since("2026-11-20T18:31:00.123+00:00"))
        for value in (None, "", "yesterday", "2026-11-20T18:31:00", "x" * 50):
            with self.subTest(since=value), self.assertRaises(ValueError):
                validate_since(value)

    def test_time_label_is_portable(self):
        label = format_time_label(
            datetime(2026, 11, 20, 23, 5, tzinfo=timezone.utc)
        )
        self.assertIn(label, ("Nov 20, 6:05 PM", "Nov 20, 11:05 PM"))

    def test_services_reject_bad_input_before_connecting(self):
        # These calls fail in pure validation, before any engine is accessed.
        with self.assertRaises(ValueError):
            post_message(1, 1, "   ")
        with self.assertRaises(ValueError):
            post_message(0, 1, "hi")
        with self.assertRaises(ValueError):
            delete_message(1, 1, 0)
        with self.assertRaises(ValueError):
            poll_messages(1, 1, 0, "not-a-time")
        with self.assertRaises(ValueError):
            load_older_messages(1, 1, 0)
        with self.assertRaises(ValueError):
            open_project_chat(1, 0)

    def test_public_signatures(self):
        expected = {
            open_project_chat: ["actor_id", "project_id"],
            load_older_messages: ["actor_id", "channel_id", "before_id"],
            poll_messages: ["actor_id", "channel_id", "after_id", "since"],
            post_message: ["actor_id", "channel_id", "body"],
            delete_message: ["actor_id", "channel_id", "message_id"],
        }
        for function, parameters in expected.items():
            with self.subTest(function=function.__name__):
                self.assertEqual(
                    list(inspect.signature(function).parameters), parameters
                )


class ChatStructureTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "UniFlow_/chat_services.py").read_text()
        tree = ast.parse(self.source)
        self.functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }

    def segment(self, name: str) -> str:
        return ast.get_source_segment(self.source, self.functions[name])

    def test_every_service_authorizes_on_its_connection(self):
        for name in (
            "load_older_messages",
            "poll_messages",
            "post_message",
            "delete_message",
        ):
            with self.subTest(name=name):
                self.assertIn(
                    "authorize_channel(connection, actor_id, channel_id)",
                    self.segment(name),
                )
        opening = self.segment("open_project_chat")
        self.assertLess(
            opening.index("authorize_workspace(connection, actor_id, project_id)"),
            opening.index("SQL_ENSURE_PROJECT_CHANNEL"),
            "Members must be authorized before a channel is created.",
        )

    def test_writes_use_transactions(self):
        for name in ("open_project_chat", "post_message", "delete_message"):
            with self.subTest(name=name):
                self.assertIn("_get_engine().begin()", self.segment(name))

    def test_sender_comes_from_session_not_browser(self):
        post = self.segment("post_message")
        self.assertIn('"actor_id": actor_id', post)
        self.assertNotIn("sender_id", post)

    def test_deleted_text_is_never_selected(self):
        self.assertIn(
            "CASE WHEN m.deleted_at IS NULL THEN m.body ELSE '' END",
            self.source,
        )

    def test_project_channel_uniqueness_in_migration(self):
        migration = (ROOT / "db/migrations/chatdev.sql").read_text()
        self.assertIn("chat_channel_one_per_project_idx", migration)
        self.assertIn("BETWEEN 1 AND 2000", migration)
        self.assertNotIn("DROP TABLE public.users", migration)

    def test_chat_is_between_team_and_milestones(self):
        workspace = (ROOT / "UniFlow_/components/workspace.py").read_text()
        team = workspace.index('"Project team"')
        chat = workspace.index("workspace_chat()")
        milestones = workspace.index("milestones_section()")
        self.assertLess(team, chat)
        self.assertLess(chat, milestones)

    def test_chat_state_cleared_on_sign_in_and_out(self):
        login = (ROOT / "UniFlow_/states/login_state.py").read_text()
        self.assertIn("ChatState", login)


if __name__ == "__main__":
    unittest.main()
