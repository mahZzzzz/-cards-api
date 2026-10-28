
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


import pytest

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
