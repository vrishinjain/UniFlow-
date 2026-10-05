import reflex as rx

from typing import TypedDict
from faker import Faker


class SampleUser(TypedDict):
    id: str
    name: str
    email: str
    role: str
    status: str
    initials: str


def sample_university_users() -> list[SampleUser]:
    fake = Faker("en_US")
    fake.seed_instance(42)
    users: list[SampleUser] = []
    assignments = (
        ("Student", "Pending"),
        ("Faculty", "Pending"),
        ("Staff", "Pending"),
        ("Student", "Active"),
        ("Faculty", "Active"),
        ("Staff", "Active"),
        ("Administrator", "Active"),
        ("Student", "Rejected"),
    )
    for index, (role, status) in enumerate(assignments):
        first = fake.first_name()
        last = fake.last_name()
        users.append(
            SampleUser(
                id=f"sample-{index + 1}",
                name=f"{first} {last}",
                email=f"{first.lower()}.{last.lower()}@university.example.edu",
                role=role,
                status=status,
                initials=f"{first[0]}{last[0]}",
            )
        )
    return users


class AdminState(rx.State):
    users: list[SampleUser] = sample_university_users()
    announcement: str = ""

    @rx.var
    def total_users(self) -> int:
        return len(self.users)

    @rx.var
    def pending_users(self) -> int:
        return sum(user["status"] == "Pending" for user in self.users)

    @rx.var
    def active_users(self) -> int:
        return sum(user["status"] == "Active" for user in self.users)

    @rx.var
    def rejected_users(self) -> int:
        return sum(user["status"] == "Rejected" for user in self.users)

    def _review_user(self, user_id: str, status: str) -> None:
        for index, user in enumerate(self.users):
            if user["id"] == user_id and user["status"] == "Pending":
                updated = user.copy()
                updated["status"] = status
                self.users[index] = updated
                decision = "approved" if status == "Active" else "rejected"
                self.announcement = f"{user['name']} {decision}. Sample status is now {status}. This change is in memory only."
                return

    @rx.event
    def approve_user(self, user_id: str):
        self._review_user(user_id, "Active")

    @rx.event
    def reject_user(self, user_id: str):
        self._review_user(user_id, "Rejected")
