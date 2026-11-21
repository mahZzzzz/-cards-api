import pytest
from fastapi.testclient import TestClient

import database
import app.main as main_module
from app import auth


TEST_ADMIN_USERNAME = "test-admin"
TEST_MEMBER_USERNAME = "test-member"
TEST_PASSWORD = "test-password-123"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Point all persistence at a fresh temporary SQLite database."""

    db_path = tmp_path / "test_cards.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.initialize_database()

    connection = database.get_connection()
    try:
        with connection:
            # Sessions first: they reference users.
            connection.execute("DELETE FROM sessions")
            connection.execute("DELETE FROM users")
            connection.execute("DELETE FROM comments")
            connection.execute("DELETE FROM cards")
            connection.execute("DELETE FROM counters")
    finally:
        connection.close()

    database.initialize_database()
    main_module.reload_storage_from_db()

    yield


@pytest.fixture(scope="session")
def test_password_hash():
    """Hash the shared test password once for the whole session."""

    return auth.hash_password(TEST_PASSWORD)


@pytest.fixture
def seeded_users(isolated_database, test_password_hash):
    """Create one admin and one member in the isolated test database."""

    admin_id = database.create_user(
        TEST_ADMIN_USERNAME,
        test_password_hash,
        "admin",
        "2026-01-01T00:00:00+00:00",
    )
    member_id = database.create_user(
        TEST_MEMBER_USERNAME,
        test_password_hash,
        "member",
        "2026-01-01T00:00:00+00:00",
    )

    return {
        "password": TEST_PASSWORD,
        "admin": {
            "id": admin_id,
            "username": TEST_ADMIN_USERNAME,
            "role": "admin",
        },
        "member": {
            "id": member_id,
            "username": TEST_MEMBER_USERNAME,
            "role": "member",
        },
    }


@pytest.fixture
def admin_token(seeded_users):
    return auth.issue_token(seeded_users["admin"]["id"])


@pytest.fixture
def member_token(seeded_users):
    return auth.issue_token(seeded_users["member"]["id"])


@pytest.fixture
def admin_client(admin_token):
    client = TestClient(main_module.app)
    client.headers["Authorization"] = f"Bearer {admin_token}"
    return client


@pytest.fixture
def member_client(member_token):
    client = TestClient(main_module.app)
    client.headers["Authorization"] = f"Bearer {member_token}"
    return client
