import unittest
from unittest.mock import MagicMock, patch

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


if __name__ == "__main__":
    unittest.main()