import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import prd_service
from schemas import Breakdown, CardDraft


client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def authenticate_admin(admin_token):
    client.headers["Authorization"] = f"Bearer {admin_token}"
    yield
    client.headers.pop("Authorization", None)


PDF_BYTES = b"%PDF-1.4\n% minimal test document\n"


@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    """Block real LLM and embedding work unless a test overrides it."""

    def fail_llm(*args, **kwargs):
        raise AssertionError("LLM must not be called during this test")

    monkeypatch.setattr(
        prd_service,
        "structured_completion",
        fail_llm,
    )
    monkeypatch.setattr(
        prd_service,
        "similar_cards",
        lambda *args, **kwargs: [],
    )


def pdf_sections():
    return [
        {
            "heading": "Page 1",
            "page": 1,
            "text": "Users must be able to log in.",
        }
    ]


def make_breakdown():
    return Breakdown(
        cards=[
            CardDraft(
                title="Build Login",
                goal="Allow users to sign in.",
                acceptance_criteria=[
                    "Valid credentials are accepted.",
                ],
                dependencies=[],
                prd_section="Page 1",
                possible_duplicate=False,
            )
        ],
        ambiguities=[
            "Session timeout is not specified.",
        ],
    )


def post_pdf(filename="prd.pdf", content=PDF_BYTES):
    return client.post(
        "/prd/preview",
        files={
            "file": (
                filename,
                content,
                "application/pdf",
            )
        },
    )


def test_successful_pdf_preview_with_mocked_ai(monkeypatch):
    monkeypatch.setattr(
        prd_service,
        "extract_pdf_sections",
        lambda path: pdf_sections(),
    )
    monkeypatch.setattr(
        prd_service,
        "structured_completion",
        lambda **kwargs: make_breakdown(),
    )

    response = post_pdf()

    assert response.status_code == 200

    body = response.json()
    assert body["ambiguities"] == [
        "Session timeout is not specified.",
    ]
    assert body["cards"] == [
        {
            "title": "Build Login",
            "goal": "Allow users to sign in.",
            "acceptance_criteria": [
                "Valid credentials are accepted.",
            ],
            "dependencies": [],
            "prd_section": "Page 1",
            "possible_duplicate": False,
        }
    ]

    assert client.get("/cards").json() == []


def test_non_pdf_upload_is_rejected():
    response = post_pdf(
        filename="notes.txt",
        content=b"this is not a pdf",
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Please upload a PDF file."
    }


def test_invalid_pdf_content_is_rejected():
    response = post_pdf(
        filename="fake.pdf",
        content=b"this is not a pdf",
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid PDF file."
    }


def test_empty_pdf_upload_is_rejected():
    response = post_pdf(
        filename="empty.pdf",
        content=b"",
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid PDF file."
    }


def test_unreadable_pdf_returns_422(monkeypatch):
    monkeypatch.setattr(
        prd_service,
        "extract_pdf_sections",
        lambda path: [],
    )

    response = post_pdf()

    assert response.status_code == 422
    assert response.json() == {
        "detail": "No readable sections found in PDF"
    }


def test_oversized_pdf_is_rejected():
    oversized = b"%PDF-" + b"0" * (10 * 1024 * 1024)

    response = post_pdf(
        filename="large.pdf",
        content=oversized,
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "PDF is too large. Maximum size is 10 MB."
    }


def test_invalid_generated_drafts_return_422(monkeypatch):
    monkeypatch.setattr(
        prd_service,
        "extract_pdf_sections",
        lambda path: pdf_sections(),
    )

    def invalid_structured_completion(**kwargs):
        return Breakdown.model_validate({
            "cards": [
                {
                    "title": "",
                    "goal": "",
                    "acceptance_criteria": [],
                    "dependencies": [],
                    "prd_section": "",
                }
            ],
            "ambiguities": [],
        })

    monkeypatch.setattr(
        prd_service,
        "structured_completion",
        invalid_structured_completion,
    )

    response = post_pdf()

    assert response.status_code == 422
    assert "cards.0" in response.json()["detail"]
    assert client.get("/cards").json() == []


def test_preview_does_not_create_board_cards(monkeypatch):
    existing = client.post(
        "/cards",
        json={
            "title": "Existing card",
            "description": "Must remain the only card",
        },
    ).json()

    monkeypatch.setattr(
        prd_service,
        "extract_pdf_sections",
        lambda path: pdf_sections(),
    )
    monkeypatch.setattr(
        prd_service,
        "structured_completion",
        lambda **kwargs: Breakdown(
            cards=[
                CardDraft(
                    title="Suggested card one",
                    goal="First suggested goal.",
                    acceptance_criteria=["First criterion."],
                    dependencies=[],
                    prd_section="Page 1",
                    possible_duplicate=False,
                ),
                CardDraft(
                    title="Suggested card two",
                    goal="Second suggested goal.",
                    acceptance_criteria=["Second criterion."],
                    dependencies=[],
                    prd_section="Page 1",
                    possible_duplicate=False,
                ),
            ],
            ambiguities=[],
        ),
    )

    before = client.get("/cards").json()
    response = post_pdf()
    after = client.get("/cards").json()

    assert response.status_code == 200
    assert after == before
    assert [card["id"] for card in after] == [existing["id"]]
