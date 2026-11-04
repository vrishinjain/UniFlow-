import reflex as rx

import re
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

from UniFlow_ import project_services as projects
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.student_state import (
    StudentProjectsState,
    StudentProjectDetailState,
)


# Independent SQL contract: changing the application's shared predicate must
# not silently change what the fake considers authorized.
VISIBILITY = """
    p.status = 'accepted'
    AND EXISTS (
        SELECT 1 FROM public.users AS u
        WHERE u.id = :student_id
          AND u.role = 'student'
          AND u.status = 'active'
          AND u.must_change_password = FALSE
    )
    AND EXISTS (
        SELECT 1 FROM public.project_course_visibility AS v
        JOIN public.course_enrollments AS e ON e.course_id = v.course_id
        WHERE v.project_id = p.id AND e.student_id = :student_id
    )
"""


def normalize(sql):
    return " ".join(str(sql).split())


QUERIES = {
    "account": normalize("""
        SELECT id FROM public.users WHERE id = :student_id
        AND role = 'student' AND status = 'active'
        AND must_change_password = FALSE
    """),
    "list": normalize(f"""
        SELECT p.id, p.title, p.description
        FROM public.projects AS p WHERE {VISIBILITY}
        ORDER BY p.created_at DESC, p.id DESC
    """),
    "detail": normalize(f"""
        SELECT p.id, p.title, p.description,
               f.id AS file_id, f.filename, f.uploaded_at
        FROM public.projects AS p
        LEFT JOIN public.project_files AS f ON f.project_id = p.id
        WHERE p.id = :project_id AND {VISIBILITY}
        ORDER BY f.uploaded_at, f.id
    """),
    "file": normalize(f"""
        SELECT f.filename, f.data FROM public.project_files AS f
        JOIN public.projects AS p ON p.id = f.project_id
        WHERE f.id = :file_id AND f.project_id = :project_id
        AND {VISIBILITY}
    """),
}


