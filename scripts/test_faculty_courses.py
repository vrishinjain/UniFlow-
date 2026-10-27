import reflex as rx

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from UniFlow_.courses_services import create_course, list_faculty_courses
from UniFlow_.states.faculty_state import FacultyState


class CourseServiceTests(unittest.TestCase):
    def test_list_is_scoped_ordered_and_primitive(self):
        connection = MagicMock()
        connection.execute.return_value.all.return_value = [
            SimpleNamespace(
                id=7,
                name=" Engineering ",
                code="CS 410",
                term="Fall 2026",
                faculty_id=12,
                created_at=datetime(2026, 10, 20),
            )
        ]
        with patch("UniFlow_.courses_services._get_engine") as engine:
            engine.return_value.connect.return_value.__enter__.return_value = (
                connection
            )
            courses = list_faculty_courses(12)
        sql, parameters = connection.execute.call_args.args
        self.assertIn("WHERE faculty_id = :faculty_id", str(sql))
        self.assertIn("ORDER BY created_at DESC, id DESC", str(sql))
        self.assertIn("status = 'active'", str(sql))
        self.assertEqual(parameters, {"faculty_id": 12})
        self.assertEqual(
            courses,
            [
                {
                    "id": 7,
                    "name": "Engineering",
                    "code": "CS 410",
                    "term": "Fall 2026",
                    "faculty_id": 12,
                    "created_at": "Oct 20, 2026",
                }
            ],
        )
        connection.commit.assert_not_called()

    def test_empty_list_and_database_failure(self):
        with patch("UniFlow_.courses_services._get_engine") as engine:
            engine.return_value.connect.return_value.__enter__.return_value.execute.return_value.all.return_value = []
            self.assertEqual(list_faculty_courses(12), [])
        with patch(
            "UniFlow_.courses_services._get_engine",
            side_effect=RuntimeError("Unavailable"),
        ):
            with (
                self.assertLogs(level="ERROR"),
                self.assertRaises(RuntimeError),
            ):
                list_faculty_courses(12)

    def test_validation_never_opens_transaction(self):
        with patch("UniFlow_.courses_services._transaction") as transaction:
            for name, code, term in [
                (" ", "CS", "Fall"),
                ("Name", " ", "Fall"),
                ("Name", "CS", " "),
                ("n" * 201, "CS", "Fall"),
                ("Name", "c" * 51, "Fall"),
                ("Name", "CS", "t" * 101),
                ("Na\x00me", "CS", "Fall"),
            ]:
                with (
                    self.subTest(name=name, code=code, term=term),
                    self.assertRaises(ValueError),
                ):
                    create_course(12, name, code, term)
            for identity in (0, -1, True, "12", 9223372036854775808):
                with (
                    self.subTest(identity=identity),
                    self.assertRaises(ValueError),
                ):
                    create_course(identity, "Name", "CS", "Fall")
            transaction.assert_not_called()
        with patch("UniFlow_.courses_services._get_engine") as engine:
            with self.assertRaises(ValueError):
                list_faculty_courses(0)
            engine.assert_not_called()

    def test_creation_locks_faculty_before_check_and_insert(self):
        session = MagicMock()
        session.execute.side_effect = [
            MagicMock(
                first=lambda: SimpleNamespace(
                    id=12, role="faculty", status="active"
                )
            ),
            MagicMock(first=lambda: None),
            MagicMock(scalar_one=lambda: 7),
        ]
        with patch("UniFlow_.courses_services._transaction") as transaction:
            transaction.return_value.__enter__.return_value = session
            self.assertEqual(
                create_course(12, " Engineering ", " CS 410 ", " Fall 2026 "), 7
            )
        calls = session.execute.call_args_list
        self.assertIn("FOR UPDATE", str(calls[0].args[0]))
        self.assertIn("public.users", str(calls[0].args[0]))
        self.assertIn(
            "lower(btrim(code)) = lower(btrim(:code))", str(calls[1].args[0])
        )
        self.assertIn(
            "lower(btrim(term)) = lower(btrim(:term))", str(calls[1].args[0])
        )
        self.assertEqual(
            calls[1].args[1],
            {"faculty_id": 12, "code": "CS 410", "term": "Fall 2026"},
        )
        self.assertIn("RETURNING id", str(calls[2].args[0]))
        self.assertEqual(
            calls[2].args[1],
            {
                "faculty_id": 12,
                "name": "Engineering",
                "code": "CS 410",
                "term": "Fall 2026",
            },
        )

    def test_duplicate_does_not_insert(self):
        session = MagicMock()
        session.execute.side_effect = [
            MagicMock(
                first=lambda: SimpleNamespace(role="faculty", status="active")
            ),
            MagicMock(first=lambda: SimpleNamespace(id=7)),
        ]
        with patch("UniFlow_.courses_services._transaction") as transaction:
            transaction.return_value.__enter__.return_value = session
            with self.assertRaisesRegex(
                ValueError, r"^You already have this course for this term\.$"
            ):
                create_course(12, "Other name", "cs 410", "fall 2026")
        self.assertEqual(session.execute.call_count, 2)
        self.assertIs(
            transaction.return_value.__exit__.call_args.args[0], ValueError
        )

    def test_inactive_wrong_role_or_missing_faculty_never_inserts(self):
        for account in (
            None,
            SimpleNamespace(role="faculty", status="pending"),
            SimpleNamespace(role="student", status="active"),
        ):
            session = MagicMock()
            session.execute.return_value.first.return_value = account
            with (
                self.subTest(account=account),
                patch("UniFlow_.courses_services._transaction") as transaction,
            ):
                transaction.return_value.__enter__.return_value = session
                with self.assertRaises(PermissionError):
                    create_course(12, "Name", "CS", "Fall")
                self.assertEqual(session.execute.call_count, 1)


