"""T-65 tests: faculty review of sponsor projects.

Uses a fake database session, so no live database is touched.
Run with:  python -m unittest scripts.test_project_review -v
"""

import copy
import unittest
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from UniFlow_ import review_services
from UniFlow_.review_services import (
    NOTES_MAX_CHARS,
    list_review_history,
    review_project,
)


class FakeResult:
    def __init__(self, first=None, rows=None):
        self._first = first
        self._rows = rows or []

    def first(self):
        return self._first

    def mappings(self):
        return SimpleNamespace(all=lambda: self._rows)


class FakeSession:
    """Mimics the projects / users / project_reviews tables."""

    def __init__(self):
        self.users = {
            7: SimpleNamespace(
                role="faculty", status="active", must_change_password=False
            ),
            8: SimpleNamespace(
                role="sponsor", status="active", must_change_password=False
            ),
            9: SimpleNamespace(
                role="student", status="active", must_change_password=False
            ),
        }
        self.projects = {42: "pending"}
        self.reviews: list[dict] = []
        self.history_rows: list[dict] = []

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        params = params or {}
        if sql.startswith("SELECT role, status, must_change_password"):
            return FakeResult(first=self.users.get(params["id"]))
        if sql.startswith("UPDATE public.projects"):
            pid = params["project_id"]
            if self.projects.get(pid) != "pending":
                return FakeResult(first=None)
            self.projects[pid] = params["new_status"]
            return FakeResult(first=SimpleNamespace(id=pid))
        if sql.startswith("INSERT INTO public.project_reviews"):
            self.reviews.append(dict(params))
            return FakeResult()
        if sql.startswith("SELECT r.action"):
            return FakeResult(rows=self.history_rows)
        raise AssertionError(f"Unexpected SQL: {sql}")