class RelationalFixture:
    """Only Python records; no SQL driver, URL, ORM session or disk storage."""

    def __init__(self):
        self.users = {}
        identities = (
            (21, "student", "active", False),
            (22, "student", "active", False),
            (23, "faculty", "active", False),
            (24, "sponsor", "active", False),
            (25, "student", "pending", False),
            (26, "student", "rejected", False),
            (27, "student", "active", True),
            (28, "student", "active", False),
        )
        for user_id, role, status, password_change in identities:
            self.users[user_id] = {
                "id": user_id,
                "role": role,
                "status": status,
                "must_change_password": password_change,
            }
        self.projects = {}
        for project_id, status, description in (
            (101, "accepted", "Shared design brief"),
            (102, "accepted", None),
            (103, "pending", "Not yet accepted"),
            (104, "accepted", "Unshared private brief"),
            (105, "accepted", "Other course only"),
            (106, "rejected", "Rejected brief"),
            (107, "revision_requested", "Needs changes"),
        ):
            self.projects[project_id] = {
                "id": project_id,
                "title": f"Project {project_id}",
                "description": description,
                "status": status,
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }
        # Repeated and multiple matching shares exercise EXISTS semantics.
        self.project_course_visibility = [
            {"project_id": project_id, "course_id": course_id}
            for project_id, course_id in (
                (101, 7),
                (101, 7),
                (101, 8),
                (102, 7),
                (103, 7),
                (105, 9),
                (106, 7),
                (107, 7),
            )
        ]
        self.course_enrollments = [
            {"student_id": user_id, "course_id": course_id}
            for user_id, course_id in (
                (21, 7),
                (21, 8),
                (22, 9),
                (23, 7),
                (24, 7),
                (25, 7),
                (26, 7),
                (27, 7),
            )
        ]
        self.project_files = {}
        for file_id, project_id, filename, uploaded_at in (
            (
                501,
                101,
                "brief.pdf",
                datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc),
            ),
            (502, 101, "notes.pdf", None),
            (503, 103, "pending.pdf", None),
            (504, 104, "private.pdf", None),
            (505, 105, "other-course.pdf", None),
            (506, 106, "rejected.pdf", None),
            (507, 107, "revision.pdf", None),
        ):
            data = f"%PDF-1.7\nfixture attachment {file_id}".encode("ascii")
            self.project_files[file_id] = {
                "id": file_id,
                "project_id": project_id,
                "filename": filename,
                "content_type": "application/pdf",
                "size_bytes": len(data),
                "data": memoryview(data),
                "uploaded_at": uploaded_at,
            }

    def active_student(self, student_id):
        account = self.users.get(student_id)
        return bool(
            account
            and account["role"] == "student"
            and account["status"] == "active"
            and account["must_change_password"] is False
        )

    def visible(self, student_id, project_id):
        project = self.projects.get(project_id)
        if not self.active_student(student_id) or not project:
            return False
        if project["status"] != "accepted":
            return False
        enrolled = {
            row["course_id"]
            for row in self.course_enrollments
            if row["student_id"] == student_id
        }
        return any(
            row["project_id"] == project_id and row["course_id"] in enrolled
            for row in self.project_course_visibility
        )

    def remove_enrollment(self, student_id, course_id):
        self.course_enrollments[:] = [
            row
            for row in self.course_enrollments
            if (row["student_id"], row["course_id"]) != (student_id, course_id)
        ]

    def lookup_account(self, user_id):
        row = self.users.get(user_id)
        return SimpleNamespace(**row) if row else None


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, engine):
        self.engine = engine
        self.entered = False

    def __enter__(self):
        if self.entered:
            raise AssertionError("Connection context entered twice")
        self.entered = True
        self.engine.open_contexts += 1
        return self

    def __exit__(self, *args):
        self.entered = False
        self.engine.open_contexts -= 1
        return False

    def execute(self, statement, params):
        try:
            if not self.entered:
                raise AssertionError("Execute outside connection context")
            if not isinstance(statement, TextClause):
                raise AssertionError("Expected parameterized sqlalchemy.text")
            sql = normalize(statement)
            kind = next(
                (name for name, query in QUERIES.items() if query == sql), None
            )
            if kind is None:
                raise AssertionError(f"Unexpected SQL: {sql}")
            bindings = set(re.findall(r":([a-z_]+)", sql))
            if set(params) != bindings:
                raise AssertionError(
                    f"Wrong bindings: {params}; expected {bindings}"
                )
            if any(
                type(value) is not int or value <= 0
                for value in params.values()
            ):
                raise AssertionError(
                    f"IDs must be bound positive integers: {params}"
                )
            self.engine.calls.append((kind, sql, dict(params)))
            return FakeResult(self.evaluate(kind, params))
        except AssertionError as error:
            # State events catch general exceptions; retain violations so teardown
            # fails even if an event turns one into a friendly loading error.
            self.engine.violations.append(str(error))
            raise

    def evaluate(self, kind, params):
        fixture = self.engine.fixture
        student_id = params["student_id"]
        if kind == "account":
            return (
                [SimpleNamespace(id=student_id)]
                if fixture.active_student(student_id)
                else []
            )
        if kind == "list":
            ordered = sorted(
                fixture.projects.values(),
                key=lambda row: (row["created_at"], row["id"]),
                reverse=True,
            )
            return [
                {key: row[key] for key in ("id", "title", "description")}
                for row in ordered
                if fixture.visible(student_id, row["id"])
            ]
        project_id = params["project_id"]
        if not fixture.visible(student_id, project_id):
            return []
        if kind == "file":
            attachment = fixture.project_files.get(params["file_id"])
            if attachment is None or attachment["project_id"] != project_id:
                return []
            return [{key: attachment[key] for key in ("filename", "data")}]
        project = fixture.projects[project_id]
        base = {key: project[key] for key in ("id", "title", "description")}
        attachments = sorted(
            (
                row
                for row in fixture.project_files.values()
                if row["project_id"] == project_id
            ),
            key=lambda row: (
                row["uploaded_at"] is None,
                row["uploaded_at"] or datetime.max.replace(tzinfo=timezone.utc),
                row["id"],
            ),
        )
        if not attachments:
            return [
                {**base, "file_id": None, "filename": None, "uploaded_at": None}
            ]
        return [
            {
                **base,
                "file_id": row["id"],
                "filename": row["filename"],
                "uploaded_at": row["uploaded_at"],
            }
            for row in attachments
        ]


