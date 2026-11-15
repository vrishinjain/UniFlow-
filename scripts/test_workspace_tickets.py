import reflex as rx

import ast
import inspect
import unittest
from pathlib import Path

from UniFlow_.workspace_services import (
    create_ticket,
    update_ticket,
    delete_ticket,
    move_ticket,
    validate_ticket_fields,
    validate_ticket_id,
)


ROOT = Path(__file__).resolve().parents[1]


class TicketValidationTests(unittest.TestCase):
    """No fixtures, mocks, database connections or SQL execution."""

    def test_normalization_and_optional_links(self):
        fields = validate_ticket_fields(
            "  Title  ", "  Description\n  ", "Medium", "17", ""
        )
        self.assertEqual(
            fields,
            {
                "title": "Title",
                "description": "Description",
                "priority": "Medium",
                "assignee": 17,
                "milestone": None,
            },
        )
        fields = validate_ticket_fields("T", "D", "Urgent", None, "6")
        self.assertIsNone(fields["assignee"])
        self.assertEqual(fields["milestone"], 6)

    def test_required_text_and_limits(self):
        for title in (None, 1, [], "", "  ", "a" * 201, "bad\x00title"):
            with self.subTest(title=repr(title)), self.assertRaises(ValueError):
                validate_ticket_fields(title, "Description", "Medium")
        for description in (
            None,
            False,
            [],
            "",
            "\n ",
            "a" * 20001,
            "bad\x00description",
        ):
            with (
                self.subTest(description=repr(description)),
                self.assertRaises(ValueError),
            ):
                validate_ticket_fields("Title", description, "Medium")
        validate_ticket_fields("t" * 200, "d" * 20000, "Low")

    def test_fixed_priorities(self):
        for priority in ("Low", "Medium", "High", "Urgent"):
            self.assertEqual(
                validate_ticket_fields("T", "D", priority)["priority"], priority
            )
        for priority in (None, [], True, "urgent", "High ", "Other"):
            with self.subTest(priority=priority), self.assertRaises(ValueError):
                validate_ticket_fields("T", "D", priority)

    def test_malformed_identifiers(self):
        for value in (
            True,
            False,
            0,
            -1,
            1.0,
            "0",
            "-1",
            "1.0",
            "+1",
            " 1",
            "١",
            "１",
            "1;DELETE",
            "9" * 20,
            9223372036854775808,
            {},
            [],
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_ticket_id(value)
            with self.subTest(assignee=value), self.assertRaises(ValueError):
                validate_ticket_fields("T", "D", "Medium", value)
            with self.subTest(milestone=value), self.assertRaises(ValueError):
                validate_ticket_fields("T", "D", "Medium", None, value)
        self.assertEqual(
            validate_ticket_id("9223372036854775807"), 9223372036854775807
        )
        self.assertIsNone(validate_ticket_id("", optional=True))
        with self.assertRaises(ValueError):
            validate_ticket_id(None)

    def test_services_reject_bad_input_before_connecting(self):
        # These exact calls fail in pure validation, before any engine is accessed.
        with self.assertRaises(ValueError):
            create_ticket(0, 0, "", "D", "Medium")
        with self.assertRaises(ValueError):
            update_ticket(0, 0, 0, "T", "D", "Invalid")
        with self.assertRaises(ValueError):
            delete_ticket(0, 0, 0)
        with self.assertRaises(ValueError):
            move_ticket(0, 0, 0, "Invalid")

    def test_public_signatures(self):
        self.assertEqual(
            list(inspect.signature(create_ticket).parameters),
            [
                "actor_id",
                "project_id",
                "title",
                "description",
                "priority",
                "assignee",
                "milestone",
            ],
        )
        self.assertEqual(
            list(inspect.signature(update_ticket).parameters),
            [
                "actor_id",
                "project_id",
                "ticket_id",
                "title",
                "description",
                "priority",
                "assignee",
                "milestone",
            ],
        )
        self.assertEqual(
            list(inspect.signature(delete_ticket).parameters),
            ["actor_id", "project_id", "ticket_id"],
        )
        self.assertEqual(
            list(inspect.signature(move_ticket).parameters),
            ["actor_id", "project_id", "ticket_id", "status"],
        )

    def test_mutation_structure_and_event_boundary(self):
        service_source = (ROOT / "UniFlow_/workspace_services.py").read_text()
        service_tree = ast.parse(service_source)
        functions = {
            node.name: node
            for node in service_tree.body
            if isinstance(node, ast.FunctionDef)
        }
        for name in (
            "create_ticket",
            "update_ticket",
            "delete_ticket",
            "move_ticket",
        ):
            source = ast.get_source_segment(service_source, functions[name])
            self.assertIn("_get_engine().begin()", source)
            self.assertIn(
                "_lock_workspace(connection, actor_id, project_id)", source
            )
            self.assertIn(
                "authorize_workspace(connection, actor_id, project_id)", source
            )
            self.assertIn(
                "_read_workspace(connection, actor_id, project_id)", source
            )
            if name != "create_ticket":
                self.assertIn(
                    "_require_ticket(connection, project_id, ticket_id)", source
                )
        update_source = ast.get_source_segment(
            service_source, functions["update_ticket"]
        )
        self.assertNotIn("status =", update_source)
        self.assertNotIn("created_by =", update_source)
        self.assertNotIn("created_at =", update_source)
        self.assertIn("updated_at = now()", update_source)
        state_tree = ast.parse(
            (ROOT / "UniFlow_/states/workspace_state.py").read_text()
        )
        state = next(
            node for node in state_tree.body if isinstance(node, ast.ClassDef)
        )
        events = {
            node.name: node
            for node in state.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in (
            "open_create",
            "open_edit",
            "open_delete",
            "submit_ticket",
            "confirm_delete",
            "change_status",
            "drop_ticket",
            "keyboard_pickup",
            "keyboard_drop",
            "mutate_ticket",
        ):
            self.assertIsInstance(events[name], ast.AsyncFunctionDef)
            self.assertIn("_session_allowed", ast.unparse(events[name]))
            self.assertNotIn(
                "actor_id", [arg.arg for arg in events[name].args.args]
            )
        self.assertIn("asyncio.to_thread", ast.unparse(events["mutate_ticket"]))

    def test_component_construction(self):
        from UniFlow_.components.workspace import workspace_portal
        from UniFlow_.components.workspace_ticket_dialogs import ticket_dialogs

        self.assertIsInstance(workspace_portal(), rx.Component)
        self.assertIsInstance(ticket_dialogs(), rx.Component)


if __name__ == "__main__":
    unittest.main()
