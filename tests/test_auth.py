from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import assistant_service
import database
from app import auth
import app.main as main_module


def make_client(token=None):
    client = TestClient(main_module.app)

    if token is not None:
        client.headers["Authorization"] = f"Bearer {token}"

    return client


def clear_auth_rows():
    connection = database.get_connection()

    try:
        with connection:
            connection.execute("DELETE FROM sessions")
            connection.execute("DELETE FROM users")
    finally:
        connection.close()


PROTECTED_REQUESTS = [
    ("get", "/cards", {}),
    ("post", "/cards", {"json": {"title": "Protected card"}}),
    ("patch", "/cards/1", {"json": {"title": "Protected update"}}),
    ("delete", "/cards/1", {}),
    ("get", "/cards/1/comments", {}),
    (
        "post",
        "/cards/1/comments",
        {"json": {"author": "Sam", "text": "Protected comment"}},
    ),
    ("post", "/assistant/chat", {"json": {"message": "How many cards?"}}),
]


def test_public_endpoints_do_not_require_authentication():
    client = make_client()

    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("role", ["admin", "member"])
def test_login_returns_token_and_role(seeded_users, role):
    credentials = seeded_users[role]
    client = make_client()

    response = client.post(
        "/auth/login",
        json={
            "username": credentials["username"],
            "password": seeded_users["password"],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["username"] == credentials["username"]
    assert body["role"] == role

    # The issued token must authenticate a protected request.
    client.headers["Authorization"] = f"Bearer {body['access_token']}"
    assert client.get("/cards").status_code == 200


def test_login_rejects_wrong_password(seeded_users):
    response = make_client().post(
        "/auth/login",
        json={
            "username": seeded_users["admin"]["username"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_unknown_user(seeded_users):
    response = make_client().post(
        "/auth/login",
        json={
            "username": "does-not-exist",
            "password": seeded_users["password"],
        },
    )

    assert response.status_code == 401


def test_login_rejects_missing_fields(seeded_users):
    client = make_client()

    assert client.post("/auth/login", json={"username": "only"}).status_code == 422
    assert client.post("/auth/login", json={"password": "only"}).status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    PROTECTED_REQUESTS,
    ids=[f"{method.upper()} {path}" for method, path, _ in PROTECTED_REQUESTS],
)
def test_missing_token_returns_401(seeded_users, method, path, kwargs):
    response = getattr(make_client(), method)(path, **kwargs)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_prd_preview_requires_authentication(seeded_users):
    response = make_client().post(
        "/prd/preview",
        files={"file": ("prd.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 401


def test_invalid_token_returns_401(seeded_users):
    response = make_client("not-a-real-token").get("/cards")

    assert response.status_code == 401


def test_malformed_authorization_scheme_returns_401(seeded_users):
    client = make_client()
    client.headers["Authorization"] = "Basic abc123"

    assert client.get("/cards").status_code == 401


def test_expired_token_returns_401_and_is_removed(seeded_users):
    token = auth.issue_token(
        seeded_users["member"]["id"],
        ttl_seconds=-60,
    )

    response = make_client(token).get("/cards")

    assert response.status_code == 401

    connection = database.get_connection()
    try:
        stored = connection.execute(
            "SELECT COUNT(*) FROM sessions WHERE token_hash = ?",
            (auth.hash_token(token),),
        ).fetchone()[0]
    finally:
        connection.close()

    assert stored == 0


def test_member_can_manage_cards_and_comments(member_client):
    created = member_client.post(
        "/cards",
        json={"title": "Member card", "description": "Allowed"},
    )

    assert created.status_code == 201
    card_id = created.json()["id"]

    updated = member_client.patch(
        f"/cards/{card_id}",
        json={"status": "ready"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "ready"

    comment = member_client.post(
        f"/cards/{card_id}/comments",
        json={"author": "Sam", "text": "Member comment"},
    )
    assert comment.status_code == 201

    assert member_client.get("/cards").status_code == 200
    assert member_client.get(f"/cards/{card_id}").status_code == 200
    assert member_client.get(f"/cards/{card_id}/comments").status_code == 200


def test_member_cannot_delete_card(admin_client, member_client):
    card_id = admin_client.post(
        "/cards",
        json={"title": "Admin-owned card"},
    ).json()["id"]

    response = member_client.delete(f"/cards/{card_id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin privileges required"

    # The card must still exist and be readable.
    assert admin_client.get(f"/cards/{card_id}").status_code == 200


def test_admin_can_delete_card(admin_client):
    card_id = admin_client.post(
        "/cards",
        json={"title": "Deletable card"},
    ).json()["id"]

    assert admin_client.delete(f"/cards/{card_id}").status_code == 204


def test_invalid_token_takes_precedence_over_role_check(seeded_users):
    response = make_client("invalid-token").delete("/cards/1")

    assert response.status_code == 401


def test_member_can_use_assistant(monkeypatch, member_client):
    def fake_chat_completion(messages, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="The board is available.",
                        tool_calls=[],
                    )
                )
            ]
        )

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    response = member_client.post(
        "/assistant/chat",
        json={"message": "Is the board available?"},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "The board is available."


def test_password_hash_is_salted_and_verifiable():
    first = auth.hash_password("correct horse")
    second = auth.hash_password("correct horse")

    assert first.startswith("scrypt$")
    assert first != second
    assert "correct horse" not in first
    assert auth.verify_password("correct horse", first)
    assert not auth.verify_password("wrong", first)
    assert not auth.verify_password("correct horse", "not-a-hash")


def test_login_stores_only_token_hash(seeded_users):
    token = make_client().post(
        "/auth/login",
        json={
            "username": seeded_users["admin"]["username"],
            "password": seeded_users["password"],
        },
    ).json()["access_token"]

    connection = database.get_connection()
    try:
        stored_hashes = [
            row["token_hash"]
            for row in connection.execute(
                "SELECT token_hash FROM sessions"
            ).fetchall()
        ]
    finally:
        connection.close()

    assert token not in stored_hashes
    assert auth.hash_token(token) in stored_hashes


def test_bootstrap_fails_without_credentials(monkeypatch):
    clear_auth_rows()
    monkeypatch.delenv("BOOTSTRAP_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="bootstrap credentials"):
        auth.ensure_bootstrap_admin()

    assert database.count_users() == 0


def test_application_startup_fails_without_bootstrap_credentials(
    monkeypatch,
):
    clear_auth_rows()
    monkeypatch.delenv("BOOTSTRAP_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="bootstrap credentials"):
        with TestClient(main_module.app):
            pass


def test_bootstrap_creates_admin_from_environment(monkeypatch):
    clear_auth_rows()
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "bootstrap-password")

    auth.ensure_bootstrap_admin()

    user = database.get_user_by_username("bootstrap-admin")

    assert user is not None
    assert user["role"] == "admin"
    assert auth.verify_password(
        "bootstrap-password",
        user["password_hash"],
    )

    # Running again must not create a second bootstrap user.
    auth.ensure_bootstrap_admin()
    assert database.count_users() == 1
