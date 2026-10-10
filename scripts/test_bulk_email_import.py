import reflex as rx

import copy
import csv
import io
import unittest
from pathlib import Path
from contextlib import contextmanager
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from UniFlow_ import user_services as services
from UniFlow_.states.admin_state import AdminState


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.writes = 0
        self.fail_write = False
        self.admin_checks = 0
        self.revoke_on_recheck = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if sql.startswith("LOCK"):
            return None
        if sql.startswith("SELECT role"):
            self.admin_checks += 1
            admin = self.rows.get("admin@example.edu")
            if self.revoke_on_recheck and self.admin_checks == 2:
                return SimpleNamespace(
                    first=lambda: SimpleNamespace(
                        role="student", status="active"
                    )
                )
            return SimpleNamespace(first=lambda: admin)
        if sql.startswith("SELECT id"):
            rows = [
                row
                for email, row in self.rows.items()
                if email in params["emails"]
            ]
            return SimpleNamespace(all=lambda: rows)
        self.writes += 1
        if sql.startswith("INSERT"):
            for item in params:
                self.rows[item["email"]] = SimpleNamespace(
                    id=len(self.rows) + 1,
                    email=item["email"],
                    full_name=item["name"],
                    password_hash=item["hash"],
                    role="student",
                    status="active",
                )
        elif sql.startswith("UPDATE"):
            if self.fail_write:
                raise RuntimeError("Simulated database failure")
            for item in params:
                row = next(
                    row for row in self.rows.values() if row.id == item["id"]
                )
                row.status = "active"
                row.password_hash = item["hash"]
        return None


