
import os

import pytest


def pytest_sessionstart(session):
    """Prevent tests from running without a test database."""
    test_database_url = os.environ.get("TEST_DATABASE_URL")

    if not test_database_url:
        raise pytest.UsageError(
            "TEST_DATABASE_URL is not set. "
            "Set it to a separate test database before running tests."
        )
