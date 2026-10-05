import unittest
import uuid
from unittest.mock import patch

import reflex as rx

from UniFlow_.user_model import User
from UniFlow_.user_services import (
    create_user,
    get_user_by_email,
    update_user_role,
    update_user_status,
)


class UserServiceUpdateTests(unittest.TestCase):
    def test_create_system_admin_when_one_already_exists_is_blocked(
        self,
    ) -> None:
        with (
            patch("UniFlow_.user_services.rx.session") as session_factory,
            patch(
                "UniFlow_.user_services._hash_password", return_value="hashed"
            ),
            patch("UniFlow_.user_services._insert_user") as insert_user,
        ):
            session = session_factory.return_value.__enter__.return_value
            session.execute.return_value.scalars.return_value.first.return_value = User(
                full_name="Existing Admin",
                email="existing-admin@example.test",
                password_hash="hashed",
                role="system_admin",
                status="active",
            )

            with self.assertRaisesRegex(
                ValueError, "^A system administrator already exists\\.$"
            ):
                create_user(
                    full_name="New Admin",
                    email="new-admin@example.test",
                    password="Test-password-42!",
                    role="system_admin",
                )

            insert_user.assert_not_called()
            session.commit.assert_not_called()

    def test_update_role_to_system_admin_when_another_exists_is_blocked(
        self,
    ) -> None:
        user = User(
            full_name="Target User",
            email="target-user@example.test",
            password_hash="hashed",
            role="student",
            status="active",
        )
        with patch("UniFlow_.user_services.rx.session") as session_factory:
            session = session_factory.return_value.__enter__.return_value
            session.get.return_value = user
            session.execute.return_value.scalars.return_value.first.return_value = object()

            with self.assertRaisesRegex(
                ValueError, "^A system administrator already exists\\.$"
            ):
                update_user_role(user_id=1, role="system_admin")

            self.assertEqual(user.role, "student")
            session.commit.assert_not_called()

    def _create_test_user(self) -> User:
        unique_id = uuid.uuid4().hex
        return create_user(
            full_name="Service Update Test",
            email=f"service-update-{unique_id}@example.test",
            password="Test-password-42!",
            role="student",
        )

    def _remove_test_user(self, user_id: int) -> None:
        with rx.session() as session:
            user = session.get(User, user_id)
            if user is not None:
                session.delete(user)
                session.commit()

    def test_update_user_role(self) -> None:
        user = self._create_test_user()
        try:
            update_user_role(user.id, "faculty")
            updated_user = get_user_by_email(user.email)
            self.assertIsNotNone(updated_user)
            self.assertEqual(updated_user.role, "faculty")

            with self.assertRaises(ValueError):
                update_user_role(user.id, "unknown-role")
            with self.assertRaises(ValueError):
                update_user_role(-1, "faculty")
        finally:
            self._remove_test_user(user.id)

    def test_update_user_status(self) -> None:
        user = self._create_test_user()
        try:
            update_user_status(user.id, "active")
            updated_user = get_user_by_email(user.email)
            self.assertIsNotNone(updated_user)
            self.assertEqual(updated_user.status, "active")

            with self.assertRaises(ValueError):
                update_user_status(user.id, "suspended")
            with self.assertRaises(ValueError):
                update_user_status(-1, "active")
        finally:
            self._remove_test_user(user.id)


if __name__ == "__main__":
    unittest.main()
