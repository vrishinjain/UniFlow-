import reflex as rx

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from UniFlow_.project_services import list_sponsor_projects
from UniFlow_.states.sponsor_state import SponsorState


class SponsorProjectsTests(unittest.TestCase):
    def test_scoped_read_and_display_fields(self):
        connection = MagicMock()
        connection.execute.return_value.all.return_value = [
            SimpleNamespace(
                id=7,
                title="A project",
                status="submitted",
                created_at=datetime(2026, 10, 20, 12, 30),
            ),
        ]
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection
        with patch(
            "UniFlow_.project_services._get_engine", return_value=engine
        ):
            projects = list_sponsor_projects(35)
        statement, parameters = connection.execute.call_args.args
        self.assertEqual(parameters, {"sponsor_id": 35})
        self.assertIn("FROM public.projects", str(statement))
        self.assertIn("WHERE sponsor_id = :sponsor_id", str(statement))
        self.assertIn("ORDER BY created_at DESC, id DESC", str(statement))
        self.assertTrue(str(statement).startswith("SELECT "))
        self.assertEqual(
            projects[0],
            {
                "id": 7,
                "title": "A project",
                "status": "Submitted",
                "submitted_date": "Oct 20, 2026",
                "submitted_at": "2026-10-20T12:30:00",
            },
        )
        connection.commit.assert_not_called()

    def test_empty_success(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value.execute.return_value.all.return_value = []
        with patch(
            "UniFlow_.project_services._get_engine", return_value=engine
        ):
            self.assertEqual(list_sponsor_projects(35), [])

    def test_failure_is_not_empty_success(self):
        with patch(
            "UniFlow_.project_services._get_engine",
            side_effect=RuntimeError("Unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                list_sponsor_projects(35)

    def test_invalid_identity_does_not_query(self):
        with patch("UniFlow_.project_services._get_engine") as engine:
            for identity in (0, -1, True, "35"):
                with self.assertRaises(ValueError):
                    list_sponsor_projects(identity)
            engine.assert_not_called()

    def test_access_clear_invalidates_inflight_loads(self):
        state = SimpleNamespace(
            _authorized=True,
            full_name="Sponsor",
            _projects_revision=2,
            projects=[{"id": 7}],
            projects_loading=True,
            projects_loaded=True,
            projects_error="Previous error",
        )
        SponsorState._clear_access(state)
        self.assertEqual(state.projects, [])
        self.assertEqual(state._projects_revision, 3)
        self.assertFalse(state._authorized)
        self.assertFalse(state.projects_loading)
        self.assertFalse(state.projects_loaded)
        self.assertEqual(state.projects_error, "")


if __name__ == "__main__":
    unittest.main()