class BulkImportTests(unittest.TestCase):
    def test_valid_files_and_case_sensitive_trimmed_matching(self):
        self.assertEqual(
            services.parse_bulk_email_file(
                "list.TXT",
                b"\xef\xbb\xbfemail\r\n Alice@example.edu \r\nalice@example.edu\n",
            ),
            ["Alice@example.edu", "alice@example.edu"],
        )
        self.assertEqual(
            services.parse_bulk_email_file(
                "list.csv", b'email\n"person@example.edu"\n'
            ),
            ["person@example.edu"],
        )
        self.assertEqual(
            services.parse_bulk_email_file(
                "list.txt", b"\n\nname@example.edu\n\n"
            ),
            ["name@example.edu"],
        )

    def test_invalid_files(self):
        cases = [
            ("list.pdf", b"name@example.edu"),
            ("list.txt", b"\xff"),
            ("list.csv", b"email,name\nperson@example.edu,Person"),
            ("list.csv", b"email,\nperson@example.edu,"),
            ("list.csv", b'"person@example.edu'),
            ("list.txt", b"name@example.edu\n name@example.edu "),
            ("list.txt", b"email\n"),
            ("list.txt", b"email\nemail\na@example.edu"),
            ("list.txt", b""),
            ("list.txt", b"Person <person@example.edu>"),
            ("list.txt", b"a..b@example.edu"),
            ("list.txt", b"a@-example.edu"),
            ("list.txt", b"a@example.edu,b@example.edu"),
            ("list.txt", b"a@example.edu\x00"),
            ("list.txt", b"x" * (services.BULK_EMAIL_MAX_BYTES + 1)),
            (
                "list.txt",
                "\n".join(f"u{i}@example.edu" for i in range(501)).encode(),
            ),
        ]
        for filename, data in cases:
            with self.subTest(filename=filename, data_length=len(data)):
                with self.assertRaises(ValueError):
                    services.parse_bulk_email_file(filename, data)

    def test_address_limit_boundary(self):
        data = "\n".join(f"u{i}@example.edu" for i in range(500)).encode()
        self.assertEqual(
            len(services.parse_bulk_email_file("list.txt", data)), 500
        )
        padded = b"a@example.edu\n".ljust(services.BULK_EMAIL_MAX_BYTES, b" ")
        self.assertEqual(
            services.parse_bulk_email_file("list.txt", padded),
            ["a@example.edu"],
        )

    def setUp(self):
        self.rows = {
            "admin@example.edu": SimpleNamespace(
                id=1,
                email="admin@example.edu",
                full_name="Admin",
                role="system_admin",
                status="active",
                password_hash="unchanged",
            ),
            "pending@example.edu": SimpleNamespace(
                id=2,
                email="pending@example.edu",
                full_name="Existing faculty",
                role="faculty",
                status="pending",
                password_hash="old",
            ),
            "rejected@example.edu": SimpleNamespace(
                id=3,
                email="rejected@example.edu",
                full_name="Existing sponsor",
                role="sponsor",
                status="rejected",
                password_hash="old",
            ),
        }
        self.session = FakeSession(self.rows)

        @contextmanager
        def fake_transaction():
            before = copy.deepcopy(self.rows)
            try:
                yield self.session
            except Exception:
                self.rows.clear()
                self.rows.update(before)
                raise

        self.transaction_patch = patch.object(
            services, "_transaction", fake_transaction
        )
        self.transaction_patch.start()
        self.addCleanup(self.transaction_patch.stop)
        self.engine_patch = patch.object(
            services,
            "_get_engine",
            side_effect=AssertionError(
                "Live database access forbidden in tests"
            ),
        )
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)

    def test_atomic_creation_reactivation_and_unchanged_active(self):
        with patch.object(
            services,
            "_hash_password",
            side_effect=lambda password: f"hashed:{password}",
        ):
            results = services.bulk_approve_emails(
                1,
                [
                    "new.student@example.edu",
                    "pending@example.edu",
                    "rejected@example.edu",
                    "admin@example.edu",
                ],
            )
        self.assertEqual(
            [r["outcome"] for r in results],
            ["Created", "Reactivated", "Reactivated", "Already approved"],
        )
        self.assertEqual(
            self.rows["new.student@example.edu"].full_name, "new student"
        )
        self.assertEqual(self.rows["new.student@example.edu"].role, "student")
        self.assertEqual(self.rows["pending@example.edu"].role, "faculty")
        self.assertEqual(
            self.rows["pending@example.edu"].full_name, "Existing faculty"
        )
        self.assertEqual(self.rows["rejected@example.edu"].role, "sponsor")
        self.assertEqual(self.rows["rejected@example.edu"].status, "active")
        self.assertEqual(
            self.rows["admin@example.edu"].password_hash, "unchanged"
        )
        self.assertEqual(results[-1]["password"], "")
        self.assertEqual(len({r["password"] for r in results[:-1]}), 3)
        self.assertEqual(self.session.admin_checks, 2)

    def test_unauthorized_and_access_revoked_before_writes(self):
        self.rows["admin@example.edu"].role = "student"
        with self.assertRaises(PermissionError):
            services.bulk_approve_emails(1, ["new@example.edu"])
        self.assertEqual(self.session.writes, 0)
        self.rows["admin@example.edu"].role = "system_admin"
        self.session.admin_checks = 0
        self.session.revoke_on_recheck = True
        with patch.object(services, "_hash_password", return_value="hash"):
            with self.assertRaises(PermissionError):
                services.bulk_approve_emails(1, ["new@example.edu"])
        self.assertEqual(self.session.writes, 0)

    def test_failure_rolls_back_prior_insert(self):
        self.session.fail_write = True
        with patch.object(services, "_hash_password", return_value="hash"):
            with self.assertRaises(RuntimeError):
                services.bulk_approve_emails(
                    1, ["new@example.edu", "pending@example.edu"]
                )
        self.assertNotIn("new@example.edu", self.rows)
        self.assertEqual(self.rows["pending@example.edu"].status, "pending")
        self.assertEqual(self.rows["pending@example.edu"].password_hash, "old")

    def test_duplicate_validation_never_opens_transaction(self):
        with patch.object(
            services,
            "_transaction",
            side_effect=AssertionError("No transaction expected"),
        ):
            with self.assertRaises(ValueError):
                services.bulk_approve_emails(
                    1, ["duplicate@example.edu", " duplicate@example.edu "]
                )

    def test_password_collision_is_regenerated(self):
        with (
            patch.object(
                services,
                "_temporary_password",
                side_effect=["Abc123!defGH", "Abc123!defGH", "Xyz456@ijkLM"],
            ),
            patch.object(services, "_hash_password", return_value="hash"),
        ):
            results = services.bulk_approve_emails(
                1, ["new@example.edu", "pending@example.edu"]
            )
        self.assertEqual(len({row["password"] for row in results}), 2)

    def test_sample_file_is_valid_utf8_upload(self):
        path = (
            Path(__file__).resolve().parents[1] / "assets" / "sample_emails.txt"
        )
        addresses = services.parse_bulk_email_file(path.name, path.read_bytes())
        self.assertEqual(len(addresses), 3)
        self.assertEqual(len(set(addresses)), 3)

    def test_real_password_strength_and_bcrypt(self):
        password = services._temporary_password()
        self.assertEqual(len(password), 12)
        self.assertTrue(any(c.islower() for c in password))
        self.assertTrue(any(c.isupper() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
        self.assertTrue(any(c in "!@#$%&*-_" for c in password))
        hashed = services._hash_password(password)
        self.assertNotEqual(hashed, password)
        self.assertTrue(services.verify_password(password, hashed))


class PasswordDownloadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.login = SimpleNamespace(
            _session_user_id=1,
            _clear_session=lambda: setattr(self.login, "_session_user_id", 0),
        )
        self.state = SimpleNamespace(
            _authorized=True,
            loading=False,
            import_error=False,
            import_message="",
            _bulk_results=[
                {
                    "email": "new@example.org",
                    "password": 'Ab1!comma,"é',
                    "outcome": "Created",
                },
                {
                    "email": "pending@example.org",
                    "password": "Cd2@efGH3456",
                    "outcome": "Reactivated",
                },
                {
                    "email": "active@example.org",
                    "password": "",
                    "outcome": "Already approved",
                },
                {
                    "email": "excluded@example.org",
                    "password": "not-issued",
                    "outcome": "Already approved",
                },
            ],
            get_state=AsyncMock(return_value=self.login),
        )
        self.state._authorize = MethodType(AdminState._authorize, self.state)
        self.state._clear_access = self.clear_access
        self.user = SimpleNamespace(role="system_admin", status="active")
        self.lookup = patch(
            "UniFlow_.states.admin_state.get_user_by_id", return_value=self.user
        ).start()
        self.addCleanup(patch.stopall)
        self.engine = patch.object(
            services,
            "_get_engine",
            side_effect=AssertionError("Live database access forbidden"),
        ).start()

    def clear_access(self):
        self.state._authorized = False
        self.state._bulk_results = []

    async def test_download_quotes_utf8_and_retains_credentials(self):
        before = copy.deepcopy(self.state._bulk_results)
        with patch("UniFlow_.states.admin_state.rx.download") as download:
            await AdminState.download_passwords.fn(self.state)
        self.lookup.assert_called_once_with(1)
        download.assert_called_once()
        data = download.call_args.kwargs["data"]
        self.assertIsInstance(data, bytes)
        rows = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
        self.assertEqual(
            rows,
            [
                ["email", "password"],
                ["new@example.org", 'Ab1!comma,"é'],
                ["pending@example.org", "Cd2@efGH3456"],
            ],
        )
        self.assertTrue(data.startswith(b'"email","password"\r\n'))
        self.assertEqual(self.state._bulk_results, before)
        self.assertEqual(
            download.call_args.kwargs["filename"], "uniflow_passwords.csv"
        )
        self.assertNotIn("url", download.call_args.kwargs)

    async def test_revoked_or_missing_identity_never_downloads(self):
        for user in (
            None,
            SimpleNamespace(role="student", status="active"),
            SimpleNamespace(role="system_admin", status="pending"),
            SimpleNamespace(role="system_admin", status="rejected"),
        ):
            with self.subTest(user=user):
                self.login._session_user_id = 1
                self.state._authorized = True
                self.lookup.return_value = user
                with patch(
                    "UniFlow_.states.admin_state.rx.download"
                ) as download:
                    await AdminState.download_passwords.fn(self.state)
                download.assert_not_called()
                self.assertFalse(self.state._authorized)
                self.assertEqual(self.state._bulk_results, [])
        self.login._session_user_id = 0
        self.lookup.reset_mock()
        with patch("UniFlow_.states.admin_state.rx.download") as download:
            await AdminState.download_passwords.fn(self.state)
        self.lookup.assert_not_called()
        download.assert_not_called()

    async def test_no_issued_passwords_never_downloads(self):
        self.state._bulk_results = [self.state._bulk_results[2]]
        with patch("UniFlow_.states.admin_state.rx.download") as download:
            await AdminState.download_passwords.fn(self.state)
        download.assert_not_called()
        self.assertTrue(self.state.import_error)

    async def test_verification_failure_never_downloads(self):
        self.lookup.side_effect = RuntimeError("Verification unavailable")
        with (
            patch("UniFlow_.states.admin_state.rx.download") as download,
            patch("UniFlow_.states.admin_state.logging.exception"),
        ):
            await AdminState.download_passwords.fn(self.state)
        download.assert_not_called()
        self.assertFalse(self.state._authorized)
        self.assertEqual(self.state._bulk_results, [])


if __name__ == "__main__":
    unittest.main()
