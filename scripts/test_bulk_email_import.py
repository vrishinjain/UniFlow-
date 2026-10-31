import reflex as rx

import copy
import csv
import io
import unittest
from pathlib import Path
from contextlib import contextmanager
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from UniFlow_ import user_services as services
from UniFlow_.states.admin_state import AdminState
from UniFlow_.states.login_state import LoginState
from UniFlow_.states.signup_state import SignupState


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
                if email.strip().lower() in params["emails"]
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
    def test_shared_txt_csv_contract_normalization_and_skipped_lines(self):
        for extension in ("TXT", "csv"):
            with self.subTest(extension=extension):
                parsed = services.parse_bulk_email_file(
                    f"list.{extension}",
                    b"\xef\xbb\xbf\r\n EMAIL \r\n Alice@Example.edu \r\nalice@example.edu\r\n\r\nbad address\r\nbob@example.edu\r\nemail",
                )
                self.assertEqual(
                    parsed["addresses"],
                    [
                        {"email": "alice@example.edu", "line": 3, "reason": ""},
                        {"email": "bob@example.edu", "line": 7, "reason": ""},
                    ],
                )
                self.assertEqual(
                    [row["line"] for row in parsed["invalid_lines"]], [6, 8]
                )
                self.assertTrue(
                    all(row["reason"] for row in parsed["invalid_lines"])
                )
        parsed = services.parse_bulk_email_file(
            "list.csv", b'\n"email"\n"Person@Example.edu"\n"bad,address"'
        )
        self.assertEqual(parsed["addresses"][0]["email"], "person@example.edu")
        self.assertEqual(parsed["invalid_lines"][0]["line"], 4)

    def test_invalid_addresses_skip_including_all_invalid(self):
        values = [
            "Person <person@example.edu>",
            "a..b@example.edu",
            "a@-example.edu",
            "a@example.edu,b@example.edu",
            "a@example.edu\x00",
        ]
        for extension in ("txt", "csv"):
            output = io.StringIO(newline="")
            if extension == "csv":
                csv.writer(output).writerows((value,) for value in values)
            else:
                output.write("\n".join(values))
            data = output.getvalue().encode()
            parsed = services.parse_bulk_email_file(f"list.{extension}", data)
            self.assertEqual(parsed["addresses"], [])
            self.assertEqual(
                [row["line"] for row in parsed["invalid_lines"]],
                [1, 2, 3, 4, 5],
            )
        parsed = services.parse_bulk_email_file(
            "list.csv", b'"bad\naddress"\nGood@example.edu'
        )
        self.assertEqual(parsed["invalid_lines"][0]["line"], 1)
        self.assertEqual(parsed["addresses"][0]["line"], 3)

    def test_structural_and_empty_file_errors(self):
        cases = [
            ("list.pdf", b"name@example.edu"),
            ("list.txt", b"\xff"),
            ("list.csv", b"email,name\nperson@example.edu,Person"),
            ("list.csv", b"email,\nperson@example.edu,"),
            ("list.csv", b'"person@example.edu'),
            ("list.csv", b'"a@example.edu"unexpected'),
            ("list.csv", b"good@example.edu\nbad,address"),
            ("list.txt", b"email\n"),
            ("list.csv", b'\n"email"\n'),
            ("list.txt", b""),
            ("list.txt", b" \r\n\t"),
            ("list.txt", b"x" * (services.BULK_EMAIL_MAX_BYTES + 1)),
        ]
        for filename, data in cases:
            with self.subTest(filename=filename, size=len(data)):
                with self.assertRaises(ValueError):
                    services.parse_bulk_email_file(filename, data)

    def test_limits_before_dedup_and_exact_byte_boundary(self):
        for extension in ("txt", "csv"):
            for value in (b"a@example.edu\n", b"bad\n"):
                parsed = services.parse_bulk_email_file(
                    f"list.{extension}", b"email\n" + value * 500
                )
                self.assertEqual(
                    len(parsed["addresses"]) + bool(parsed["invalid_lines"]), 1
                )
                with self.assertRaises(ValueError):
                    services.parse_bulk_email_file(
                        f"list.{extension}", value * 501
                    )
        data = "\n".join(f"u{i}@example.edu" for i in range(500)).encode()
        self.assertEqual(
            len(services.parse_bulk_email_file("list.txt", data)["addresses"]),
            500,
        )
        padded = b"a@example.edu\n".ljust(services.BULK_EMAIL_MAX_BYTES, b" ")
        self.assertEqual(
            services.parse_bulk_email_file("list.txt", padded)["addresses"][0][
                "email"
            ],
            "a@example.edu",
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

    def test_missing_or_inactive_administrator_never_writes(self):
        for status in ("pending", "rejected"):
            self.rows["admin@example.edu"].status = status
            with self.assertRaises(PermissionError):
                services.bulk_approve_emails(1, ["new@example.edu"])
        del self.rows["admin@example.edu"]
        with self.assertRaises(PermissionError):
            services.bulk_approve_emails(1, ["new@example.edu"])
        self.assertEqual(self.session.writes, 0)

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

    def test_case_variants_deduplicate_and_new_accounts_are_lowercase(self):
        with patch.object(services, "_hash_password", return_value="hash"):
            results = services.bulk_approve_emails(
                1, [" New@Example.edu ", "new@example.edu", "NEW@example.edu"]
            )
        self.assertEqual([row["email"] for row in results], ["new@example.edu"])
        self.assertIn("new@example.edu", self.rows)
        self.assertEqual(len(self.rows), 4)

    def test_case_insensitive_existing_lookup_preserves_identity(self):
        row = self.rows.pop("pending@example.edu")
        row.email = "Pending@Example.edu"
        self.rows[row.email] = row
        with patch.object(services, "_hash_password", return_value="hash"):
            results = services.bulk_approve_emails(
                1, [" PENDING@example.edu ", "pending@example.edu"]
            )
        self.assertEqual([row["outcome"] for row in results], ["Reactivated"])
        self.assertEqual(len(self.rows), 3)
        self.assertEqual(row.email, "Pending@Example.edu")
        self.assertEqual(row.role, "faculty")

    def test_ambiguous_legacy_accounts_abort_entire_import_before_writes(self):
        self.rows["Pending@Example.edu"] = SimpleNamespace(
            id=4,
            email="Pending@Example.edu",
            role="student",
            status="active",
            password_hash="old",
        )
        before = copy.deepcopy(self.rows)
        with self.assertRaisesRegex(ValueError, "multiple"):
            services.bulk_approve_emails(
                1, ["new@example.edu", "pending@example.edu"]
            )
        self.assertEqual(self.session.writes, 0)
        self.assertEqual(self.rows, before)

    def test_direct_invalid_empty_and_oversized_input_never_opens_transaction(
        self,
    ):
        with patch.object(
            services,
            "_transaction",
            side_effect=AssertionError("No transaction expected"),
        ):
            for addresses in (
                [],
                ["bad"],
                ["a@example.edu", "bad"],
                ["a@example.edu"] * 501,
            ):
                with self.subTest(addresses=addresses[:2]):
                    with self.assertRaises(ValueError):
                        services.bulk_approve_emails(1, addresses)

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
        parsed = services.parse_bulk_email_file(path.name, path.read_bytes())
        addresses = [row["email"] for row in parsed["addresses"]]
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


class IdentitySafetyTests(unittest.TestCase):
    def test_login_case_insensitive_lookup_and_ambiguity(self):
        for matches in (
            [],
            [SimpleNamespace(email="Alice@Example.edu")],
            [SimpleNamespace(id=1), SimpleNamespace(id=2)],
        ):
            session = MagicMock()
            session.scalars.return_value.all.return_value = matches
            with patch.object(services, "_transaction") as transaction:
                transaction.return_value.__enter__.return_value = session
                if len(matches) > 1:
                    with self.assertRaisesRegex(ValueError, "multiple"):
                        services.get_user_by_email(" ALICE@Example.edu ")
                else:
                    self.assertIs(
                        services.get_user_by_email(" ALICE@Example.edu "),
                        matches[0] if matches else None,
                    )
            statement, params = session.scalars.call_args.args
            self.assertIn("lower(btrim(email)) = :email", str(statement))
            self.assertEqual(params, {"email": "alice@example.edu"})

    def test_signup_lowercases_and_locks_before_case_insensitive_check(self):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        with (
            patch.object(services, "_transaction") as transaction,
            patch.object(services, "_hash_password", return_value="hash"),
        ):
            transaction.return_value.__enter__.return_value = session
            user = services.create_user(
                "Alice", " ALICE@Example.edu ", "password", "student"
            )
        self.assertEqual(user.email, "alice@example.edu")
        self.assertIn(
            "LOCK TABLE", str(session.execute.call_args_list[0].args[0])
        )
        self.assertIn(
            "lower(btrim(email))",
            str(session.execute.call_args_list[1].args[0]),
        )
        self.assertEqual(
            session.execute.call_args_list[1].args[1],
            {"email": "alice@example.edu"},
        )

    def test_signup_refuses_existing_and_ambiguous_matches_without_insert(self):
        for matches in (
            [SimpleNamespace(id=1)],
            [SimpleNamespace(id=1), SimpleNamespace(id=2)],
        ):
            session = MagicMock()
            session.execute.return_value.all.return_value = matches
            with self.assertRaises(ValueError):
                services._insert_user(
                    session,
                    "Alice",
                    " ALICE@example.edu ",
                    "hash",
                    "student",
                    "pending",
                )
            session.add.assert_not_called()
            session.flush.assert_not_called()


class ImportStateHarness:
    _clear_import = AdminState._clear_import
    _clear_access = AdminState._clear_access
    _verify_import_access = AdminState._verify_import_access

    def __init__(self):
        self._import_epoch = 0
        self.revision = 0
        self._clear_access()
        self._authorized = True
        self.login = SimpleNamespace(_session_user_id=1)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_state(self, state_class):
        return self.login


class ImportStateTests(unittest.IsolatedAsyncioTestCase):
    async def process(self, data: bytes, filename: str = "s.txt", account=None):
        state = ImportStateHarness()
        file = SimpleNamespace(name=filename, read=AsyncMock(return_value=data))
        account = account or SimpleNamespace(
            role="system_admin", status="active"
        )
        with patch(
            "UniFlow_.states.admin_state.get_user_by_id", return_value=account
        ):
            events = [
                event
                async for event in AdminState.import_emails.fn(state, [file])
            ]
            if state.importing:
                events.extend(
                    [
                        event
                        async for event in AdminState.process_email_import.fn(
                            state, state._import_epoch
                        )
                    ]
                )
        return state, events

    async def test_all_invalid_retains_line_feedback_without_any_write(self):
        with (
            patch("UniFlow_.states.admin_state.bulk_approve_emails") as approve,
            patch.object(
                services,
                "_get_engine",
                side_effect=AssertionError("Live database forbidden"),
            ),
        ):
            state, _ = await self.process(b"email\nbad\nworse")
        approve.assert_not_called()
        self.assertEqual(
            [row["line"] for row in state._import_invalid_lines], [2, 3]
        )
        self.assertIn("No valid email", state.import_message)
        self.assertTrue(state.import_error)
        self.assertEqual(state._bulk_results, [])
        self.assertFalse(state.loading)
        self.assertFalse(state.importing)
        state._clear_import()
        self.assertEqual(state._import_invalid_lines, [])
        self.assertEqual(state.import_message, "")

    async def test_partial_csv_import_passes_only_deduplicated_valid_addresses(
        self,
    ):
        results = [
            {
                "email": "alice@example.edu",
                "password": "temporary",
                "outcome": "Created",
            }
        ]
        with (
            patch(
                "UniFlow_.states.admin_state.bulk_approve_emails",
                return_value=results,
            ) as approve,
            patch(
                "UniFlow_.states.admin_state.list_pending_users",
                return_value=[],
            ),
            patch(
                "UniFlow_.states.admin_state.list_active_users", return_value=[]
            ),
        ):
            state, _ = await self.process(
                b'email\nAlice@Example.edu\n"bad,address"\nalice@example.edu',
                "s.csv",
            )
        approve.assert_called_once_with(1, ["alice@example.edu"])
        self.assertEqual(state._bulk_results, results)
        self.assertEqual(state._import_invalid_lines[0]["line"], 3)
        self.assertIn("1 invalid lines skipped", state.import_message)
        self.assertFalse(state.import_error)

    async def test_structural_error_and_denied_role_never_write(self):
        with (
            patch("UniFlow_.states.admin_state.bulk_approve_emails") as approve,
            patch("UniFlow_.states.admin_state.logging.exception"),
        ):
            state, _ = await self.process(
                b"good@example.edu\nbad,address", "s.csv"
            )
            self.assertTrue(state.import_error)
            self.assertEqual(state._bulk_results, [])
            state, _ = await self.process(
                b"good@example.edu",
                account=SimpleNamespace(role="student", status="active"),
            )
            self.assertFalse(state._authorized)
            approve.assert_not_called()

    async def test_epoch_change_discards_late_credentials(self):
        state = ImportStateHarness()
        state.importing = state.loading = True
        state._pending_import = (
            1,
            services.parse_bulk_email_file("s.txt", b"a@example.edu"),
        )

        def save(*args):
            state._clear_access()
            return [
                {
                    "email": "a@example.edu",
                    "password": "secret",
                    "outcome": "Created",
                }
            ]

        with (
            patch(
                "UniFlow_.states.admin_state.get_user_by_id",
                return_value=SimpleNamespace(
                    role="system_admin", status="active"
                ),
            ),
            patch(
                "UniFlow_.states.admin_state.bulk_approve_emails",
                side_effect=save,
            ),
        ):
            _ = [
                event
                async for event in AdminState.process_email_import.fn(
                    state, state._import_epoch
                )
            ]
        self.assertEqual(state._bulk_results, [])
        self.assertFalse(state._authorized)


class IdentityDisplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_signup_submission_display_is_lowercase(self):
        state = SimpleNamespace(
            loading=False, submitted=False, message="", submitted_email=""
        )
        with patch("UniFlow_.states.signup_state.create_user") as create:
            _ = [
                event
                async for event in SignupState.request_account.fn(
                    state,
                    {
                        "full_name": "Alice",
                        "email": " ALICE@Example.edu ",
                        "password": "longpassword",
                        "confirm_password": "longpassword",
                        "account_type": "student",
                    },
                )
            ]
        create.assert_called_once_with(
            "Alice", "alice@example.edu", "longpassword", "student"
        )
        self.assertEqual(state.submitted_email, "alice@example.edu")

    async def test_login_lookup_and_signed_in_display_are_lowercase(self):
        state = SimpleNamespace(
            loading=False,
            signed_in=False,
            password_revision=0,
            _clear_dashboard_access=AsyncMock(),
        )
        user = SimpleNamespace(
            id=7,
            full_name="Alice",
            email="Alice@Example.edu",
            role="student",
            status="active",
            password_hash="hash",
            must_change_password=False,
        )
        with (
            patch(
                "UniFlow_.states.login_state.get_user_by_email",
                return_value=user,
            ) as lookup,
            patch(
                "UniFlow_.states.login_state.verify_password", return_value=True
            ),
        ):
            _ = [
                event
                async for event in LoginState.sign_in.fn(
                    state,
                    {"email": " ALICE@Example.edu ", "password": "password"},
                )
            ]
        lookup.assert_called_once_with("alice@example.edu")
        self.assertEqual(state.email, "alice@example.edu")
        self.assertTrue(state.signed_in)
        self.assertEqual(state._session_user_id, 7)

    async def test_ambiguous_login_never_verifies_password_or_signs_in(self):
        state = SimpleNamespace(
            loading=False, signed_in=False, password_revision=0
        )
        with (
            patch(
                "UniFlow_.states.login_state.get_user_by_email",
                side_effect=ValueError("Ambiguous account"),
            ),
            patch("UniFlow_.states.login_state.verify_password") as verify,
            patch("UniFlow_.states.login_state.logging.exception"),
        ):
            _ = [
                event
                async for event in LoginState.sign_in.fn(
                    state,
                    {"email": "Alice@example.edu", "password": "password"},
                )
            ]
        verify.assert_not_called()
        self.assertFalse(state.signed_in)
        self.assertEqual(state._session_user_id, 0)


if __name__ == "__main__":
    unittest.main()
