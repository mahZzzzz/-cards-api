from pathlib import Path

from fastapi.testclient import TestClient

import database
import app.main as main_module


client = TestClient(main_module.app)


def restart_storage():
    """Simulate a backend restart by reloading everything from SQLite."""

    main_module.reload_storage_from_db()


def create_card(title="Persisted card", description="Stored in SQLite"):
    response = client.post(
        "/cards",
        json={"title": title, "description": description},
    )
    assert response.status_code == 201
    return response.json()


def test_cards_comments_status_and_assignee_survive_restart():
    card = create_card()
    card_id = card["id"]

    response = client.patch(
        f"/cards/{card_id}",
        json={"status": "ready", "assignee": "Alex"},
    )
    assert response.status_code == 200

    response = client.post(
        f"/cards/{card_id}/comments",
        json={"author": "Sam", "text": "Please keep this comment."},
    )
    assert response.status_code == 201
    comment_id = response.json()["id"]

    restart_storage()

    response = client.get(f"/cards/{card_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["assignee"] == "Alex"

    response = client.get(f"/cards/{card_id}/comments")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": comment_id,
            "card_id": card_id,
            "author": "Sam",
            "text": "Please keep this comment.",
        }
    ]


def test_updates_survive_restart():
    card = create_card()
    card_id = card["id"]

    response = client.patch(
        f"/cards/{card_id}",
        json={
            "title": "Updated title",
            "description": "Updated description",
        },
    )
    assert response.status_code == 200

    restart_storage()

    response = client.get(f"/cards/{card_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["description"] == "Updated description"


def test_ids_are_not_reused_after_delete_and_restart():
    first = create_card("First card")
    second = create_card("Second card")

    response = client.post(
        f"/cards/{first['id']}/comments",
        json={"author": "Sam", "text": "First comment."},
    )
    assert response.status_code == 201
    comment_id = response.json()["id"]

    assert client.delete(f"/cards/{second['id']}").status_code == 204
    assert client.delete(f"/cards/{first['id']}").status_code == 204

    restart_storage()

    new_card = create_card("New card")
    response = client.post(
        f"/cards/{new_card['id']}/comments",
        json={"author": "Sam", "text": "New comment."},
    )
    assert response.status_code == 201

    assert new_card["id"] == second["id"] + 1
    assert response.json()["id"] == comment_id + 1


def test_delete_card_removes_comments_from_database():
    card = create_card()
    card_id = card["id"]

    for text in ("First comment.", "Second comment."):
        response = client.post(
            f"/cards/{card_id}/comments",
            json={"author": "Sam", "text": text},
        )
        assert response.status_code == 201

    assert client.delete(f"/cards/{card_id}").status_code == 204

    restart_storage()

    assert client.get(f"/cards/{card_id}").status_code == 404
    assert client.get(f"/cards/{card_id}/comments").status_code == 404

    connection = database.get_connection()
    try:
        card_count = connection.execute(
            "SELECT COUNT(*) FROM cards WHERE id = ?",
            (card_id,),
        ).fetchone()[0]
        comment_count = connection.execute(
            "SELECT COUNT(*) FROM comments WHERE card_id = ?",
            (card_id,),
        ).fetchone()[0]
    finally:
        connection.close()

    assert card_count == 0
    assert comment_count == 0


def test_application_startup_loads_persisted_state():
    card = create_card("Loaded at startup")
    card_id = card["id"]

    main_module.cards.clear()
    main_module.comments.clear()

    with TestClient(main_module.app) as restarted_client:
        response = restarted_client.get(f"/cards/{card_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Loaded at startup"


def test_existing_database_without_counters_continues_ids(tmp_path, monkeypatch):
    legacy_path = tmp_path / "legacy_cards.db"
    monkeypatch.setattr(database, "DB_PATH", legacy_path)

    database.initialize_database()

    connection = database.get_connection()
    try:
        with connection:
            connection.execute("DROP TABLE counters")
            connection.execute(
                """
                INSERT INTO cards (
                    id, title, description, status, assignee
                )
                VALUES (5, 'Legacy card', '', 'spec', NULL)
                """
            )
            connection.execute(
                """
                INSERT INTO comments (
                    id, card_id, author, text
                )
                VALUES (3, 5, 'Sam', 'Legacy comment')
                """
            )
    finally:
        connection.close()

    database.initialize_database()

    assert database.get_next_ids() == (6, 4)

    main_module.reload_storage_from_db()

    assert main_module.next_card_id == 6
    assert main_module.next_comment_id == 4


def test_tests_use_a_temporary_database(tmp_path):
    real_database = Path(database.__file__).resolve().parent / "cards.db"

    assert database.DB_PATH != real_database
    assert database.DB_PATH.parent == tmp_path
    assert database.DB_PATH.is_file()
