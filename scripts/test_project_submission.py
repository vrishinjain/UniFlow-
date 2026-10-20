import reflex as rx

import copy
import io
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

from UniFlow_ import project_services
from UniFlow_.states.sponsor_state import SponsorState
from UniFlow_.utils.files import MAX_FILE_BYTES, MIME_TYPES, read_and_validate


def upload(name: str, data: bytes):
    return SimpleNamespace(
        name=name, read=AsyncMock(side_effect=lambda limit: data[:limit])
    )


def office_document(extension: str) -> bytes:
    folder, filename, root, namespace, content_type = (
        (
            "word",
            "document.xml",
            "document",
            "wordprocessingml",
            "wordprocessingml.document",
        )
        if extension == ".docx"
        else (
            "ppt",
            "presentation.xml",
            "presentation",
            "presentationml",
            "presentationml.presentation",
        )
    )
    main = f"{folder}/{filename}"
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/{main}" ContentType="application/vnd.openxmlformats-officedocument.{content_type}.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="{main}"/></Relationships>',
        )
        archive.writestr(
            main,
            f'<{root} xmlns="http://schemas.openxmlformats.org/{namespace}/2006/main"/>',
        )
    return stream.getvalue()


class FileValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_optional_and_valid_types_with_canonical_mime(self):
        self.assertEqual(await read_and_validate([]), [])
        items = [
            upload("brief.PDF", b"%PDF-1.7\ncontent"),
            upload("brief.DoCx", office_document(".docx")),
            upload("brief.PPTX", office_document(".pptx")),
        ]
        result = await read_and_validate(items)
        for item, accepted in zip(items, result):
            item.read.assert_awaited_once_with(MAX_FILE_BYTES + 1)
            self.assertEqual(accepted["filename"], item.name)
            self.assertEqual(accepted["size_bytes"], len(accepted["data"]))
            self.assertEqual(
                accepted["content_type"],
                MIME_TYPES[f".{item.name.rsplit('.', 1)[1].lower()}"],
            )

    async def test_limits_are_bounded_and_no_partial_result(self):
        items = [upload("brief.pdf", b"%PDF-1.7\n") for _ in range(4)]
        with self.assertRaises(ValueError):
            await read_and_validate(items)
        for item in items:
            item.read.assert_not_awaited()
        exact = b"%PDF-1.7\n".ljust(MAX_FILE_BYTES, b" ")
        self.assertEqual(
            (await read_and_validate([upload("exact.pdf", exact)]))[0][
                "size_bytes"
            ],
            MAX_FILE_BYTES,
        )
        too_large = upload("large.pdf", exact + b" ")
        with self.assertRaises(ValueError):
            await read_and_validate(
                [upload("valid.pdf", b"%PDF-1.7\n"), too_large]
            )
        too_large.read.assert_awaited_once_with(MAX_FILE_BYTES + 1)

    async def test_unsafe_names_and_mismatched_signatures(self):
        for name in (
            "",
            " ",
            "../brief.pdf",
            "folder/brief.pdf",
            "folder\\brief.pdf",
            "C:brief.pdf",
            "brief\x00.pdf",
            "brief.exe",
            " brief.pdf",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                await read_and_validate([upload(name, b"%PDF-1.7\n")])
        for name, data in (
            ("brief.pdf", b"not pdf"),
            ("brief.docx", b"%PDF-1.7\n"),
            ("brief.docx", office_document(".pptx")),
            ("brief.pptx", office_document(".docx")),
            ("brief.pdf", b""),
        ):
            with (
                self.subTest(name=name),
                self.assertRaises(ValueError),
                patch("UniFlow_.utils.files.logging.exception"),
            ):
                await read_and_validate([upload(name, data)])

    async def test_malformed_and_unsafe_zip(self):
        for entry in ("../bad.xml", "vbaProject.bin"):
            data = io.BytesIO(office_document(".docx"))
            with ZipFile(data, "a") as archive:
                archive.writestr(entry, "bad")
            with self.assertRaises(ValueError):
                await read_and_validate([upload("brief.docx", data.getvalue())])
        data = io.BytesIO()
        with ZipFile(data, "w") as archive:
            archive.writestr("word/document.xml", "not xml")
        with self.assertRaises(ValueError):
            await read_and_validate([upload("brief.docx", data.getvalue())])


class FakeSession:
    def __init__(self):
        self.rows: list[dict] = []
        self.sponsor = SimpleNamespace(
            role="sponsor", status="active", must_change_password=False
        )
        self.fail_files = False
        self.statements: list[str] = []

    def execute(self, statement, params):
        sql = str(statement)
        self.statements.append(sql)
        if sql.startswith("SELECT"):
            return SimpleNamespace(first=lambda: self.sponsor)
        if sql.startswith("INSERT INTO public.projects"):
            self.rows.append(dict(params))
            return SimpleNamespace(scalar_one=lambda: 42)
        self.rows.extend(copy.deepcopy(params))
        if self.fail_files:
            raise RuntimeError("Simulated attachment failure")
        return None


class ProjectServiceTests(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()

        @contextmanager
        def transaction():
            before = copy.deepcopy(self.session.rows)
            try:
                yield self.session
            except Exception:
                self.session.rows = before
                raise

        self.patch = patch.object(project_services, "_transaction", transaction)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        engine = patch(
            "UniFlow_.user_services._get_engine",
            side_effect=AssertionError("Live database access forbidden"),
        )
        engine.start()
        self.addCleanup(engine.stop)
        data = b"%PDF-1.7\ncontent"
        self.files = [
            {
                "filename": "brief.pdf",
                "data": data,
                "size_bytes": len(data),
                "content_type": "application/pdf",
            }
        ]

    def test_atomic_submission_and_parameter_binding(self):
        title = "  Sponsor's project :title  "
        self.assertEqual(
            project_services.submit_project(
                1, title, " Description ", self.files
            ),
            42,
        )
        self.assertEqual(self.session.rows[0]["title"], title.strip())
        self.assertEqual(self.session.rows[0]["description"], "Description")
        self.assertEqual(self.session.rows[0]["status"], "submitted")
        self.assertEqual(self.session.rows[1]["project_id"], 42)
        self.assertIn("FOR UPDATE", self.session.statements[0])
        self.assertNotIn(title.strip(), self.session.statements[1])

    def test_no_attachments_and_rollback_on_attachment_failure(self):
        project_services.submit_project(1, "Title", "Description", [])
        self.assertEqual(len(self.session.rows), 1)
        self.session.rows.clear()
        self.session.fail_files = True
        with self.assertRaises(RuntimeError):
            project_services.submit_project(
                1, "Title", "Description", self.files
            )
        self.assertEqual(self.session.rows, [])

    def test_authorization_and_validation_precede_writes(self):
        for role, status, password_change in (
            ("student", "active", False),
            ("sponsor", "pending", False),
            ("sponsor", "rejected", False),
            ("sponsor", "active", True),
        ):
            self.session.sponsor = SimpleNamespace(
                role=role, status=status, must_change_password=password_change
            )
            with self.assertRaises(PermissionError):
                project_services.submit_project(
                    1, "Title", "Description", self.files
                )
            self.assertEqual(self.session.rows, [])
        for title, description in ((" ", "Description"), ("Title", " ")):
            with self.assertRaises(ValueError):
                project_services.submit_project(1, title, description, [])
        invalid = [{**self.files[0], "size_bytes": 0}]
        with self.assertRaises(ValueError):
            project_services.submit_project(1, "Title", "Description", invalid)
        self.assertEqual(self.session.rows, [])


class SubmissionRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_field_and_upload_errors_allow_retry(self):
        state = SimpleNamespace(
            title=" ",
            description=" ",
            loading=False,
            title_error="",
            description_error="",
            upload_error="",
            submission_error="",
            success_message="",
            _pending_files=[],
        )
        self.assertFalse(await SponsorState._prepare_submission(state, []))
        self.assertTrue(state.title_error)
        self.assertTrue(state.description_error)
        self.assertFalse(state.loading)
        state.title = " Title "
        state.description = " Description "
        self.assertFalse(
            await SponsorState._prepare_submission(
                state, [upload("brief.exe", b"bad")]
            )
        )
        self.assertTrue(state.upload_error)
        self.assertFalse(state.loading)
        self.assertTrue(await SponsorState._prepare_submission(state, []))
        self.assertEqual(state.title, "Title")
        self.assertEqual(state.description, "Description")
        self.assertEqual(state.upload_error, "")
        self.assertTrue(state.loading)


if __name__ == "__main__":
    unittest.main()