class CourseStateHarness:
    _clear_access = FacultyState._clear_access
    _courses_session_matches = FacultyState._courses_session_matches

    def __init__(self):
        self._courses_epoch = 0
        self._courses_load_request = 0
        self.course_form_revision = 0
        self.course_creating = False
        self.login = SimpleNamespace(
            signed_in=True,
            _session_user_id=12,
            role="faculty",
            must_change_password=False,
        )
        self._clear_access()
        self._authorized = True
        self.full_name = "Faculty"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_state(self, state_class):
        return self.login


async def consume(generator):
    return [event async for event in generator]


class CourseStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_creation_ignores_client_identity_and_refreshes(self):
        state = CourseStateHarness()
        account = SimpleNamespace(id=12)
        with (
            patch(
                "UniFlow_.states.faculty_state.check_dashboard_access",
                new=AsyncMock(return_value=(account, "")),
            ) as guard,
            patch(
                "UniFlow_.states.faculty_state.save_course", return_value=7
            ) as save,
        ):
            events = await consume(
                FacultyState.create_course.fn(
                    state,
                    {
                        "faculty_id": 999,
                        "name": "Name",
                        "code": "CS",
                        "term": "Fall",
                    },
                )
            )
        save.assert_called_once_with(12, "Name", "CS", "Fall")
        self.assertEqual(guard.await_count, 2)
        self.assertEqual(state.course_name, "")
        self.assertEqual(state.course_success, "Course added successfully.")
        self.assertFalse(state.course_creating)
        self.assertTrue(events)

    async def test_duplicate_preserves_fields_and_exact_message(self):
        state = CourseStateHarness()
        with (
            patch(
                "UniFlow_.states.faculty_state.check_dashboard_access",
                new=AsyncMock(return_value=(SimpleNamespace(id=12), "")),
            ),
            patch(
                "UniFlow_.states.faculty_state.save_course",
                side_effect=ValueError(
                    "You already have this course for this term."
                ),
            ),
        ):
            with self.assertLogs(level="ERROR"):
                await consume(
                    FacultyState.create_course.fn(
                        state, {"name": "Name", "code": "CS", "term": "Fall"}
                    )
                )
        self.assertEqual(
            state.course_error, "You already have this course for this term."
        )
        self.assertEqual(state.course_name, "Name")
        self.assertFalse(state.course_creating)

    async def test_denied_access_never_calls_services(self):
        for handler, args, target in [
            (FacultyState.load_courses, (), "list_faculty_courses"),
            (
                FacultyState.create_course,
                ({"name": "Name", "code": "CS", "term": "Fall"},),
                "save_course",
            ),
        ]:
            state = CourseStateHarness()
            with (
                patch(
                    "UniFlow_.states.faculty_state.check_dashboard_access",
                    new=AsyncMock(return_value=(None, "/")),
                ),
                patch(f"UniFlow_.states.faculty_state.{target}") as service,
            ):
                await consume(handler.fn(state, *args))
            service.assert_not_called()
            self.assertFalse(state._authorized)
            self.assertEqual(state.courses, [])

    async def test_session_change_during_read_discards_data(self):
        state = CourseStateHarness()

        def read(faculty_id):
            state.login._session_user_id = 99
            return [
                {
                    "id": 7,
                    "name": "Private",
                    "code": "CS",
                    "term": "Fall",
                    "faculty_id": 12,
                    "created_at": "Oct 20, 2026",
                }
            ]

        with (
            patch(
                "UniFlow_.states.faculty_state.check_dashboard_access",
                new=AsyncMock(
                    side_effect=[
                        (SimpleNamespace(id=12), ""),
                        (SimpleNamespace(id=99), ""),
                    ]
                ),
            ),
            patch(
                "UniFlow_.states.faculty_state.list_faculty_courses",
                side_effect=read,
            ),
        ):
            await consume(FacultyState.load_courses.fn(state))
        self.assertEqual(state.courses, [])
        self.assertFalse(state._authorized)
        self.assertFalse(state.courses_loading)

    async def test_logout_epoch_prevents_late_creation_feedback(self):
        state = CourseStateHarness()

        def save(*args):
            state._clear_access()
            state.login.signed_in = False
            return 7

        with (
            patch(
                "UniFlow_.states.faculty_state.check_dashboard_access",
                new=AsyncMock(
                    side_effect=[(SimpleNamespace(id=12), ""), (None, "/")]
                ),
            ),
            patch(
                "UniFlow_.states.faculty_state.save_course", side_effect=save
            ),
        ):
            await consume(
                FacultyState.create_course.fn(
                    state, {"name": "Name", "code": "CS", "term": "Fall"}
                )
            )
        self.assertEqual(state.course_success, "")
        self.assertEqual(state.course_name, "")
        self.assertEqual(state.courses, [])
        self.assertFalse(state.course_creating)


if __name__ == "__main__":
    unittest.main()
