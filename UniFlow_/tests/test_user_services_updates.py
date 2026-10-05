import unittest
import uuid

from UniFlow_.user_model import User
from UniFlow_.user_services import (
    _transaction,
    create_user,
    get_user_by_email,
    update_user_role,
    update_user_status,
)


class UserServiceUpdateTests(unittest.TestCase):
    def _create_test_user(self) -> User:
        unique_id = uuid.uuid4().hex
        return create_user(
            full_name="Service Update Test",
            email=f"service-update-{unique_id}@example.test",
            password="Test-password-42!",
            role="student",
        )

    def _remove_test_user(self, user_id: int) -> None:
        with _transaction() as session:
            user = session.get(User, user_id)
            if user is not None:
                session.delete(user)

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