class FakeEngine:
    def __init__(self, fixture):
        self.fixture = fixture
        self.calls = []
        self.violations = []
        self.open_contexts = 0

    def connect(self):
        return FakeConnection(self)


class OfflineTests:
    """Install per-test fail-closed barriers, including real SQLAlchemy I/O."""

    def setUp(self):
        self.fixture = RelationalFixture()
        self.engine = FakeEngine(self.fixture)
        self.forbidden_attempts = []
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)

        def forbidden(*args, **kwargs):
            self.forbidden_attempts.append(
                "Real database/transaction attempted"
            )
            raise AssertionError(self.forbidden_attempts[-1])

        for target in (
            "UniFlow_.user_services._get_engine",
            "UniFlow_.user_services._transaction",
            "UniFlow_.user_services.create_engine",
            "UniFlow_.project_services._transaction",
            "UniFlow_.review_services._transaction",
            "sqlalchemy.create_engine",
            "sqlalchemy.engine.Engine.connect",
            "sqlalchemy.engine.Engine.begin",
            "sqlalchemy.engine.Connection.execute",
        ):
            self.stack.enter_context(patch(target, side_effect=forbidden))
        self.get_engine = self.stack.enter_context(
            patch.object(projects, "_get_engine", return_value=self.engine)
        )

    def tearDown(self):
        self.assertEqual(self.forbidden_attempts, [])
        self.assertEqual(self.engine.violations, [])
        self.assertEqual(self.engine.open_contexts, 0)


