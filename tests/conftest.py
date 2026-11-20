import pytest

import database
import app.main as main_module


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Point all persistence at a fresh temporary SQLite database."""

    db_path = tmp_path / "test_cards.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.initialize_database()

    connection = database.get_connection()
    try:
        with connection:
            connection.execute("DELETE FROM comments")
            connection.execute("DELETE FROM cards")
            connection.execute("DELETE FROM counters")
    finally:
        connection.close()

    database.initialize_database()
    main_module.reload_storage_from_db()

    yield