class ReviewProjectTests(unittest.TestCase):
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

        patcher = patch.object(review_services, "_transaction", transaction)
        patcher.start()
        self.addCleanup(patcher.stop)

        engine = patch(
            "UniFlow_.user_services._get_engine",
            side_effect=AssertionError("Live database access forbidden"),
        )
        engine.start()
        self.addCleanup(engine.stop)

    # ---------- happy paths ----------

    def test_accept_moves_pending_to_accepted_and_logs_it(self):
        self.assertEqual(review_project(7, 42, "accept"), "accepted")
        self.assertEqual(self.db.projects[42], "accepted")
        self.assertEqual(
            self.db.reviews,
            [
                {
                    "project_id": 42,
                    "actor_id": 7,
                    "action": "accepted",
                    "notes": None,
                }
            ],
        )

    def test_accept_keeps_optional_notes(self):
        review_project(7, 42, "accept", "  Great fit for CS682  ")
        self.assertEqual(self.db.reviews[0]["notes"], "Great fit for CS682")

    def test_request_revision_with_notes(self):
        status = review_project(7, 42, "request_revision", "Add a timeline")
        self.assertEqual(status, "revision_requested")
        self.assertEqual(self.db.projects[42], "revision_requested")
        self.assertEqual(self.db.reviews[0]["notes"], "Add a timeline")

    def test_reject_with_reason(self):
        self.assertEqual(
            review_project(7, 42, "reject", "Out of scope"), "rejected"
        )
        self.assertEqual(self.db.reviews[0]["action"], "rejected")

    # ---------- required notes ----------

    def test_request_revision_requires_notes(self):
        for notes in ("", "   ", "\n\t", None):
            with self.subTest(notes=notes), self.assertRaises(ValueError):
                review_project(7, 42, "request_revision", notes)
        self.assertEqual(self.db.projects[42], "pending")
        self.assertEqual(self.db.reviews, [])

    def test_reject_requires_reason(self):
        with self.assertRaises(ValueError):
            review_project(7, 42, "reject", "   ")
        self.assertEqual(self.db.projects[42], "pending")
        self.assertEqual(self.db.reviews, [])

    def test_notes_too_long_or_with_null_character(self):
        for notes in ("x" * (NOTES_MAX_CHARS + 1), "bad\x00note"):
            with self.subTest(length=len(notes)), self.assertRaises(ValueError):
                review_project(7, 42, "reject", notes)
        self.assertEqual(self.db.projects[42], "pending")

    def test_notes_at_the_limit_are_allowed(self):
        review_project(7, 42, "reject", "x" * NOTES_MAX_CHARS)
        self.assertEqual(self.db.projects[42], "rejected")

    # ---------- permissions ----------

    def test_only_faculty_can_review(self):
        for user_id in (8, 9, 999):  # sponsor, student, unknown user
            with self.subTest(user_id=user_id), self.assertRaises(
                PermissionError
            ):
                review_project(user_id, 42, "accept")
        self.assertEqual(self.db.projects[42], "pending")
        self.assertEqual(self.db.reviews, [])

    def test_inactive_faculty_cannot_review(self):
        self.db.users[7].status = "rejected"
        with self.assertRaises(PermissionError):
            review_project(7, 42, "accept")
        self.assertEqual(self.db.projects[42], "pending")

    def test_faculty_who_must_change_password_cannot_review(self):
        self.db.users[7].must_change_password = True
        with self.assertRaises(PermissionError):
            review_project(7, 42, "accept")
        self.assertEqual(self.db.projects[42], "pending")

    # ---------- status rules ----------

    def test_cannot_review_a_project_twice(self):
        review_project(7, 42, "accept")
        for action, notes in (
            ("accept", ""),
            ("reject", "changed my mind"),
            ("request_revision", "more detail"),
        ):
            with self.subTest(action=action), self.assertRaises(ValueError):
                review_project(7, 42, action, notes)
        self.assertEqual(self.db.projects[42], "accepted")
        self.assertEqual(len(self.db.reviews), 1)

    def test_cannot_review_non_pending_projects(self):
        for status in ("revision_requested", "accepted", "rejected"):
            self.db.projects[42] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                review_project(7, 42, "accept")
            self.assertEqual(self.db.projects[42], status)
        self.assertEqual(self.db.reviews, [])

    def test_missing_project_is_refused(self):
        with self.assertRaises(ValueError):
            review_project(7, 1234, "accept")

    # ---------- bad input ----------

    def test_invalid_action(self):
        for action in ("approve", "", "ACCEPT", None):
            with self.subTest(action=action), self.assertRaises(ValueError):
                review_project(7, 42, action)
        self.assertEqual(self.db.projects[42], "pending")

    def test_invalid_ids(self):
        for faculty_id, project_id in (
            (0, 42),
            (-1, 42),
            (True, 42),
            ("7", 42),
            (7, 0),
            (7, -5),
            (7, "42"),
            (7, True),
        ):
            with self.subTest(f=faculty_id, p=project_id), self.assertRaises(
                ValueError
            ):
                review_project(faculty_id, project_id, "accept")
        self.assertEqual(self.db.projects[42], "pending")

    # ---------- history ----------

    def test_history_is_formatted_for_display(self):
        self.db.history_rows = [
            {
                "action": "rejected",
                "notes": "Out of scope",
                "created_at": datetime(2026, 10, 27, 14, 5),
                "reviewer": "Dr. Smith",
            },
            {
                "action": "resubmitted",
                "notes": None,
                "created_at": datetime(2026, 10, 26, 9, 0),
                "reviewer": "Acme Corp",
            },
        ]
        history = list_review_history(42)
        self.assertEqual(history[0]["label"], "Rejected")
        self.assertEqual(history[0]["notes"], "Out of scope")
        self.assertEqual(history[0]["reviewer"], "Dr. Smith")
        self.assertEqual(history[0]["created_at"], "Oct 27, 2026 02:05 PM")
        self.assertEqual(history[1]["label"], "Resubmitted by sponsor")
        self.assertEqual(history[1]["notes"], "")

    def test_history_rejects_bad_project_id(self):
        with self.assertRaises(ValueError):
            list_review_history(0)


if __name__ == "__main__":
    unittest.main()
