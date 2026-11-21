
import pytest
from fastapi.testclient import TestClient

from app.main import app, cards


@pytest.fixture(autouse=True)
def reset_cards():
    cards.clear()
    yield
    cards.clear()


def test_add_comment_to_card():
    client = TestClient(app)

    # Create a card
    response = client.post(
        "/cards",
        json={
            "title": "Build Login",
            "description": "Implement authentication"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Add a comment
    response = client.post(
        f"/cards/{card_id}/comments",
        json={
            "author": "Test User",
            "text": "Please add input validation."
        }
    )

    assert response.status_code == 201

    comment = response.json()

    assert comment["author"] == "Test User"
    assert comment["text"] == "Please add input validation."


def test_cannot_comment_on_nonexistent_card():
    client = TestClient(app)

    response = client.post(
        "/cards/999999/comments",
        json={
            "author": "Test User",
            "text": "This card does not exist."
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Card not found"


def test_list_card_comments():
    client = TestClient(app)

    # Create a card
    response = client.post(
        "/cards",
        json={
            "title": "Build Login",
            "description": "Implement authentication"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Add a comment
    response = client.post(
        f"/cards/{card_id}/comments",
        json={
            "author": "Test User",
            "text": "Please add input validation."
        }
    )

    assert response.status_code == 201

    # Retrieve comments
    response = client.get(f"/cards/{card_id}/comments")

    assert response.status_code == 200

    comments = response.json()

    assert len(comments) == 1
    assert comments[0]["author"] == "Test User"
    assert comments[0]["text"] == "Please add input validation."


@pytest.mark.parametrize(
    "payload",
    [
        {"author": "Test User", "text": ""},
        {"author": "", "text": "This is a comment."},
    ],
)
def test_reject_invalid_comment(payload):
    client = TestClient(app)

    response = client.post(
        "/cards",
        json={
            "title": "Test Card",
            "description": "Testing comment validation"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    response = client.post(
        f"/cards/{card_id}/comments",
        json=payload
    )

    assert response.status_code == 422

    
def test_assign_card_to_user():
    client = TestClient(app)

    # Create a card
    response = client.post(
        "/cards",
        json={
            "title": "Implement Login",
            "description": "Build authentication"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Assign the card to a user
    response = client.patch(
        f"/cards/{card_id}",
        json={"assignee": "Alex"}
    )

    assert response.status_code == 200
    assert response.json()["assignee"] == "Alex"

    # Verify the assignment is saved
    response = client.get(f"/cards/{card_id}")

    assert response.status_code == 200
    assert response.json()["assignee"] == "Alex"



def test_change_card_assignee():
    client = TestClient(app)

    response = client.post(
        "/cards",
        json={
            "title": "Implement Login",
            "description": "Build authentication"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Assign to Alex
    response = client.patch(
        f"/cards/{card_id}",
        json={"assignee": "Alex"}
    )

    assert response.status_code == 200
    assert response.json()["assignee"] == "Alex"

    # Change assignee to Sara
    response = client.patch(
        f"/cards/{card_id}",
        json={"assignee": "Sara"}
    )

    assert response.status_code == 200
    assert response.json()["assignee"] == "Sara"


def test_remove_card_assignee():
    client = TestClient(app)

    response = client.post(
        "/cards",
        json={
            "title": "Implement Login",
            "description": "Build authentication"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    # Assign the card
    response = client.patch(
        f"/cards/{card_id}",
        json={"assignee": "Alex"}
    )

    assert response.status_code == 200
    assert response.json()["assignee"] == "Alex"

    # Remove the assignee
    response = client.patch(
        f"/cards/{card_id}",
        json={"assignee": None}
    )

    assert response.status_code == 200
    assert response.json()["assignee"] is None

    # Verify the change was saved
    response = client.get(f"/cards/{card_id}")

    assert response.status_code == 200
    assert response.json()["assignee"] is None


@pytest.mark.parametrize("assignee", ["", "   "])
def test_reject_invalid_assignee(assignee):
    client = TestClient(app)

    response = client.post(
        "/cards",
        json={
            "title": "Test Assignment",
            "description": "Test invalid assignee"
        }
    )

    assert response.status_code == 201
    card_id = response.json()["id"]

    response = client.patch(
        f"/cards/{card_id}",
        json={"assignee": assignee}
    )

    assert response.status_code == 422


def test_create_card_with_assignee():
    client = TestClient(app)

    response = client.post(
        "/cards",
        json={
            "title": "Assigned on creation",
            "description": "Assignee supplied with the create request",
            "assignee": "Alex",
        },
    )

    assert response.status_code == 201

    card = response.json()
    assert card["assignee"] == "Alex"
    assert card["status"] == "spec"

    # Verify the assignment was stored with the new card.
    response = client.get(f"/cards/{card['id']}")

    assert response.status_code == 200
    assert response.json()["assignee"] == "Alex"


@pytest.mark.parametrize("assignee", ["", "   "])
def test_reject_invalid_assignee_on_create(assignee):
    client = TestClient(app)

    before = client.get("/cards").json()

    response = client.post(
        "/cards",
        json={
            "title": "Invalid assignee on create",
            "assignee": assignee,
        },
    )

    assert response.status_code == 422
    assert client.get("/cards").json() == before
