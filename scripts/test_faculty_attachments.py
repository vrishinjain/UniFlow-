import reflex as rx

import base64
import json
import threading
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from UniFlow_ import project_services
from UniFlow_.components.faculty import _file_row, faculty_project_details
from UniFlow_.states.faculty_state import FacultyState


class FacultyHarness(SimpleNamespace):
    def __init__(self, route_id="42", selected_id="42"):
        super().__init__(
            router=SimpleNamespace(
                page=SimpleNamespace(params={"id": route_id})
            ),
            selected_project={"id": selected_id},
            files=[],
            projects=[],
            project_error="",
            full_name="",
            _authorized=True,
            _load_version=0,
        )
        self.locked = False

    async def __aenter__(self):
        self.locked = True
        return self

    async def __aexit__(self, *args):
        self.locked = False

    def _clear_access(self):
        FacultyState._clear_access(self)


async def collect(handler, state, *args):
    return [event async for event in handler.fn(state, *args)]


def event_args(event):
    return {str(key): json.loads(str(value)) for key, value in event.args}


def project_details():
    return {
        "id": "42",
        "title": "Project",
        "description": "Description",
        "sponsor_name": "Sponsor",
        "created_at": "",
        "status": "submitted",
        "files": [{"id": "7", "filename": "brief.pdf", "size_bytes": 12}],
    }


class FacultyEventTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.state = FacultyHarness()
        self.account = SimpleNamespace(id=3, full_name="Faculty")
        self.guard = AsyncMock(return_value=(self.account, ""))
        guard_patch = patch(
            "UniFlow_.states.faculty_state.check_dashboard_access", self.guard
        )
        guard_patch.start()
        self.addCleanup(guard_patch.stop)
        engine_patch = patch(
            "UniFlow_.user_services._get_engine",
            side_effect=AssertionError("Live database access forbidden"),
        )
        engine_patch.start()
        self.addCleanup(engine_patch.stop)

    async def test_download_passes_raw_bytes_and_encodes_exactly_once(self):
        raw = b"%PDF-1.7\n\x00\xffcontent"
        attachment = {
            "filename": "brief.pdf",
            "content_type": "application/pdf",
            "data": raw,
        }
        main_thread = threading.get_ident()

        def read(file_id, project_id):
            self.assertNotEqual(threading.get_ident(), main_thread)
            self.assertFalse(self.state.locked)
            return attachment

        with (
            patch(
                "UniFlow_.states.faculty_state.get_faculty_project_file",
                side_effect=read,
            ) as service,
            patch(
                "UniFlow_.states.faculty_state.rx.download", wraps=rx.download
            ) as download,
        ):
            events = await collect(FacultyState.download_file, self.state, "7")
        service.assert_called_once_with(7, 42)
        download.assert_called_once_with(data=raw, filename="brief.pdf")
        args = event_args(events[0])
        self.assertEqual(args["filename"], "brief.pdf")
        prefix, encoded = args["url"].split(",", 1)
        self.assertEqual(prefix, "data:application/octet-stream;base64")
        self.assertEqual(base64.b64decode(encoded), raw)
        self.assertEqual(self.guard.await_count, 2)
        self.guard.assert_awaited_with(self.state, "faculty", background=True)

    async def test_invalid_and_mismatched_ids_do_not_query_files(self):
        cases = [
            ("42", "42", "0"),
            ("42", "42", "-1"),
            ("42", "42", "abc"),
            ("42", "42", "1.5"),
            ("0", "0", "7"),
            ("-1", "-1", "7"),
            ("abc", "42", "7"),
            (None, "42", "7"),
            ("42", "41", "7"),
            ("42", "", "7"),
        ]
        for route, selected, file_id in cases:
            with self.subTest(route=route, selected=selected, file_id=file_id):
                state = FacultyHarness(route, selected)
                with patch(
                    "UniFlow_.states.faculty_state.get_faculty_project_file"
                ) as service:
                    self.assertEqual(
                        await collect(
                            FacultyState.download_file, state, file_id
                        ),
                        [],
                    )
                    service.assert_not_called()
                self.assertTrue(state.project_error)

    async def test_denied_access_on_load_and_download_never_reads_projects(
        self,
    ):
        self.guard.return_value = (None, "/")
        with (
            patch(
                "UniFlow_.states.faculty_state.get_faculty_projects"
            ) as projects,
            patch(
                "UniFlow_.states.faculty_state.get_faculty_project_details"
            ) as details,
            patch(
                "UniFlow_.states.faculty_state.get_faculty_project_file"
            ) as files,
        ):
            for handler, args in (
                (FacultyState.load_faculty, ()),
                (FacultyState.download_file, ("7",)),
            ):
                events = await collect(handler, self.state, *args)
                self.assertEqual(len(events), 1)
                self.assertFalse(self.state._authorized)
            projects.assert_not_called()
            details.assert_not_called()
            files.assert_not_called()

    async def test_db_errors_are_logged_and_safe_for_list_details_and_download(
        self,
    ):
        cases = [
            (FacultyState.load_faculty, (), None, "get_faculty_projects"),
            (
                FacultyState.load_faculty,
                (),
                "42",
                "get_faculty_project_details",
            ),
            (
                FacultyState.download_file,
                ("7",),
                "42",
                "get_faculty_project_file",
            ),
        ]
        for handler, args, route, service in cases:
            with self.subTest(service=service):
                state = FacultyHarness(route)
                if route is None:
                    state.router.page.params = {}
                with (
                    patch(
                        f"UniFlow_.states.faculty_state.{service}",
                        side_effect=RuntimeError("PRIVATE database failure"),
                    ),
                    patch(
                        "UniFlow_.states.faculty_state.logging.exception"
                    ) as log,
                ):
                    self.assertEqual(await collect(handler, state, *args), [])
                log.assert_called_once()
                self.assertIn("Please try again.", state.project_error)
                self.assertNotIn("PRIVATE", state.project_error)

    async def test_details_load_typed_metadata_off_thread_and_clear_stale_data(
        self,
    ):
        main_thread = threading.get_ident()

        def read(project_id):
            self.assertEqual(project_id, 42)
            self.assertFalse(self.state.locked)
            self.assertNotEqual(threading.get_ident(), main_thread)
            return project_details()

        with patch(
            "UniFlow_.states.faculty_state.get_faculty_project_details",
            side_effect=read,
        ):
            await collect(FacultyState.load_faculty, self.state)
        self.assertEqual(self.state.files, project_details()["files"])
        self.assertEqual(self.state.selected_project["id"], "42")
        self.assertNotIn("files", self.state.selected_project)
        for route in ("0", "-1", "bad"):
            self.state.router.page.params["id"] = route
            with patch(
                "UniFlow_.states.faculty_state.get_faculty_project_details"
            ) as service:
                await collect(FacultyState.load_faculty, self.state)
                service.assert_not_called()
            self.assertEqual(self.state.files, [])
            self.assertEqual(self.state.selected_project, {})

    async def test_missing_file_and_route_changed_during_read_never_download(
        self,
    ):
        with patch(
            "UniFlow_.states.faculty_state.get_faculty_project_file",
            return_value=None,
        ):
            self.assertEqual(
                await collect(FacultyState.download_file, self.state, "7"), []
            )
        self.assertEqual(self.state.project_error, "Attachment not found.")

        def change_route(*args):
            self.state.router.page.params["id"] = "43"
            return {
                "filename": "brief.pdf",
                "content_type": "application/pdf",
                "data": b"pdf",
            }

        with patch(
            "UniFlow_.states.faculty_state.get_faculty_project_file",
            side_effect=change_route,
        ):
            self.assertEqual(
                await collect(FacultyState.download_file, self.state, "7"), []
            )

    async def test_revoked_access_after_read_blocks_download(self):
        self.guard.side_effect = [(self.account, ""), (None, "/")]
        with (
            patch(
                "UniFlow_.states.faculty_state.get_faculty_project_file",
                return_value={
                    "filename": "brief.pdf",
                    "content_type": "application/pdf",
                    "data": b"pdf",
                },
            ),
            patch("UniFlow_.states.faculty_state.rx.download") as download,
        ):
            events = await collect(FacultyState.download_file, self.state, "7")
        self.assertEqual(len(events), 1)
        download.assert_not_called()
        self.assertEqual(self.state.files, [])
        self.assertFalse(self.state._authorized)


class FacultyServiceTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock()

        @contextmanager
        def transaction():
            yield self.session

        transaction_patch = patch.object(
            project_services, "_transaction", transaction
        )
        transaction_patch.start()
        self.addCleanup(transaction_patch.stop)

    def test_file_query_binds_both_ids_and_rejects_wrong_project(self):
        stored = {
            "id": 7,
            "project_id": 42,
            "filename": "brief.pdf",
            "content_type": "application/pdf",
            "data": memoryview(b"pdf"),
        }

        def execute(statement, params):
            sql = " ".join(str(statement).split())
            self.assertIn(
                "WHERE id = :file_id AND project_id = :project_id", sql
            )
            row = stored if params == {"file_id": 7, "project_id": 42} else None
            return SimpleNamespace(
                mappings=lambda: SimpleNamespace(first=lambda: row)
            )

        self.session.execute.side_effect = execute
        self.assertIsNone(project_services.get_faculty_project_file(7, 43))
        self.assertIsNone(project_services.get_faculty_project_file(8, 42))
        self.assertEqual(
            project_services.get_faculty_project_file(7, 42)["data"], b"pdf"
        )

    def test_service_invalid_ids_precede_transaction_queries(self):
        for invalid in (0, -1, True, "42", None):
            self.assertIsNone(
                project_services.get_faculty_project_details(invalid)
            )
            self.assertIsNone(
                project_services.get_faculty_project_file(invalid, 42)
            )
            self.assertIsNone(
                project_services.get_faculty_project_file(7, invalid)
            )
        self.session.execute.assert_not_called()

    def test_project_list_remains_unfiltered_and_details_scope_metadata(self):
        self.session.execute.return_value.mappings.return_value.all.return_value = []
        self.assertEqual(project_services.get_faculty_projects(), [])
        sql = str(self.session.execute.call_args.args[0]).lower()
        self.assertNotIn("where", sql)
        self.assertNotIn("faculty_id", sql)
        self.assertIn("order by p.created_at desc, p.id desc", sql)
        self.session.execute.reset_mock()
        project = {**project_details(), "id": 42, "created_at": None}
        first = SimpleNamespace(
            mappings=lambda: SimpleNamespace(first=lambda: project)
        )
        second = SimpleNamespace(
            mappings=lambda: SimpleNamespace(
                all=lambda: [
                    {"id": 7, "filename": "brief.pdf", "size_bytes": 12}
                ]
            )
        )
        self.session.execute.side_effect = [first, second]
        details = project_services.get_faculty_project_details(42)
        self.assertEqual(details["files"], project_details()["files"])
        query, params = self.session.execute.call_args.args
        self.assertIn("WHERE project_id = :project_id", str(query))
        self.assertEqual(params, {"project_id": 42})
        self.assertNotIn("data", details["files"][0])


class AttachmentRenderTests(unittest.TestCase):
    def test_foreach_with_state_metadata_renders_without_dynamic_casts(self):
        component = rx.foreach(FacultyState.files, _file_row)
        rendered = str(component)
        self.assertIn("filename", rendered)
        self.assertIn("size_bytes", rendered)
        self.assertIn("download_file", rendered)
        self.assertIn("Attachments", str(faculty_project_details()))


if __name__ == "__main__":
    unittest.main()
