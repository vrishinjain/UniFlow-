import reflex as rx

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from UniFlow_.project_services import list_sponsor_projects


class SponsorProjectsTests(unittest.TestCase):
    def test_parameterized_query_and_display_fields(self):
        created_at = datetime(2026, 10, 20, 3, 51, 30)
        connection = MagicMock()
        connection.execute.return_value.all.return_value = [
            SimpleNamespace(
                id=5,
                title="Project",
                status="pending",
                created_at=created_at,
            )
        ]
        with patch("UniFlow_.project_services._get_engine") as engine:
            engine.return_value.connect.return_value.__enter__.return_value = (
                connection
            )
            result = list_sponsor_projects(35)
        statement, parameters = connection.execute.call_args.args
        self.assertEqual(
            str(statement),
            "SELECT id,title,status,created_at FROM public.projects WHERE sponsor_id = :sponsor_id ORDER BY created_at DESC, id DESC",
        )
        self.assertEqual(parameters, {"sponsor_id": 35})
        self.assertEqual(
            result,
            [
                {
                    "id": 5,
                    "title": "Project",
                    "status": "Pending",
                    "submitted_date": "Oct 20, 2026",
                    "submitted_at": created_at.isoformat(),
                }
            ],
        )
        connection.commit.assert_not_called()

    def test_empty_result(self):
        with patch("UniFlow_.project_services._get_engine") as engine:
            engine.return_value.connect.return_value.__enter__.return_value.execute.return_value.all.return_value = []
            self.assertEqual(list_sponsor_projects(35), [])

    def test_invalid_identity_never_queries(self):
        with patch("UniFlow_.project_services._get_engine") as engine:
            for value in (0, -1, True, "35", 9223372036854775808):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    list_sponsor_projects(value)
            engine.assert_not_called()

    def test_failure_is_not_an_empty_result(self):
        with patch(
            "UniFlow_.project_services._get_engine",
            side_effect=RuntimeError("Unavailable"),
        ):
            with (
                self.assertLogs(level="ERROR"),
                self.assertRaises(RuntimeError),
            ):
                list_sponsor_projects(35)


if __name__ == "__main__":
    unittest.main()
