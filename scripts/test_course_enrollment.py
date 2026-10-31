import reflex as rx

import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from UniFlow_ import courses_services as courses
from UniFlow_ import user_services as users
from UniFlow_.states.faculty_state import FacultyState
from scripts.test_faculty_courses import CourseStateHarness, consume


class CourseParserTests(unittest.TestCase):
    def test_header_crlf_normalization_dedup_and_line_numbers(self):
        parsed = users.parse_bulk_email_file(
            "students.TXT",
            b"\xef\xbb\xbf\r\n EMAIL \r\n Alice@Example.edu \r\nalice@example.edu\r\n\r\nbad address\r\nbob@example.edu\r\n",
        )
        self.assertEqual(
            parsed["addresses"],
            [
                {"email": "alice@example.edu", "line": 3, "reason": ""},
                {"email": "bob@example.edu", "line": 7, "reason": ""},
            ],
        )
        self.assertEqual(
            parsed["invalid_lines"],
            [
                {
                    "email": "bad address",
                    "line": 6,
                    "reason": "Invalid email syntax",
                },
            ],
        )

    def test_only_first_nonblank_header_is_skipped(self):
        parsed = users.parse_bulk_email_file(
            "s.txt", b"email\nemail\na@example.edu"
        )
        self.assertEqual(parsed["invalid_lines"][0]["line"], 2)
        self.assertEqual(parsed["addresses"][0]["line"], 3)
        parsed = users.parse_bulk_email_file(
            "s.txt", b"bad\nemail\na@example.edu"
        )
        self.assertEqual(
            [item["line"] for item in parsed["invalid_lines"]], [1, 2]
        )

    def test_partial_and_all_invalid_files(self):
        parsed = users.parse_bulk_email_file(
            "s.txt",
            b"a..b@example.edu\na@-example.edu\na@example.edu\na@example.edu\na@example.edu\x00",
        )
        self.assertEqual(len(parsed["addresses"]), 1)
        self.assertEqual(
            [item["line"] for item in parsed["invalid_lines"]], [1, 2, 5]
        )
        self.assertEqual(
            len(
                users.parse_bulk_email_file("s.txt", b"bad\nworse")[
                    "invalid_lines"
                ]
            ),
            2,
        )

    def test_file_rejections(self):
        cases = [
            ("s.csv", b"email,name\na@example.edu,Name"),
            ("s.pdf", b"a@example.edu"),
            ("", b"a@example.edu"),
            ("s.txt", b"\xff"),
            ("s.txt", b""),
            ("s.txt", b" \r\n\t"),
            ("s.txt", b"email\r\n"),
            ("s.txt", b"x" * (users.BULK_EMAIL_MAX_BYTES + 1)),
            ("s.txt", b"a@example.edu\n" * 501),
            ("s.txt", b"bad\n" * 501),
        ]
        with patch.object(
            users,
            "_get_engine",
            side_effect=AssertionError("Parser must never access a database"),
        ):
            for filename, data in cases:
                with self.subTest(filename=filename, size=len(data)):
                    with self.assertRaises(ValueError):
                        users.parse_bulk_email_file(filename, data)

    def test_limits_before_dedup_and_exact_byte_boundary(self):
        parsed = users.parse_bulk_email_file(
            "s.txt", b"email\n" + b"a@example.edu\n" * 500
        )
        self.assertEqual(len(parsed["addresses"]), 1)
        self.assertEqual(
            users.parse_bulk_email_file(
                "s.txt",
                b"a@example.edu\n".ljust(users.BULK_EMAIL_MAX_BYTES, b" "),
            )["addresses"][0]["email"],
            "a@example.edu",
        )

    def test_single_and_bulk_share_syntax_and_normalization(self):
        values = [
            " Alice@Example.edu ",
            "a+b@example.edu",
            "a..b@example.edu",
            "a@example.edu\x00",
            "Name <a@example.edu>",
            "a@example.edu,b@example.edu",
            "a@localhost",
            ".a@example.edu",
        ]
        for value in values:
            with self.subTest(value=value):
                parsed = users.parse_bulk_email_file("s.txt", value.encode())
                if parsed["addresses"]:
                    self.assertEqual(
                        users.normalize_course_email(value),
                        parsed["addresses"][0]["email"],
                    )
                else:
                    with self.assertRaises(ValueError):
                        users.normalize_course_email(value)
        with self.assertRaises(ValueError):
            users.normalize_course_email("email")

    def test_admin_and_faculty_share_result_contract(self):
        data = b"email\nAlice@example.edu\nalice@example.edu\nbad"
        txt = users.parse_bulk_email_file("s.txt", data)
        csv = users.parse_bulk_email_file("s.csv", data)
        self.assertEqual(txt, csv)
        self.assertEqual(
            txt["addresses"],
            [{"email": "alice@example.edu", "line": 2, "reason": ""}],
        )
        self.assertEqual(txt["invalid_lines"][0]["line"], 4)

    def test_faculty_service_rejects_csv_before_database_access(self):
        with patch.object(courses, "_transaction") as transaction:
            with self.assertRaisesRegex(ValueError, r"\.txt"):
                courses.bulk_enroll_course_students(
                    12, 7, "s.csv", b"a@example.edu"
                )
            transaction.assert_not_called()


class CourseAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = patch.object(
            courses,
            "_get_engine",
            side_effect=AssertionError("Live database access forbidden"),
        )
        self.engine.start()
        self.addCleanup(self.engine.stop)

    def test_route_ids_are_positive_ascii_numeric_bigints(self):
        self.assertEqual(courses.parse_course_id("0012"), 12)
        self.assertEqual(
            courses.parse_course_id(9223372036854775807), 9223372036854775807
        )
        for value in (
            0,
            -1,
            True,
            "",
            "-1",
            "12.0",
            "1 OR 1=1",
            " 12",
            "１２",
            "1e2",
            "9223372036854775808",
            [],
            1.0,
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    courses.parse_course_id(value)

    def test_invalid_ids_do_not_start_transactions(self):
        with patch.object(courses, "_transaction") as transaction:
            for value in ("0", "abc", "-2", "9223372036854775808"):
                with self.assertRaises(ValueError):
                    courses.get_faculty_course_detail(12, value)
                with self.assertRaises(ValueError):
                    courses.enroll_course_student(12, value, "a@example.edu")
                with self.assertRaises(ValueError):
                    courses.remove_course_student(12, value, 1)
            transaction.assert_not_called()

    def test_missing_inactive_and_wrong_role_never_read_course_or_write(self):
        # These represent denied identities, never a fabricated authorized session.
        for denied in (
            None,
            SimpleNamespace(role="faculty", status="pending"),
            SimpleNamespace(role="student", status="active"),
            SimpleNamespace(role="faculty", status="rejected"),
        ):
            for operation in (
                lambda: courses.get_faculty_course_detail(12, "7"),
                lambda: courses.enroll_course_student(12, "7", "a@example.edu"),
                lambda: courses.bulk_enroll_course_students(
                    12, "7", "s.txt", b"a@example.edu\nbad"
                ),
                lambda: courses.remove_course_student(12, "7", 1),
            ):
                session = MagicMock()
                session.execute.return_value.first.return_value = denied
                with patch.object(courses, "_transaction") as transaction:
                    transaction.return_value.__enter__.return_value = session
                    with self.assertRaises(PermissionError):
                        operation()
                self.assertEqual(session.execute.call_count, 1)
                sql, params = session.execute.call_args.args
                self.assertIn("FOR SHARE", str(sql))
                self.assertEqual(params["authenticated_faculty_id"], 12)

    def test_sql_ownership_contract_for_reads_and_each_mutation(self):
        scope = courses._COURSE_SCOPE
        self.assertIn("c.id = :course_id", scope)
        self.assertIn("c.faculty_id = :authenticated_faculty_id", scope)
        self.assertIn("f.role = 'faculty'", scope)
        self.assertIn("f.status = 'active'", scope)
        for function in (
            courses._owned_course,
            courses.get_faculty_course_detail,
            courses._enroll_course_addresses,
            courses.remove_course_student,
        ):
            source = inspect.getsource(function)
            self.assertIn("_COURSE_SCOPE", source)
        source = inspect.getsource(courses._enroll_course_addresses)
        self.assertIn("lower(btrim(u.email)) = ANY(:emails)", source)
        self.assertIn("u.role = 'student'", source)
        self.assertIn("u.status = 'active'", source)
        self.assertIn("u.role, u.status", source)
        self.assertIn(
            "ON CONFLICT (course_id, student_id) DO NOTHING RETURNING student_id",
            source,
        )
        self.assertIn("FOR SHARE OF u", source)
        self.assertNotIn("UPDATE public.users", source)
        self.assertNotIn("INSERT INTO public.users", source)
        self.assertIn("_owned_course(session", source)
        self.assertIn(
            "_owned_course(session",
            inspect.getsource(courses.remove_course_student),
        )

    def test_single_and_bulk_enrollment_require_approved_active_students(self):
        account_rows = [
            SimpleNamespace(
                id=21,
                email="active@example.edu",
                role="student",
                status="active",
            ),
            SimpleNamespace(
                id=22,
                email="pending@example.edu",
                role="student",
                status="pending",
            ),
            SimpleNamespace(
                id=23,
                email="rejected@example.edu",
                role="student",
                status="rejected",
            ),
            SimpleNamespace(
                id=24,
                email="faculty@example.edu",
                role="faculty",
                status="active",
            ),
        ]
        expected_groups = {
            "active@example.edu": "added",
            "pending@example.edu": "not_approved",
            "rejected@example.edu": "not_approved",
            "faculty@example.edu": "not_student",
            "missing@example.edu": "no_account",
        }

        def make_session():
            session = MagicMock()
            session.execute.side_effect = [
                MagicMock(
                    first=lambda: SimpleNamespace(
                        role="faculty", status="active"
                    )
                ),
                MagicMock(
                    first=lambda: SimpleNamespace(
                        name="Course", code="CS", term="Fall"
                    )
                ),
                MagicMock(all=lambda: account_rows),
                MagicMock(all=lambda: [SimpleNamespace(student_id=21)]),
            ]
            return session

        for email, expected_group in expected_groups.items():
            session = make_session()
            with (
                self.subTest(single_email=email),
                patch.object(courses, "_transaction") as transaction,
            ):
                transaction.return_value.__enter__.return_value = session
                summary = courses.enroll_course_student(12, "7", email)
            self.assertEqual(
                [item["email"] for item in summary[expected_group]], [email]
            )
            for group in expected_groups.values():
                if group != expected_group:
                    self.assertEqual(
                        [item["email"] for item in summary[group]], []
                    )
            if expected_group == "added":
                insert_sql, insert_params = session.execute.call_args.args
                self.assertIn("u.status = 'active'", str(insert_sql))
                self.assertEqual(insert_params["student_ids"], [21])
            else:
                self.assertEqual(session.execute.call_count, 3)

        session = make_session()
        mixed_addresses = (
            b"active@example.edu\n"
            b"pending@example.edu\n"
            b"rejected@example.edu\n"
            b"faculty@example.edu\n"
            b"missing@example.edu\n"
        )
        with patch.object(courses, "_transaction") as transaction:
            transaction.return_value.__enter__.return_value = session
            summary = courses.bulk_enroll_course_students(
                12, "7", "students.txt", mixed_addresses
            )
        self.assertEqual(
            [item["email"] for item in summary["added"]],
            ["active@example.edu"],
        )
        self.assertEqual(
            [item["email"] for item in summary["not_approved"]],
            ["pending@example.edu", "rejected@example.edu"],
        )
        self.assertEqual(
            [item["email"] for item in summary["not_student"]],
            ["faculty@example.edu"],
        )
        self.assertEqual(
            [item["email"] for item in summary["no_account"]],
            ["missing@example.edu"],
        )
        self.assertEqual(summary["already_enrolled"], [])
        insert_sql, insert_params = session.execute.call_args.args
        self.assertIn("u.status = 'active'", str(insert_sql))
        self.assertEqual(insert_params["student_ids"], [21])
        self.assertNotIn(22, insert_params["student_ids"])
        self.assertNotIn(23, insert_params["student_ids"])

    def test_ambiguous_case_variants_are_never_enrolled(self):
        session = MagicMock()
        session.execute.side_effect = [
            MagicMock(
                first=lambda: SimpleNamespace(role="faculty", status="active")
            ),
            MagicMock(
                first=lambda: SimpleNamespace(
                    name="Course", code="CS", term="Fall"
                )
            ),
            MagicMock(
                all=lambda: [
                    SimpleNamespace(
                        id=21,
                        email="Alice@example.edu",
                        role="student",
                        status="active",
                    ),
                    SimpleNamespace(
                        id=22,
                        email="alice@example.edu",
                        role="student",
                        status="active",
                    ),
                ]
            ),
        ]
        with patch.object(courses, "_transaction") as transaction:
            transaction.return_value.__enter__.return_value = session
            summary = courses.bulk_enroll_course_students(
                12, 7, "s.txt", b" ALICE@example.edu \nalice@example.edu\nbad"
            )
        self.assertEqual(summary["added"], [])
        self.assertEqual(len(summary["not_student"]), 1)
        self.assertIn("Ambiguous", summary["not_student"][0]["reason"])
        self.assertEqual(summary["invalid_lines"][0]["line"], 3)
        self.assertEqual(session.execute.call_count, 3)
        self.assertEqual(
            session.execute.call_args.args[1]["emails"], ["alice@example.edu"]
        )

    def test_all_invalid_checks_ownership_without_account_reads_or_writes(self):
        session = MagicMock()
        session.execute.side_effect = [
            MagicMock(
                first=lambda: SimpleNamespace(role="faculty", status="active")
            ),
            MagicMock(
                first=lambda: SimpleNamespace(
                    name="Course", code="CS", term="Fall"
                )
            ),
        ]
        with patch.object(courses, "_transaction") as transaction:
            transaction.return_value.__enter__.return_value = session
            summary = courses.bulk_enroll_course_students(
                12, 7, "s.txt", b"bad\nworse"
            )
        self.assertEqual(len(summary["invalid_lines"]), 2)
        self.assertEqual(summary["added"], [])
        self.assertEqual(session.execute.call_count, 2)

    def test_direct_invalid_addresses_fail_before_transaction(self):
        with patch.object(courses, "_transaction") as transaction:
            for entries in (
                [],
                [{"email": "bad", "line": 1, "reason": ""}],
                [{"email": "a@example.edu", "line": 1, "reason": ""}] * 501,
            ):
                with self.assertRaises(ValueError):
                    courses._enroll_course_addresses(
                        12, 7, {"addresses": entries, "invalid_lines": []}
                    )
            transaction.assert_not_called()

    def test_direct_mixed_case_duplicate_entries_enroll_only_once(self):
        session = MagicMock()
        session.execute.side_effect = [
            MagicMock(
                first=lambda: SimpleNamespace(role="faculty", status="active")
            ),
            MagicMock(
                first=lambda: SimpleNamespace(
                    name="Course", code="CS", term="Fall"
                )
            ),
            MagicMock(
                all=lambda: [
                    SimpleNamespace(
                        id=21,
                        email="Alice@Example.edu",
                        role="student",
                        status="active",
                    )
                ]
            ),
            MagicMock(all=lambda: [SimpleNamespace(student_id=21)]),
        ]
        with patch.object(courses, "_transaction") as transaction:
            transaction.return_value.__enter__.return_value = session
            summary = courses._enroll_course_addresses(
                12,
                7,
                {
                    "addresses": [
                        {
                            "email": " Alice@Example.edu ",
                            "line": 2,
                            "reason": "",
                        },
                        {"email": "alice@example.edu", "line": 3, "reason": ""},
                    ],
                    "invalid_lines": [],
                },
            )
        self.assertEqual(
            summary["added"],
            [{"email": "alice@example.edu", "line": 2, "reason": ""}],
        )
        self.assertEqual(session.execute.call_args.args[1]["student_ids"], [21])


class CourseDetailAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_guard_rejects_signed_out_events_without_database(self):
        state = CourseStateHarness()
        state._perform_course_action = (
            FacultyState._perform_course_action.__get__(state)
        )
        state.router = SimpleNamespace(
            page=SimpleNamespace(path="/faculty/course/7", params={"id": "7"})
        )
        state.login.signed_in = False
        state.login._session_user_id = 0
        for event, args in (
            (FacultyState.load_course_detail, ()),
            (
                FacultyState.add_course_student,
                ({"email": "a@example.edu", "faculty_id": 999},),
            ),
            (FacultyState.remove_enrolled_student, (1,)),
            (FacultyState.process_course_upload, ("token",)),
            (FacultyState.upload_course_emails, ([],)),
        ):
            state.course_detail = {
                "name": "Private",
                "code": "CS",
                "term": "Fall",
            }
            state.enrollment_has_summary = True
            with patch(
                "UniFlow_.states.role_guard.get_user_by_id",
                side_effect=AssertionError(
                    "No identity means no database lookup"
                ),
            ) as lookup:
                await consume(event.fn(state, *args))
                lookup.assert_not_called()
            self.assertEqual(
                state.course_detail, {"name": "", "code": "", "term": ""}
            )
            self.assertEqual(state.enrolled_students, [])
            self.assertFalse(state.enrollment_has_summary)
            self.assertFalse(state.enrollment_busy)

    def test_course_route_is_excluded_from_project_loader(self):
        source = inspect.getsource(FacultyState.load_faculty.fn)
        self.assertIn('path.startswith("/faculty/course/")', source)
        self.assertLess(
            source.index('path.startswith("/faculty/course/")'),
            source.index("get_faculty_projects()"),
        )


if __name__ == "__main__":
    unittest.main()
