"""T-65 / T-66 tests: faculty review of sponsor projects and course sharing.

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
    MAX_SHARED_COURSES,
    NOTES_MAX_CHARS,
    course_option,
    list_project_courses,
    list_review_history,
    review_project,
    set_project_courses,
)


class FakeResult:
    def __init__(self, first=None, rows=None):
        self._first = first
        self._rows = rows or []

    def first(self):
        return self._first

    def all(self):
        return self._rows

    def mappings(self):
        return SimpleNamespace(all=lambda: self._rows)


class FakeSession:
    """Mimics users, projects, project_reviews, courses, project_course_visibility."""

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
            10: SimpleNamespace(
                role="faculty", status="active", must_change_password=False
            ),
        }
        self.projects = {42: "pending"}
        self.reviews: list[dict] = []
        self.history_rows: list[dict] = []
        # course id -> (owner faculty id, code, name, term)
        self.courses = {
            1: (7, "CS682", "Capstone", "Fall 2026"),
            2: (7, "CS637", "Database Websites", "Fall 2026"),
            3: (10, "CS410", "Software Engineering", "Fall 2026"),
        }
        self.shares: list[dict] = []

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        if isinstance(params, list):
            return self.execute_many(sql, params)
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
        if sql.startswith("SELECT id FROM public.courses"):
            return FakeResult(
                rows=[
                    SimpleNamespace(id=cid)
                    for cid in params["course_ids"]
                    if cid in self.courses
                    and self.courses[cid][0] == params["faculty_id"]
                ]
            )
        if sql.startswith("DELETE FROM public.project_course_visibility"):
            self.shares = [
                row
                for row in self.shares
                if not (
                    row["project_id"] == params["project_id"]
                    and self.courses[row["course_id"]][0] == params["faculty_id"]
                )
            ]
            return FakeResult()
        if sql.startswith("SELECT status FROM public.projects"):
            status = self.projects.get(params["project_id"])
            return FakeResult(
                first=None if status is None else SimpleNamespace(status=status)
            )
        if sql.startswith("SELECT DISTINCT c.id"):
            ids = sorted(
                {
                    row["course_id"]
                    for row in self.shares
                    if row["project_id"] == params["project_id"]
                }
            )
            return FakeResult(
                rows=[
                    {
                        "id": cid,
                        "code": self.courses[cid][1],
                        "name": self.courses[cid][2],
                        "term": self.courses[cid][3],
                    }
                    for cid in ids
                ]
            )
        raise AssertionError(f"Unexpected SQL: {sql}")

    def execute_many(self, sql, rows):
        if sql.startswith("INSERT INTO public.project_course_visibility"):
            self.shares.extend(dict(row) for row in rows)
            return FakeResult()
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
                copy.deepcopy(self.db.shares),
            )
            try:
                yield self.db
            except Exception:
                self.db.projects, self.db.reviews, self.db.shares = before
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
        self.assertEqual(review_project(7, 42, "accept", "", [1]), "accepted")
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
        review_project(7, 42, "accept", "  Great fit for CS682  ", [1])
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
                review_project(user_id, 42, "accept", "", [1])
        self.assertEqual(self.db.projects[42], "pending")
        self.assertEqual(self.db.reviews, [])

    def test_inactive_faculty_cannot_review(self):
        self.db.users[7].status = "rejected"
        with self.assertRaises(PermissionError):
            review_project(7, 42, "accept", "", [1])
        self.assertEqual(self.db.projects[42], "pending")

    def test_faculty_who_must_change_password_cannot_review(self):
        self.db.users[7].must_change_password = True
        with self.assertRaises(PermissionError):
            review_project(7, 42, "accept", "", [1])
        self.assertEqual(self.db.projects[42], "pending")

    # ---------- status rules ----------

    def test_cannot_review_a_project_twice(self):
        review_project(7, 42, "accept", "", [1])
        for action, notes in (
            ("accept", ""),
            ("reject", "changed my mind"),
            ("request_revision", "more detail"),
        ):
            with self.subTest(action=action), self.assertRaises(ValueError):
                review_project(7, 42, action, notes, [1])
        self.assertEqual(self.db.projects[42], "accepted")
        self.assertEqual(len(self.db.reviews), 1)

    def test_cannot_review_non_pending_projects(self):
        for status in ("revision_requested", "accepted", "rejected"):
            self.db.projects[42] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                review_project(7, 42, "accept", "", [1])
            self.assertEqual(self.db.projects[42], status)
        self.assertEqual(self.db.reviews, [])

    def test_missing_project_is_refused(self):
        with self.assertRaises(ValueError):
            review_project(7, 1234, "accept", "", [1])

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
                review_project(faculty_id, project_id, "accept", "", [1])
        self.assertEqual(self.db.projects[42], "pending")

    # ---------- T-66: sharing on accept ----------

    def test_accept_shares_with_chosen_courses(self):
        review_project(7, 42, "accept", "", [1, 2])
        self.assertEqual(
            sorted(row["course_id"] for row in self.db.shares), [1, 2]
        )
        self.assertTrue(all(row["shared_by"] == 7 for row in self.db.shares))
        self.assertTrue(all(row["project_id"] == 42 for row in self.db.shares))

    def test_accept_ignores_duplicate_course_ids(self):
        review_project(7, 42, "accept", "", [1, 1, 1])
        self.assertEqual([row["course_id"] for row in self.db.shares], [1])

    def test_accept_requires_at_least_one_course(self):
        for courses in (None, [], ()):
            with self.subTest(courses=courses), self.assertRaises(ValueError):
                review_project(7, 42, "accept", "", courses)
        self.assertEqual(self.db.projects[42], "pending")
        self.assertEqual(self.db.reviews, [])
        self.assertEqual(self.db.shares, [])

    def test_accept_refuses_another_faculty_members_course(self):
        with self.assertRaises(PermissionError):
            review_project(7, 42, "accept", "", [1, 3])  # 3 belongs to faculty 10
        # Nothing is saved: still pending, no review, no shares.
        self.assertEqual(self.db.projects[42], "pending")
        self.assertEqual(self.db.reviews, [])
        self.assertEqual(self.db.shares, [])

    def test_accept_refuses_missing_course(self):
        with self.assertRaises(PermissionError):
            review_project(7, 42, "accept", "", [999])
        self.assertEqual(self.db.projects[42], "pending")

    def test_accept_refuses_bad_course_ids(self):
        for courses in (["1"], [0], [-2], [True], [1.5]):
            with self.subTest(courses=courses), self.assertRaises(ValueError):
                review_project(7, 42, "accept", "", courses)
        self.assertEqual(self.db.projects[42], "pending")

    def test_accept_refuses_too_many_courses(self):
        with self.assertRaises(ValueError):
            review_project(
                7, 42, "accept", "", list(range(1, MAX_SHARED_COURSES + 2))
            )

    def test_revise_and_reject_do_not_share(self):
        review_project(7, 42, "request_revision", "More detail", [1])
        self.assertEqual(self.db.shares, [])

    # ---------- T-66: changing sharing later ----------

    def test_change_shared_courses_on_accepted_project(self):
        review_project(7, 42, "accept", "", [1])
        set_project_courses(7, 42, [2])
        self.assertEqual([row["course_id"] for row in self.db.shares], [2])

    def test_changing_sharing_keeps_other_faculty_shares(self):
        review_project(7, 42, "accept", "", [1])
        set_project_courses(10, 42, [3])  # faculty 10 adds their own course
        set_project_courses(7, 42, [2])  # faculty 7 swaps 1 -> 2
        self.assertEqual(
            sorted(row["course_id"] for row in self.db.shares), [2, 3]
        )

    def test_cannot_share_project_that_is_not_accepted(self):
        for status in ("pending", "revision_requested", "rejected"):
            self.db.projects[42] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                set_project_courses(7, 42, [1])
        self.assertEqual(self.db.shares, [])

    def test_cannot_share_missing_project(self):
        with self.assertRaises(ValueError):
            set_project_courses(7, 1234, [1])

    def test_cannot_share_to_courses_you_do_not_own(self):
        review_project(7, 42, "accept", "", [1])
        with self.assertRaises(PermissionError):
            set_project_courses(7, 42, [3])
        self.assertEqual([row["course_id"] for row in self.db.shares], [1])

    def test_only_faculty_can_change_sharing(self):
        review_project(7, 42, "accept", "", [1])
        for user_id in (8, 9):
            with self.subTest(user_id=user_id), self.assertRaises(
                PermissionError
            ):
                set_project_courses(user_id, 42, [1])
        self.assertEqual([row["course_id"] for row in self.db.shares], [1])

    def test_changing_sharing_needs_at_least_one_course(self):
        review_project(7, 42, "accept", "", [1])
        with self.assertRaises(ValueError):
            set_project_courses(7, 42, [])
        self.assertEqual([row["course_id"] for row in self.db.shares], [1])

    def test_list_shared_courses_for_display(self):
        review_project(7, 42, "accept", "", [2, 1])
        self.assertEqual(
            list_project_courses(42),
            [
                {"id": "1", "label": "CS682 · Capstone (Fall 2026)"},
                {"id": "2", "label": "CS637 · Database Websites (Fall 2026)"},
            ],
        )

    def test_course_option_from_faculty_course_list(self):
        self.assertEqual(
            course_option(
                {
                    "id": 5,
                    "name": " Capstone ",
                    "code": "CS682",
                    "term": "Fall 2026",
                    "faculty_id": 7,
                    "created_at": "Oct 01, 2026",
                }
            ),
            {"id": "5", "label": "CS682 · Capstone (Fall 2026)"},
        )

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