class StudentServiceAccessTests(OfflineTests, unittest.TestCase):
    def test_shared_predicate_and_parameterized_sql_contract(self):
        self.assertEqual(
            normalize(projects._STUDENT_PROJECT_VISIBILITY),
            normalize(VISIBILITY),
        )
        for clause in (
            "p.status = 'accepted'",
            "u.role = 'student'",
            "u.status = 'active'",
            "u.must_change_password = FALSE",
            "u.id = :student_id",
            "JOIN public.course_enrollments AS e ON e.course_id = v.course_id",
            "v.project_id = p.id AND e.student_id = :student_id",
        ):
            self.assertIn(
                clause, normalize(projects._STUDENT_PROJECT_VISIBILITY)
            )
        projects.list_shared_projects_for_student(21)
        projects.get_shared_project_for_student(21, 101)
        projects.get_shared_project_file_for_student(21, 101, 501)
        self.assertEqual(
            [call[0] for call in self.engine.calls],
            ["account", "list", "detail", "file"],
        )
        self.assertEqual(
            [call[2] for call in self.engine.calls],
            [
                {"student_id": 21},
                {"student_id": 21},
                {"student_id": 21, "project_id": 101},
                {"student_id": 21, "project_id": 101, "file_id": 501},
            ],
        )
        for kind, sql, params in self.engine.calls:
            for value in params.values():
                self.assertNotRegex(sql, rf"\b{value}\b")
            if kind != "account":
                self.assertIn(
                    normalize(projects._STUDENT_PROJECT_VISIBILITY), sql
                )
        self.assertIn("f.project_id = p.id", self.engine.calls[2][1])
        self.assertIn("p.id = f.project_id", self.engine.calls[3][1])
        self.assertIn(
            "f.id = :file_id AND f.project_id = :project_id",
            self.engine.calls[3][1],
        )

    def test_list_filters_and_deduplicates_with_current_student_identity(self):
        self.assertEqual(
            projects.list_shared_projects_for_student(21),
            [
                {"id": "102", "title": "Project 102", "description": ""},
                {
                    "id": "101",
                    "title": "Project 101",
                    "description": "Shared design brief",
                },
            ],
        )
        self.assertEqual(
            [
                row["id"]
                for row in projects.list_shared_projects_for_student(22)
            ],
            ["105"],
        )
        self.assertEqual(projects.list_shared_projects_for_student(28), [])

    def test_direct_guessed_pending_unshared_and_other_course_projects_are_denied(
        self,
    ):
        for project_id in (103, 104, 105, 106, 107, 999):
            with self.subTest(project_id=project_id):
                self.assertIsNone(
                    projects.get_shared_project_for_student(21, project_id)
                )
        self.assertIsNone(projects.get_shared_project_for_student(22, 101))
        self.assertIsNone(projects.get_shared_project_for_student(28, 101))

    def test_detail_metadata_excludes_bytes_and_handles_no_files(self):
        detail = projects.get_shared_project_for_student(21, 101)
        self.assertEqual(
            detail,
            {
                "id": "101",
                "title": "Project 101",
                "description": "Shared design brief",
                "files": [
                    {
                        "id": "501",
                        "filename": "brief.pdf",
                        "uploaded_at": "Jan 02, 2026 10:30 AM UTC",
                    },
                    {
                        "id": "502",
                        "filename": "notes.pdf",
                        "uploaded_at": "Upload date unavailable",
                    },
                ],
            },
        )
        self.assertNotIn("f.data", self.engine.calls[-1][1])
        self.assertEqual(
            projects.get_shared_project_for_student(21, 102),
            {
                "id": "102",
                "title": "Project 102",
                "description": "",
                "files": [],
            },
        )

    def test_authorized_attachment_bytes_and_scoped_denials(self):
        attachment = projects.get_shared_project_file_for_student(21, 101, 501)
        self.assertEqual(
            attachment,
            {
                "filename": "brief.pdf",
                "data": bytes(self.fixture.project_files[501]["data"]),
            },
        )
        self.assertIs(type(attachment["data"]), bytes)
        for student_id, project_id, file_id in (
            (21, 101, 999),
            (21, 101, 505),
            (21, 102, 501),
            (21, 103, 503),
            (21, 104, 504),
            (21, 105, 505),
            (21, 106, 506),
            (21, 107, 507),
            (21, 999, 501),
            (22, 101, 501),
            (28, 101, 501),
        ):
            with self.subTest(
                student=student_id, project=project_id, file=file_id
            ):
                self.assertIsNone(
                    projects.get_shared_project_file_for_student(
                        student_id, project_id, file_id
                    )
                )
        self.assertEqual(
            projects.get_shared_project_file_for_student(22, 105, 505)[
                "filename"
            ],
            "other-course.pdf",
        )

    def test_enrollment_removal_revokes_all_access_without_cached_results(self):
        self.assertIsNotNone(projects.get_shared_project_for_student(21, 101))
        self.assertIsNotNone(
            projects.get_shared_project_file_for_student(21, 101, 501)
        )
        self.fixture.remove_enrollment(21, 7)
        self.assertEqual(
            [
                row["id"]
                for row in projects.list_shared_projects_for_student(21)
            ],
            ["101"],
        )
        self.assertIsNone(projects.get_shared_project_for_student(21, 102))
        self.fixture.remove_enrollment(21, 8)
        self.assertEqual(projects.list_shared_projects_for_student(21), [])
        self.assertIsNone(projects.get_shared_project_for_student(21, 101))
        self.assertIsNone(
            projects.get_shared_project_file_for_student(21, 101, 501)
        )
        self.assertEqual(
            [
                row["id"]
                for row in projects.list_shared_projects_for_student(22)
            ],
            ["105"],
        )

    def test_wrong_role_inactive_password_change_and_missing_users_denied(self):
        for student_id in (23, 24, 25, 26, 27, 999):
            with self.subTest(student_id=student_id):
                start = len(self.engine.calls)
                with (
                    self.assertLogs(level="ERROR"),
                    self.assertRaises(PermissionError),
                ):
                    projects.list_shared_projects_for_student(student_id)
                self.assertEqual(
                    [call[0] for call in self.engine.calls[start:]], ["account"]
                )
                self.assertIsNone(
                    projects.get_shared_project_for_student(student_id, 101)
                )
                self.assertIsNone(
                    projects.get_shared_project_file_for_student(
                        student_id, 101, 501
                    )
                )

    def test_status_and_sharing_changes_are_rechecked(self):
        self.fixture.projects[101]["status"] = "pending"
        self.assertIsNone(projects.get_shared_project_for_student(21, 101))
        self.assertIsNone(
            projects.get_shared_project_file_for_student(21, 101, 501)
        )
        self.fixture.projects[101]["status"] = "accepted"
        self.fixture.project_course_visibility[:] = [
            row
            for row in self.fixture.project_course_visibility
            if row["project_id"] != 101
        ]
        self.assertEqual(
            [
                row["id"]
                for row in projects.list_shared_projects_for_student(21)
            ],
            ["102"],
        )
        self.assertIsNone(projects.get_shared_project_for_student(21, 101))
        self.assertIsNone(
            projects.get_shared_project_file_for_student(21, 101, 501)
        )

    def test_invalid_ids_fail_before_connection(self):
        for value in (0, -1, True, "21", 1.5, 9223372036854775808):
            with self.subTest(value=value):
                for operation in (
                    lambda: projects.list_shared_projects_for_student(value),
                    lambda: projects.get_shared_project_for_student(value, 101),
                    lambda: projects.get_shared_project_for_student(21, value),
                    lambda: projects.get_shared_project_file_for_student(
                        value, 101, 501
                    ),
                    lambda: projects.get_shared_project_file_for_student(
                        21, value, 501
                    ),
                    lambda: projects.get_shared_project_file_for_student(
                        21, 101, value
                    ),
                ):
                    with self.assertRaises(ValueError):
                        operation()
        self.get_engine.assert_not_called()

    def test_fake_rejects_unexpected_or_unparameterized_sql(self):
        # Separate fake: these deliberately induced violations are not swallowed.
        engine = FakeEngine(RelationalFixture())
        with engine.connect() as connection:
            for sql, params in (
                ("SELECT * FROM public.projects", {"student_id": 21}),
                (
                    QUERIES["file"].replace(
                        "f.project_id = :project_id", "TRUE"
                    ),
                    {"student_id": 21, "project_id": 101, "file_id": 501},
                ),
                (QUERIES["list"], {"student_id": 22, "extra": 1}),
                (QUERIES["list"].replace(":student_id", "21"), {}),
            ):
                with self.subTest(sql=sql), self.assertRaises(AssertionError):
                    connection.execute(text(sql), params)
        self.assertEqual(len(engine.violations), 4)
        self.assertEqual(engine.calls, [])


