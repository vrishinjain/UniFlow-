import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from UniFlow_.course_assignment_services import (
    update_manual_assignment,
    list_manual_assignment_projects,
)


class ManualAssignmentTest(unittest.TestCase):

    def setUp(self):
        self.actor_id = 1
        self.course_id = 10
        self.student_id = 20
        self.project_id = 30

        self.session = MagicMock()

        transaction = patch(
            "UniFlow_.course_assignment_services._transaction"
        )
        self.transaction = transaction.start()
        self.addCleanup(transaction.stop)

        self.transaction.return_value.__enter__.return_value = (
            self.session
        )

        access = patch(
            "UniFlow_.course_assignment_services._require_course_access"
        )
        self.access = access.start()
        self.addCleanup(access.stop)

        validation = patch(
            "UniFlow_.course_assignment_services._visible_assignment_projects"
        )
        self.validation = validation.start()
        self.addCleanup(validation.stop)

        self.student = SimpleNamespace(
            id=20,
            email="student@example.com",
        )

        self.project = SimpleNamespace(
            id=30,
            title="Project A",
        )

    def prepare_assignment(self, project_id, title):
        student_result = MagicMock()
        student_result.first.return_value = self.student

        project_result = MagicMock()
        project_result.first.return_value = SimpleNamespace(
            id=project_id,
            title=title,
        )

        self.session.execute.side_effect = [
            student_result,
            project_result,
            MagicMock(),
        ]

        self.validation.return_value = [
            SimpleNamespace(id=project_id, title=title)
        ]

    def test_assign_student(self):
        self.prepare_assignment(30, "Project A")

        result = update_manual_assignment(
            self.actor_id,
            self.course_id,
            self.student_id,
            30,
        )

        self.assertEqual(
            result,
            "Student assignment updated successfully.",
        )

        query, params = self.session.execute.call_args.args

        self.assertIn("INSERT INTO", str(query))
        self.assertEqual(params["student_id"], 20)
        self.assertEqual(params["project_id"], 30)
        self.assertEqual(params["course_id"], 10)

    def test_change_student_project(self):
        self.prepare_assignment(40, "Project B")

        result = update_manual_assignment(
            self.actor_id,
            self.course_id,
            self.student_id,
            40,
        )

        self.assertEqual(
            result,
            "Student assignment updated successfully.",
        )

        query, params = self.session.execute.call_args.args

        self.assertIn("ON CONFLICT", str(query))
        self.assertIn("DO UPDATE", str(query))
        self.assertEqual(params["project_id"], 40)

    def test_duplicate_project_titles(self):
        self.prepare_assignment(40, "Project A")

        self.validation.return_value = [
            SimpleNamespace(id=30, title="Project A"),
            SimpleNamespace(id=40, title="Project A"),
        ]

        result = update_manual_assignment(
            self.actor_id,
            self.course_id,
            self.student_id,
            40,
        )

        self.assertEqual(
            result,
            "Student assignment updated successfully.",
        )

        query, params = self.session.execute.call_args.args

        self.assertIn("INSERT INTO", str(query))
        self.assertEqual(params["project_id"], 40)

    def test_unassign_student(self):
        self.session.execute.return_value.first.return_value = (
            self.student
        )

        result = update_manual_assignment(
            self.actor_id,
            self.course_id,
            self.student_id,
            None,
        )

        self.assertEqual(
            result,
            "Student unassigned successfully.",
        )

        query, params = self.session.execute.call_args.args

        self.assertIn("DELETE FROM", str(query))
        self.assertEqual(params["student_id"], 20)
        self.assertEqual(params["course_id"], 10)

    def test_student_not_enrolled(self):
        self.session.execute.return_value.first.return_value = None

        with self.assertRaisesRegex(
            ValueError,
            "Student not enrolled",
        ):
            update_manual_assignment(
                self.actor_id,
                self.course_id,
                self.student_id,
                self.project_id,
            )

        self.assertEqual(self.session.execute.call_count, 1)

    def test_project_not_visible(self):
        self.prepare_assignment(30, "Project A")

        self.validation.return_value = []

        with self.assertRaisesRegex(
            ValueError,
            "Project not visible",
        ):
            update_manual_assignment(
                self.actor_id,
                self.course_id,
                self.student_id,
                self.project_id,
            )

        self.assertEqual(self.session.execute.call_count, 2)

    def test_unauthorized_faculty(self):
        self.access.side_effect = PermissionError(
            "Course assignment access denied."
        )

        with self.assertRaises(PermissionError):
            update_manual_assignment(
                self.actor_id,
                self.course_id,
                self.student_id,
                self.project_id,
            )

        self.session.execute.assert_not_called()

    def test_project_not_found(self):
        student_result = MagicMock()
        student_result.first.return_value = self.student

        project_result = MagicMock()
        project_result.first.return_value = None

        self.session.execute.side_effect = [
            student_result,
            project_result,
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Project not found",
        ):
            update_manual_assignment(
                self.actor_id,
                self.course_id,
                self.student_id,
                self.project_id,
            )

        self.validation.assert_not_called()

    def test_list_available_projects(self):
        self.session.execute.return_value.all.return_value = [
            SimpleNamespace(id=30, title="Project A"),
            SimpleNamespace(id=40, title="Project B"),
        ]

        result = list_manual_assignment_projects(
            self.actor_id,
            self.course_id,
        )

        self.assertEqual(
            result,
            [
                {"id": "30", "title": "Project A"},
                {"id": "40", "title": "Project B"},
            ],
        )

        query, params = self.session.execute.call_args.args

        self.assertIn("project_course_visibility", str(query))
        self.assertIn("accepted", str(query))
        self.assertEqual(params["course_id"], 10)

    def test_no_available_projects(self):
        self.session.execute.return_value.all.return_value = []

        result = list_manual_assignment_projects(
            self.actor_id,
            self.course_id,
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
