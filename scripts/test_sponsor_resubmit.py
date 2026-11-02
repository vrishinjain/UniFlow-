"""T-67 tests: sponsor sees review status, revises and resubmits.

Uses a fake database session, so no live database is touched.
Run with:  python -m unittest scripts.test_sponsor_resubmit -v
"""

import copy
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from UniFlow_ import sponsor_review_services
from UniFlow_.sponsor_review_services import (
    DESCRIPTION_MAX_CHARS,
    TITLE_MAX_CHARS,
    get_sponsor_project,
    resubmit_project,
)


class FakeResult:
    def __init__(self, first=None):
        self._first = first

    def first(self):
        return self._first

    def mappings(self):
        return self


class FakeSession:
    """Mimics users, projects and project_reviews."""

    def __init__(self):
        self.users = {
            8: SimpleNamespace(
                role="sponsor", status="active", must_change_password=False
            ),
            11: SimpleNamespace(
                role="sponsor", status="active", must_change_password=False
            ),
            7: SimpleNamespace(
                role="faculty", status="active", must_change_password=False
            ),
            9: SimpleNamespace(
                role="student", status="active", must_change_password=False
            ),
        }
        # project id -> row
        self.projects = {
            42: {
                "id": 42,
                "sponsor_id": 8,
                "title": "Parking app",
                "description": "First draft",
                "status": "revision_requested",
            }
        }
        # newest first, like ORDER BY created_at DESC
        self.reviews: list[dict] = [
            {
                "project_id": 42,
                "actor_id": 7,
                "action": "revision_requested",
                "notes": "Add a timeline",
            }
        ]

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = params or {}

        if sql.startswith("SELECT role, status, must_change_password"):
            return FakeResult(first=self.users.get(params["id"]))

        if sql.startswith("SELECT id, title, description, status"):
            row = self.projects.get(params["project_id"])
            if row is None or row["sponsor_id"] != params["sponsor_id"]:
                return FakeResult(first=None)
            return FakeResult(first=dict(row))

        if sql.startswith("SELECT notes FROM public.project_reviews"):
            for review in self.reviews:
                if review["project_id"] == params["project_id"] and review[
                    "action"
                ] in ("accepted", "revision_requested", "rejected"):
                    return FakeResult(first={"notes": review["notes"]})
            return FakeResult(first=None)

        if sql.startswith("UPDATE public.projects"):
            row = self.projects.get(params["project_id"])
            if (
                row is None
                or row["sponsor_id"] != params["sponsor_id"]
                or row["status"] != "revision_requested"
            ):
                return FakeResult(first=None)
            row.update(
                title=params["title"],
                description=params["description"],
                status="pending",
            )
            return FakeResult(first=SimpleNamespace(id=row["id"]))

        if sql.startswith("INSERT INTO public.project_reviews"):
            self.reviews.insert(
                0,
                {
                    "project_id": params["project_id"],
                    "actor_id": params["actor_id"],
                    "action": "resubmitted",
                    "notes": None,
                },
            )
            return FakeResult()

        raise AssertionError(f"Unexpected SQL: {sql}")


class SponsorResubmitTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession()

        @contextmanager
        def transaction():
            # Roll back on error, like the real _transaction().
            before = (
                copy.deepcopy(self.db.projects),
                copy.deepcopy(self.db.reviews),
            )
            try:
                yield self.db
            except Exception:
                self.db.projects, self.db.reviews = before
                raise

        patcher = patch.object(
            sponsor_review_services, "_transaction", transaction
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        engine = patch(
            "UniFlow_.user_services._get_engine",
            side_effect=AssertionError("Live database access forbidden"),
        )
        engine.start()
        self.addCleanup(engine.stop)

    def project(self):
        return self.db.projects[42]

    # ---------- viewing ----------

    def test_sponsor_sees_status_and_feedback(self):
        details = get_sponsor_project(8, 42)
        self.assertEqual(details["status"], "revision_requested")
        self.assertEqual(details["status_label"], "Changes requested")
        self.assertEqual(details["feedback"], "Add a timeline")
        self.assertTrue(details["can_resubmit"])
        self.assertEqual(details["id"], "42")

    def test_rejected_project_shows_reason_and_cannot_resubmit(self):
        self.project()["status"] = "rejected"
        self.db.reviews.insert(
            0,
            {
                "project_id": 42,
                "actor_id": 7,
                "action": "rejected",
                "notes": "Out of scope",
            },
        )
        details = get_sponsor_project(8, 42)
        self.assertEqual(details["status_label"], "Rejected")
        self.assertEqual(details["feedback"], "Out of scope")
        self.assertFalse(details["can_resubmit"])

    def test_pending_project_shows_no_old_feedback(self):
        self.project()["status"] = "pending"
        details = get_sponsor_project(8, 42)
        self.assertEqual(details["status_label"], "Pending review")
        self.assertEqual(details["feedback"], "")
        self.assertFalse(details["can_resubmit"])

    def test_other_sponsor_cannot_see_project(self):
        self.assertIsNone(get_sponsor_project(11, 42))

    def test_missing_project_returns_none(self):
        self.assertIsNone(get_sponsor_project(8, 1234))

    def test_bad_ids_are_refused(self):
        for sponsor_id, project_id in ((0, 42), (8, 0), (True, 42), (8, "42")):
            with self.subTest(s=sponsor_id, p=project_id), self.assertRaises(
                ValueError
            ):
                get_sponsor_project(sponsor_id, project_id)

    # ---------- resubmitting ----------

    def test_resubmit_saves_edits_and_goes_back_to_pending(self):
        resubmit_project(8, 42, "  Parking app v2  ", "  With a timeline  ")
        self.assertEqual(self.project()["status"], "pending")
        self.assertEqual(self.project()["title"], "Parking app v2")
        self.assertEqual(self.project()["description"], "With a timeline")
        self.assertEqual(
            self.db.reviews[0],
            {
                "project_id": 42,
                "actor_id": 8,
                "action": "resubmitted",
                "notes": None,
            },
        )

    def test_cannot_resubmit_twice(self):
        resubmit_project(8, 42, "v2", "desc")
        with self.assertRaises(ValueError):
            resubmit_project(8, 42, "v3", "desc")
        self.assertEqual(self.project()["title"], "v2")
        self.assertEqual(
            [r["action"] for r in self.db.reviews].count("resubmitted"), 1
        )

    def test_only_revision_requested_projects_can_be_resubmitted(self):
        for status in ("pending", "accepted", "rejected"):
            self.project()["status"] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                resubmit_project(8, 42, "New title", "New description")
            self.assertEqual(self.project()["status"], status)
            self.assertEqual(self.project()["title"], "Parking app")

    def test_other_sponsor_cannot_resubmit(self):
        with self.assertRaises(ValueError):
            resubmit_project(11, 42, "Hijacked", "Not mine")
        self.assertEqual(self.project()["title"], "Parking app")
        self.assertEqual(self.project()["status"], "revision_requested")

    def test_only_active_sponsors_can_resubmit(self):
        for user_id in (7, 9, 999):  # faculty, student, unknown
            with self.subTest(user_id=user_id), self.assertRaises(
                PermissionError
            ):
                resubmit_project(user_id, 42, "Title", "Description")
        self.db.users[8].status = "rejected"
        with self.assertRaises(PermissionError):
            resubmit_project(8, 42, "Title", "Description")
        self.assertEqual(self.project()["status"], "revision_requested")

    def test_sponsor_who_must_change_password_cannot_resubmit(self):
        self.db.users[8].must_change_password = True
        with self.assertRaises(PermissionError):
            resubmit_project(8, 42, "Title", "Description")

    def test_title_and_description_are_required(self):
        for title, description in (
            ("", "desc"),
            ("   ", "desc"),
            ("Title", ""),
            ("Title", "  \n "),
        ):
            with self.subTest(t=title, d=description), self.assertRaises(
                ValueError
            ):
                resubmit_project(8, 42, title, description)
        self.assertEqual(self.project()["status"], "revision_requested")

    def test_too_long_or_null_characters_are_refused(self):
        for title, description in (
            ("x" * (TITLE_MAX_CHARS + 1), "desc"),
            ("Title", "x" * (DESCRIPTION_MAX_CHARS + 1)),
            ("Bad\x00title", "desc"),
            ("Title", "bad\x00desc"),
        ):
            with self.subTest(t=len(title), d=len(description)), self.assertRaises(
                ValueError
            ):
                resubmit_project(8, 42, title, description)
        self.assertEqual(self.project()["status"], "revision_requested")

    def test_limits_are_allowed(self):
        resubmit_project(
            8, 42, "x" * TITLE_MAX_CHARS, "y" * DESCRIPTION_MAX_CHARS
        )
        self.assertEqual(self.project()["status"], "pending")


if __name__ == "__main__":
    unittest.main()
