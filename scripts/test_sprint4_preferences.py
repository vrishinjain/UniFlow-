import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import IntegrityError

from UniFlow_.preference_services import save_student_preferences


class TestSprint4Preferences(unittest.TestCase):

    @patch("UniFlow_.preference_services._transaction")
    def test_duplicate_preferences_rejected(self, mock_transaction):

        with self.assertRaisesRegex(
            ValueError, "Each project can only be ranked once."
        ):
            save_student_preferences(1, 10, ["101", "101", "103"])

        mock_transaction.assert_not_called()

    @patch("UniFlow_.preference_services._require_active_student")
    @patch("UniFlow_.preference_services._transaction")
    def test_closed_preferences_rejected(
        self, mock_transaction, mock_active_student
    ):
        session = MagicMock()
        mock_transaction.return_value.__enter__.return_value = session

        course = MagicMock()
        course.preferences_open = False
        session.execute.return_value.first.return_value = course

        with self.assertRaisesRegex(
            ValueError, "Preferences are closed for this course."
        ):
            save_student_preferences(1, 10, ["101", "102", "103"])

        session.execute.assert_called_once()

    @patch("UniFlow_.preference_services._require_active_student")
    @patch("UniFlow_.preference_services._transaction")
    def test_preferences_saved_with_unique_ranks(
        self, mock_transaction, mock_active_student
    ):
        session = MagicMock()
        mock_transaction.return_value.__enter__.return_value = session

        course = MagicMock()
        course.preferences_open = True
        session.execute.return_value.first.return_value = course

        session.execute.return_value.all.return_value = [
            MagicMock(id=101),
            MagicMock(id=102),
            MagicMock(id=103),
        ]

        save_student_preferences(1, 10, ["101", "102", "103"])

        inserted = [
            call.args[1]
            for call in session.execute.call_args_list
            if "INSERT INTO" in str(call.args[0])
        ]

        self.assertEqual(3, len(inserted))
        self.assertEqual([1, 2, 3], [row["rank"] for row in inserted])
        self.assertEqual(
            [101, 102, 103],
            [row["project_id"] for row in inserted],
        )

    @patch("UniFlow_.preference_services._require_active_student")
    @patch("UniFlow_.preference_services._transaction")
    def test_duplicate_rank_constraint_error(
        self, mock_transaction, mock_active_student
    ):
        session = MagicMock()
        mock_transaction.return_value.__enter__.return_value = session

        course = MagicMock()
        course.preferences_open = True

        course_result = MagicMock()
        course_result.first.return_value = course

        project_result = MagicMock()
        project_result.all.return_value = [
            MagicMock(id=101),
            MagicMock(id=102),
            MagicMock(id=103),
        ]

        session.execute.side_effect = [
            course_result,
            project_result,
            MagicMock(),
            IntegrityError(
                "INSERT INTO student_preference",
                {},
                Exception("Duplicate rank"),
            ),
        ]

        with self.assertLogs(level="ERROR"):
            with self.assertRaisesRegex(
                ValueError,
                "Your preferences could not be saved.",
            ):
                save_student_preferences(1, 10, ["101", "102", "103"])

        self.assertEqual(4, session.execute.call_count)


if __name__ == "__main__":
    unittest.main()