
import pytest
from fastapi.testclient import TestClient

import app.main as main_module


@pytest.fixture(autouse=True)
def reset_cards():
    main_module.cards.clear()
    main_module.next_card_id = 1


client = TestClient(main_module.app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_card():
    response = client.post(
        "/cards",
        json={
            "title": "Test Card",
            "description": "Created by automated test"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] >= 1
    assert data["title"] == "Test Card"
    assert data["description"] == "Created by automated test"
    assert data["status"] == "spec"

def test_list_cards():
    create_response = client.post(
        "/cards",
        json={
            "title": "List Test Card",
            "description": "Testing GET cards endpoint"
        }
    )

    assert create_response.status_code == 201

    created_card = create_response.json()

    response = client.get("/cards")

    assert response.status_code == 200

    cards = response.json()

    assert isinstance(cards, list)

    assert any(
        card["id"] == created_card["id"]
        and card["title"] == "List Test Card"
        for card in cards
    )

def test_read_card():
    create_response = client.post(
        "/cards",
        json={
            "title": "Read Test Card",
            "description": "Testing a single card"
        }
    )

    assert create_response.status_code == 201

    created_card = create_response.json()
    card_id = created_card["id"]

    response = client.get(f"/cards/{card_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == card_id
    assert data["title"] == "Read Test Card"
    assert data["description"] == "Testing a single card"
    assert data["status"] == "spec"

def test_update_card():
    create_response = client.post(
        "/cards",
        json={
            "title": "Update Test Card",
            "description": "Testing PATCH endpoint"
        }
    )

    assert create_response.status_code == 201

    card_id = create_response.json()["id"]

    response = client.patch(
        f"/cards/{card_id}",
        json={"status": "ready"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == card_id
    assert data["title"] == "Update Test Card"
    assert data["status"] == "ready"

    # Verify that the update was saved
    get_response = client.get(f"/cards/{card_id}")

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "ready"

def test_delete_card():
    # Create a new card
    create_response = client.post(
        "/cards",
        json={
            "title": "Delete Test Card",
            "description": "Testing DELETE endpoint"
        }
    )

    assert create_response.status_code == 201

    card_id = create_response.json()["id"]

    # Delete the card
    delete_response = client.delete(f"/cards/{card_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    # Verify that the card no longer exists
    get_response = client.get(f"/cards/{card_id}")

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Card not found"

def test_read_nonexistent_card():
    response = client.get("/cards/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Card not found"
    }

def test_illegal_status_transition():
    # Create a card with initial status "spec"
    create_response = client.post(
        "/cards",
        json={
            "title": "Invalid Transition Test",
            "description": "Testing illegal status changes"
        }
    )

    assert create_response.status_code == 201
    card_id = create_response.json()["id"]

    # Attempt an illegal status transition
    response = client.patch(
        f"/cards/{card_id}",
        json={"status": "done"}
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Illegal card status transition"
    }

    # Verify that the status was not changed
    get_response = client.get(f"/cards/{card_id}")

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "spec"

def test_create_card_with_empty_title():
    # Get the number of cards before the request
    before_response = client.get("/cards")
    assert before_response.status_code == 200
    before_count = len(before_response.json())

    # Attempt to create a card with an invalid title
    response = client.post(
        "/cards",
        json={
            "title": "",
            "description": "Testing invalid input"
        }
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        error["loc"] == ["body", "title"]
        and error["type"] == "string_too_short"
        for error in errors
    )

    # Verify that the invalid card was not created
    after_response = client.get("/cards")
    assert after_response.status_code == 200
    assert len(after_response.json()) == before_count

def test_delete_nonexistent_card():
    response = client.delete("/cards/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Card not found"
    }


def test_update_nonexistent_card():
    response = client.patch(
        "/cards/999999",
        json={"title": "Updated Title"}
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Card not found"
    }

def test_complete_status_workflow():
    response = client.post(
        "/cards",
        json={
            "title": "Workflow Test",
            "description": "Testing all valid transitions"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    valid_statuses = [
        "ready",
        "in_progress",
        "review",
        "done"
    ]

    for new_status in valid_statuses:
        response = client.patch(
            f"/cards/{card_id}",
            json={"status": new_status}
        )

        assert response.status_code == 200
        assert response.json()["status"] == new_status

    final_response = client.get(f"/cards/{card_id}")

    assert final_response.status_code == 200
    assert final_response.json()["status"] == "done"

def test_cannot_transition_from_done():
    # Create a card
    response = client.post(
        "/cards",
        json={
            "title": "Completed Card",
            "description": "Testing transitions from done"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Move through all valid statuses
    for new_status in ["ready", "in_progress", "review", "done"]:
        response = client.patch(
            f"/cards/{card_id}",
            json={"status": new_status}
        )
        assert response.status_code == 200

    # Attempt to move backwards from done
    response = client.patch(
        f"/cards/{card_id}",
        json={"status": "review"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Illegal card status transition"

    # Verify status remains unchanged
    response = client.get(f"/cards/{card_id}")
    assert response.json()["status"] == "done"


def test_invalid_card_status():
    # Create a card
    response = client.post(
        "/cards",
        json={
            "title": "Invalid Status Card",
            "description": "Testing an unknown status"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Attempt to use an undefined status
    response = client.patch(
        f"/cards/{card_id}",
        json={"status": "cancelled"}
    )

    assert response.status_code == 422

    # Verify the card was not modified
    response = client.get(f"/cards/{card_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "spec"

def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Cards API is running"
    }


def test_status_cannot_be_null():
    # Create a new card
    create_response = client.post(
        "/cards",
        json={
            "title": "Null Status Test",
            "description": "Testing null status validation"
        }
    )

    assert create_response.status_code == 201
    card_id = create_response.json()["id"]

    # Attempt to set status to null
    response = client.patch(
        f"/cards/{card_id}",
        json={"status": None}
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Status cannot be null"
    }

    # Verify that status remains unchanged
    get_response = client.get(f"/cards/{card_id}")

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "spec"


STATUS_PATH = {
    "spec": [],
    "ready": ["ready"],
    "in_progress": ["ready", "in_progress"],
    "review": ["ready", "in_progress", "review"],
    "done": ["ready", "in_progress", "review", "done"],
}


def move_card_to(card_id, target_status):
    """Advance a card along the legal workflow to the requested status."""

    for status in STATUS_PATH[target_status]:
        response = client.patch(
            f"/cards/{card_id}",
            json={"status": status},
        )
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        ("spec", "in_progress"),
        ("spec", "review"),
        ("spec", "done"),
        ("ready", "spec"),
        ("ready", "review"),
        ("ready", "done"),
        ("in_progress", "spec"),
        ("in_progress", "ready"),
        ("in_progress", "done"),
        ("review", "spec"),
        ("review", "ready"),
        ("review", "in_progress"),
        ("done", "spec"),
        ("done", "ready"),
        ("done", "in_progress"),
        ("done", "review"),
    ],
)
def test_illegal_status_transitions(from_status, to_status):
    response = client.post("/cards", json={"title": "Illegal transition"})
    assert response.status_code == 201
    card_id = response.json()["id"]

    move_card_to(card_id, from_status)

    response = client.patch(
        f"/cards/{card_id}",
        json={"status": to_status},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Illegal card status transition"
    }

    # The failed transition must leave the card untouched.
    get_response = client.get(f"/cards/{card_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == from_status


@pytest.mark.parametrize(
    "status",
    ["spec", "ready", "in_progress", "review", "done"],
)
def test_setting_same_status_is_accepted(status):
    response = client.post("/cards", json={"title": "Same status"})
    assert response.status_code == 201
    card_id = response.json()["id"]

    move_card_to(card_id, status)
    before = client.get(f"/cards/{card_id}").json()

    response = client.patch(
        f"/cards/{card_id}",
        json={"status": status},
    )

    assert response.status_code == 200
    assert response.json() == before

    # The no-op update must also be persisted unchanged.
    main_module.reload_storage_from_db()
    assert client.get(f"/cards/{card_id}").json() == before


@pytest.mark.parametrize(
    ("title_length", "expected_status"),
    [(100, 201), (101, 422)],
)
def test_title_length_boundary(title_length, expected_status):
    response = client.post(
        "/cards",
        json={"title": "t" * title_length},
    )

    assert response.status_code == expected_status

    if expected_status == 201:
        assert len(response.json()["title"]) == 100
    else:
        assert any(
            error["loc"] == ["body", "title"]
            for error in response.json()["detail"]
        )


def test_description_longer_than_1000_characters_is_rejected():
    before = client.get("/cards").json()

    response = client.post(
        "/cards",
        json={
            "title": "Too long description",
            "description": "d" * 1001,
        },
    )

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", "description"]
        for error in response.json()["detail"]
    )
    assert client.get("/cards").json() == before


def test_create_card_with_missing_title_is_rejected():
    before = client.get("/cards").json()

    response = client.post(
        "/cards",
        json={"description": "No title supplied"},
    )

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", "title"]
        and error["type"] == "missing"
        for error in response.json()["detail"]
    )
    assert client.get("/cards").json() == before


def test_create_card_with_malformed_json_is_rejected():
    before = client.get("/cards").json()

    response = client.post(
        "/cards",
        content=b'{"title": "Broken"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert client.get("/cards").json() == before


def test_create_card_with_wrong_title_type_is_rejected():
    before = client.get("/cards").json()

    response = client.post(
        "/cards",
        json={"title": 123},
    )

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", "title"]
        for error in response.json()["detail"]
    )
    assert client.get("/cards").json() == before
