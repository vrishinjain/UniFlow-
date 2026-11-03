
import os

import pytest
from sqlalchemy.engine import make_url


def pytest_sessionstart(session):
    """Prevent tests from using the application database."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    app_url = os.environ.get("REFLEX_DB_URL")

    if not test_url:
        raise pytest.UsageError(
            "TEST_DATABASE_URL is not set. "
            "Configure a separate test database before running tests."
        )

    try:
        test_database = make_url(test_url)

        if app_url:
            app_database = make_url(app_url)

            if test_database == app_database:
                raise pytest.UsageError(
                    "TEST_DATABASE_URL must be different from REFLEX_DB_URL."
                )
    except ValueError as error:
        raise pytest.UsageError(
            "Invalid database URL configuration."
        ) from error
