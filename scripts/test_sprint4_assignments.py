import csv
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from UniFlow_.course_assignment_services import (
    export_course_preferences_csv,
    preview_course_assignments,
    save_course_assignments,
)


class TestSprint4Assignments(unittest.TestCase):

    def setUp(self):
        self.session = MagicMock()

        transaction = patch(
            "UniFlow_.course_assignment_services._transaction"
        )
        self.mock_transaction = transaction.start()
        self.addCleanup(transaction.stop)

        self.mock_transaction.return_value.__enter__.return_value = (
            self.session
        )

        access = patch(
            "UniFlow_.course_assignment_services._require_course_access"
        )
        access.start()
        self.addCleanup(access.stop)

    def test_csv_export_format(self):
        self.session.execute.return_value.mappings.return_value.all.return_value = [
            {
                "student": "student@example.com",
                "choice_1": "Project A",
                "choice_2": "Project B",
                "choice_3": "Project C",
            }
        ]

        result = export_course_preferences_csv(1, 10)
        rows = list(csv.reader(io.StringIO(result)))

        self.assertEqual(
            ["student", "choice_1", "choice_2", "choice_3"],
            rows[0],
        )

        self.assertEqual(
            [
                "student@example.com",
                "Project A",
                "Project B",
                "Project C",
            ],
            rows[1],
        )

    def test_invalid_import_row_rejected(self):
        self.session.execute.return_value.all.return_value = []

        result = preview_course_assignments(
            1, 10, "Invalid assignment row"
        )

        self.assertEqual([], result["valid"])
        self.assertEqual(1, len(result["skipped"]))
        self.assertEqual(
            "Line format not recognized",
            result["skipped"][0]["reason"],
        )

    def test_unknown_student_rejected(self):
        self.session.execute.return_value.all.return_value = []

        result = preview_course_assignments(
            1, 10, "unknown@example.com joins Project A"
        )

        self.assertEqual([], result["valid"])
        self.assertEqual(
            "Unknown student",
            result["skipped"][0]["reason"],
        )

    def test_unenrolled_student_cannot_be_assigned(self):
        users = MagicMock()
        users.all.return_value = [
            SimpleNamespace(
                id=5,
                email="student@example.com",
                role="student",
            )
        ]

        enrollments = MagicMock()
        enrollments.all.return_value = []

        projects = MagicMock()
        projects.all.return_value = [
            SimpleNamespace(id=101, title="Project A")
        ]

        snapshot = MagicMock()
        snapshot.all.return_value = []

        self.session.execute.side_effect = [
            users,
            enrollments,
            projects,
            snapshot,
        ]

        result = save_course_assignments(
            1, 10, "student@example.com joins Project A"
        )

        self.assertEqual(0, result["saved"])
        self.assertEqual(
            "Student not enrolled in this course",
            result["skipped"][0]["reason"],
        )

        self.assertEqual(4, self.session.execute.call_count)

    def test_export_compatible_with_assignment_script(self):
        self.session.execute.return_value.mappings.return_value.all.return_value = [
            {
                "student": "student@example.com",
                "choice_1": "Project1",
                "choice_2": "Project2",
                "choice_3": "Project3",
            }
        ]

        result = export_course_preferences_csv(1, 10)

        script_path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "assignment-script"
            / "assign_students.py"
        )

        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "preferences.csv"

            with open(csv_path, "w", encoding="utf-8", newline="") as file:
                file.write(result)

            output = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(csv_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

        self.assertEqual(
            "student@example.com joins Project1",
            output.stdout.strip(),
        )


if __name__ == "__main__":
    unittest.main()