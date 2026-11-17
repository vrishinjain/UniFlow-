import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from UniFlow_ import workspace_services


class TestSprint4Workspace(unittest.TestCase):

    def setUp(self):
        self.connection = MagicMock()

        engine = patch.object(workspace_services, "_get_engine")
        self.mock_engine = engine.start()
        self.addCleanup(engine.stop)

        self.mock_engine.return_value.connect.return_value.__enter__.return_value = (
            self.connection
        )

        self.mock_engine.return_value.begin.return_value.__enter__.return_value = (
            self.connection
        )

    @patch.dict("os.environ", {"REFLEX_DB_URL": "mock-only"})
    def test_student_cannot_access_another_team_workspace(self):
        self.connection.execute.return_value.mappings.return_value.first.return_value = None

        with self.assertRaisesRegex(PermissionError, "Access denied"):
            workspace_services.get_workspace(1, 101)

        self.connection.execute.assert_called_once()

    @patch.object(workspace_services, "_require_database")
    @patch.object(workspace_services, "_lock_workspace")
    def test_ticket_assignee_outside_team_rejected(
        self, mock_lock, mock_database
    ):
        self.connection.execute.return_value.scalar_one_or_none.side_effect = [
            99,
            None,
        ]

        with self.assertRaisesRegex(
            ValueError, "Choose an eligible project team member"
        ):
            workspace_services.create_ticket(
                1,
                101,
                "Test Ticket",
                "Test Description",
                "Medium",
                99,
            )

        self.assertEqual(2, self.connection.execute.call_count)

    def test_past_milestone_due_date_rejected(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        with self.assertRaisesRegex(
            ValueError, "Due date must be today or later."
        ):
            workspace_services.create_milestone(
                1,
                101,
                "Test Milestone",
                "Test Description",
                yesterday,
                [],
            )

        self.mock_engine.assert_not_called()

    @patch.object(workspace_services, "_require_database")
    @patch.object(workspace_services, "_lock_workspace")
    @patch.object(workspace_services, "authorize_workspace")
    def test_only_faculty_can_create_milestones(
        self, mock_authorize, mock_lock, mock_database
    ):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        for role in ["student", "system_admin"]:
            with self.subTest(role=role):
                mock_authorize.return_value = {
                    "id": 1,
                    "role": role,
                    "can_edit_milestones": False,
                }

                with self.assertRaisesRegex(
                    PermissionError, "Access denied"
                ):
                    workspace_services.create_milestone(
                        1,
                        101,
                        "Test Milestone",
                        "Test Description",
                        tomorrow,
                        [],
                    )

        self.connection.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