class StudentHarness:
    def __init__(self, route_id="101"):
        self._load_request = 0
        self.login = SimpleNamespace(
            signed_in=True,
            _session_user_id=21,
            role="student",
            must_change_password=False,
        )
        self.router = SimpleNamespace(
            page=SimpleNamespace(
                path=f"/student/projects/{route_id}",
                params={"project_id": route_id},
            )
        )
        self._clear_access()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_state(self, state_class):
        if state_class is not LoginState:
            raise AssertionError("Unexpected state lookup")
        return self.login


class ProjectsHarness(StudentHarness):
    _clear_access = StudentProjectsState._clear_access
    _session_matches = StudentProjectsState._session_matches

    def __init__(self):
        super().__init__()
        self.router.page.path = "/student/projects"
        self.router.page.params = {}


class DetailHarness(StudentHarness):
    _clear_access = StudentProjectDetailState._clear_access
    _session_matches = StudentProjectDetailState._session_matches


async def consume(generator):
    return [event async for event in generator]


class StudentEventAccessTests(OfflineTests, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.lookup = self.stack.enter_context(
            patch(
                "UniFlow_.states.role_guard.get_user_by_id",
                side_effect=self.fixture.lookup_account,
            )
        )
        self.redirect = self.stack.enter_context(
            patch.object(
                rx,
                "redirect",
                side_effect=lambda url: ("redirect", url),
            )
        )
        self.download = self.stack.enter_context(
            patch.object(
                rx,
                "download",
                return_value=("download",),
            )
        )

    def assert_detail_cleared(self, state):
        self.assertEqual(
            (state.title, state.description, state.selected_project_id),
            ("", "", ""),
        )
        self.assertEqual(state.files, [])
        self.assertFalse(state.authorized)
        self.assertFalse(state.ready)
        self.assertFalse(state.loading)
        self.assertEqual(state.error, "")
        self.assertEqual(state.downloading_file_id, "")

    def seed_private_detail(self, state):
        state.title = "Previously visible title"
        state.description = "Previously visible description"
        state.files = [
            {
                "id": "501",
                "filename": "private.pdf",
                "uploaded_at": "Private date",
            }
        ]
        state.selected_project_id = str(state.router.page.params["project_id"])
        state.authorized = True
        state.ready = True
        state.loading = False

    async def test_authorized_list_detail_and_download_use_real_services(self):
        listing = ProjectsHarness()
        self.assertEqual(
            await consume(
                StudentProjectsState.load_student_projects.fn(listing)
            ),
            [],
        )
        self.assertEqual(
            [row["id"] for row in listing.projects], ["102", "101"]
        )
        self.assertTrue(listing.authorized)
        self.assertFalse(listing.loading)
        state = DetailHarness()
        self.assertEqual(
            await consume(
                StudentProjectDetailState.load_student_project_detail.fn(state)
            ),
            [],
        )
        self.assertTrue(state.ready)
        self.assertTrue(state.authorized)
        self.assertEqual(state.selected_project_id, "101")
        self.assertEqual([row["id"] for row in state.files], ["501", "502"])
        events = await consume(
            StudentProjectDetailState.download_file.fn(state, "501")
        )
        self.assertEqual(events, [("download",)])
        self.download.assert_called_once_with(
            data=bytes(self.fixture.project_files[501]["data"]),
            filename="brief.pdf",
        )
        self.assertEqual(state.downloading_file_id, "")
        self.assertEqual(
            self.engine.calls[-1][2],
            {"student_id": 21, "project_id": 101, "file_id": 501},
        )
        self.redirect.assert_not_called()

    async def test_denied_login_never_calls_lookup_or_project_services(self):
        for changes, destination in (
            ({"signed_in": False, "_session_user_id": 0}, "/"),
            ({"_session_user_id": 0}, "/"),
            ({"role": "faculty"}, "/"),
            ({"role": "sponsor"}, "/"),
            ({"must_change_password": True}, "/set-password"),
        ):
            for mode in ("list", "detail", "file"):
                with self.subTest(changes=changes, event=mode):
                    self.lookup.reset_mock()
                    self.redirect.reset_mock()
                    state = (
                        ProjectsHarness() if mode == "list" else DetailHarness()
                    )
                    for key, value in changes.items():
                        setattr(state.login, key, value)
                    if mode == "list":
                        state.projects = [
                            {
                                "id": "101",
                                "title": "Private",
                                "description": "Private",
                            }
                        ]
                        state.authorized = True
                        handler, args = (
                            StudentProjectsState.load_student_projects,
                            (),
                        )
                    else:
                        self.seed_private_detail(state)
                        handler, args = (
                            (
                                StudentProjectDetailState.load_student_project_detail,
                                (),
                            )
                            if mode == "detail"
                            else (
                                StudentProjectDetailState.download_file,
                                ("501",),
                            )
                        )
                    with (
                        patch(
                            "UniFlow_.states.student_state.list_shared_projects_for_student"
                        ) as listing,
                        patch(
                            "UniFlow_.states.student_state.get_shared_project_for_student"
                        ) as detail,
                        patch(
                            "UniFlow_.states.student_state.get_shared_project_file_for_student"
                        ) as attachment,
                    ):
                        events = await consume(handler.fn(state, *args))
                        listing.assert_not_called()
                        detail.assert_not_called()
                        attachment.assert_not_called()
                    self.assertEqual(events, [("redirect", destination)])
                    self.lookup.assert_not_called()
                    if mode == "list":
                        self.assertEqual(state.projects, [])
                        self.assertFalse(state.authorized)
                        self.assertFalse(state.loading)
                        self.assertEqual(state.error, "")
                    else:
                        self.assert_detail_cleared(state)
        self.get_engine.assert_not_called()
        self.download.assert_not_called()

    async def test_persisted_wrong_role_inactive_or_missing_account_redirects(
        self,
    ):
        for user_id in (23, 24, 25, 26, 999):
            for mode in ("list", "detail", "file"):
                with self.subTest(user_id=user_id, event=mode):
                    state = (
                        ProjectsHarness() if mode == "list" else DetailHarness()
                    )
                    state.login._session_user_id = user_id
                    # Stale client session still claims student; real guard checks fixture.
                    if mode == "list":
                        handler, args = (
                            StudentProjectsState.load_student_projects,
                            (),
                        )
                    else:
                        self.seed_private_detail(state)
                        handler, args = (
                            (
                                StudentProjectDetailState.load_student_project_detail,
                                (),
                            )
                            if mode == "detail"
                            else (
                                StudentProjectDetailState.download_file,
                                ("501",),
                            )
                        )
                    self.assertEqual(
                        await consume(handler.fn(state, *args)),
                        [("redirect", "/")],
                    )
                    if mode == "list":
                        self.assertEqual(state.projects, [])
                        self.assertFalse(state.authorized)
                    else:
                        self.assert_detail_cleared(state)
        self.get_engine.assert_not_called()
        self.download.assert_not_called()

    async def test_direct_url_denials_clear_previous_detail_and_redirect(self):
        for route_id in (
            "103",
            "104",
            "105",
            "106",
            "107",
            "999",
            "0",
            "bad",
            "1 OR 1=1",
        ):
            with self.subTest(route_id=route_id):
                state = DetailHarness(route_id)
                self.seed_private_detail(state)
                if route_id in ("0", "bad", "1 OR 1=1"):
                    with self.assertLogs(level="ERROR"):
                        events = await consume(
                            StudentProjectDetailState.load_student_project_detail.fn(
                                state
                            )
                        )
                else:
                    events = await consume(
                        StudentProjectDetailState.load_student_project_detail.fn(
                            state
                        )
                    )
                self.assertEqual(events, [("redirect", "/student")])
                self.assert_detail_cleared(state)
        self.download.assert_not_called()

    async def test_wrong_attachment_ids_and_removed_enrollment_do_not_download(
        self,
    ):
        for route_id, file_id in (
            ("101", "999"),
            ("101", "505"),
            ("102", "501"),
            ("104", "504"),
        ):
            with self.subTest(route_id=route_id, file_id=file_id):
                state = DetailHarness(route_id)
                self.seed_private_detail(state)
                events = await consume(
                    StudentProjectDetailState.download_file.fn(state, file_id)
                )
                self.assertEqual(events, [("redirect", "/student")])
                self.assert_detail_cleared(state)
        state = DetailHarness()
        await consume(
            StudentProjectDetailState.load_student_project_detail.fn(state)
        )
        self.fixture.remove_enrollment(21, 7)
        self.fixture.remove_enrollment(21, 8)
        self.assertEqual(
            await consume(
                StudentProjectDetailState.download_file.fn(state, "501")
            ),
            [("redirect", "/student")],
        )
        self.assert_detail_cleared(state)
        listing = ProjectsHarness()
        await consume(StudentProjectsState.load_student_projects.fn(listing))
        self.assertEqual(listing.projects, [])
        self.assertEqual(
            await consume(
                StudentProjectDetailState.load_student_project_detail.fn(state)
            ),
            [("redirect", "/student")],
        )
        self.assert_detail_cleared(state)
        self.download.assert_not_called()

    async def test_download_requires_ready_authorized_matching_url_and_no_inflight(
        self,
    ):
        for field, value in (
            ("ready", False),
            ("authorized", False),
            ("selected_project_id", "105"),
            ("downloading_file_id", "502"),
        ):
            with self.subTest(field=field):
                state = DetailHarness()
                self.seed_private_detail(state)
                setattr(state, field, value)
                self.assertEqual(
                    await consume(
                        StudentProjectDetailState.download_file.fn(state, "501")
                    ),
                    [],
                )
        self.lookup.assert_not_called()
        self.get_engine.assert_not_called()
        self.download.assert_not_called()
        self.redirect.assert_not_called()

    async def test_logout_during_service_read_discards_list_detail_and_download(
        self,
    ):
        for handler, service_name, actual_service, args, mode in (
            (
                StudentProjectsState.load_student_projects,
                "list_shared_projects_for_student",
                projects.list_shared_projects_for_student,
                (),
                "list",
            ),
            (
                StudentProjectDetailState.load_student_project_detail,
                "get_shared_project_for_student",
                projects.get_shared_project_for_student,
                (),
                "detail",
            ),
            (
                StudentProjectDetailState.download_file,
                "get_shared_project_file_for_student",
                projects.get_shared_project_file_for_student,
                ("501",),
                "file",
            ),
        ):
            with self.subTest(event=mode):
                state = ProjectsHarness() if mode == "list" else DetailHarness()
                if mode == "file":
                    self.seed_private_detail(state)

                def read_then_logout(*ids):
                    result = actual_service(*ids)
                    state.login.signed_in = False
                    return result

                with patch(
                    f"UniFlow_.states.student_state.{service_name}",
                    side_effect=read_then_logout,
                ) as service:
                    events = await consume(handler.fn(state, *args))
                service.assert_called_once()
                self.assertEqual(events, [("redirect", "/")])
                if mode == "list":
                    self.assertEqual(state.projects, [])
                    self.assertFalse(state.authorized)
                else:
                    self.assert_detail_cleared(state)
        self.download.assert_not_called()

    async def test_detail_url_change_during_read_discards_late_metadata(self):
        state = DetailHarness()

        def change_route_after_read(student_id, project_id):
            result = projects.get_shared_project_for_student(
                student_id, project_id
            )
            state.router.page.path = "/student/projects/105"
            state.router.page.params["project_id"] = "105"
            return result

        with patch(
            "UniFlow_.states.student_state.get_shared_project_for_student",
            side_effect=change_route_after_read,
        ) as service:
            self.assertEqual(
                await consume(
                    StudentProjectDetailState.load_student_project_detail.fn(
                        state
                    )
                ),
                [],
            )
        service.assert_called_once_with(21, 101)
        self.assertEqual(
            (state.title, state.description, state.selected_project_id),
            ("", "", ""),
        )
        self.assertEqual(state.files, [])
        self.assertFalse(state.ready)
        self.assertFalse(state.authorized)
        self.download.assert_not_called()
        self.redirect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
