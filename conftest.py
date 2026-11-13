
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from UniFlow_.user_model import User
from UniFlow_.project_model import Project


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


@pytest.fixture(scope="session")
def test_engine():
    """Create an engine exclusively for the test database."""
    test_url = os.environ.get("TEST_DATABASE_URL")

    if not test_url:
        raise pytest.UsageError(
            "TEST_DATABASE_URL is required."
        )

    engine = create_engine(test_url)

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Roll back all fixture changes after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def test_user(db_session):
    """Create a temporary active sponsor."""
    user = User(
        full_name="Test Sponsor",
        email=f"test-{uuid.uuid4().hex}@example.com",
        password_hash="test-only-not-a-real-password-hash",
        role="sponsor",
        status="active",
        must_change_password=False,
    )

    db_session.add(user)
    db_session.flush()

    return user


@pytest.fixture
def test_project(db_session, test_user):
    """Create a temporary project belonging to the test sponsor."""
    project = Project(
        sponsor_id=test_user.id,
        title="Test Project",
        description="Temporary project for pytest testing.",
        status="pending",
    )

    db_session.add(project)
    db_session.flush()

    return project
