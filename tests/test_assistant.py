import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import assistant_service
import app.main as main_module


client = TestClient(main_module.app)


def make_tool_call(
    name="search_cards",
    arguments='{"query": ""}',
    call_id="call-1",
):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=arguments,
        ),
    )


class FakeAssistantMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none=False):
        data = {
            "role": "assistant",
            "content": self.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ],
        }

        if exclude_none:
            return {
                key: value
                for key, value in data.items()
                if value is not None
            }

        return data


def fake_response(content=None, tool_calls=None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=FakeAssistantMessage(content, tool_calls)
            )
        ]
    )


@pytest.fixture(autouse=True)
def block_real_llm(monkeypatch):
    """Fail the test if anything tries to make a real LLM call."""

    def fail(*args, **kwargs):
        raise AssertionError("Real LLM call attempted during test")

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fail,
    )


def test_successful_response_uses_mocked_llm(monkeypatch):
    def fake_chat_completion(messages, **kwargs):
        assert messages[-1] == {
            "role": "user",
            "content": "How many cards are on the board?",
        }
        return fake_response(content="The board is currently empty.")

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    response = client.post(
        "/assistant/chat",
        json={"message": "How many cards are on the board?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "The board is currently empty."
    }


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message_returns_422(message, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("LLM must not be called for an empty message")

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fail,
    )

    response = client.post(
        "/assistant/chat",
        json={"message": message},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Message cannot be empty"
    }


def test_assistant_searches_and_returns_real_board_data(monkeypatch):
    login_card = client.post(
        "/cards",
        json={
            "title": "Build Login",
            "description": "Implement authentication",
        },
    ).json()
    client.post(
        "/cards",
        json={
            "title": "Write Docs",
            "description": "Document the API",
        },
    )

    call_count = 0
    tool_result = None

    def fake_chat_completion(messages, **kwargs):
        nonlocal call_count, tool_result
        call_count += 1

        if call_count == 1:
            return fake_response(
                tool_calls=[
                    make_tool_call(arguments='{"query": "login"}')
                ]
            )

        tool_result = json.loads(messages[-1]["content"])
        return fake_response(
            content=f"Found {len(tool_result)} matching card(s)."
        )

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    response = client.post(
        "/assistant/chat",
        json={"message": "Find the login card"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Found 1 matching card(s)."
    }
    assert call_count == 2
    assert [card["id"] for card in tool_result] == [
        login_card["id"]
    ]
    assert tool_result[0]["title"] == "Build Login"


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_error"),
    [
        (
            "search_cards",
            "{invalid json",
            "Expecting",
        ),
        (
            "search_cards",
            '{"query": 123}',
            "Query must be a string",
        ),
        (
            "unknown_tool",
            '{"query": "login"}',
            "Unknown tool",
        ),
    ],
)
def test_tool_call_errors_are_passed_back_to_model(
    tool_name,
    arguments,
    expected_error,
    monkeypatch,
):
    call_count = 0
    tool_result = None

    def fake_chat_completion(messages, **kwargs):
        nonlocal call_count, tool_result
        call_count += 1

        if call_count == 1:
            return fake_response(
                tool_calls=[
                    make_tool_call(
                        name=tool_name,
                        arguments=arguments,
                    )
                ]
            )

        tool_result = json.loads(messages[-1]["content"])
        return fake_response(
            content="I could not complete the search."
        )

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    response = client.post(
        "/assistant/chat",
        json={"message": "Find matching cards"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "I could not complete the search."
    }
    assert call_count == 2
    assert expected_error in tool_result["error"]


def run_single_proposal(monkeypatch, tool_name, arguments):
    """Ask the assistant once and return the response plus tool result."""

    call_count = 0
    tool_result = None

    def fake_chat_completion(messages, **kwargs):
        nonlocal call_count, tool_result
        call_count += 1

        if call_count == 1:
            return fake_response(
                tool_calls=[
                    make_tool_call(
                        name=tool_name,
                        arguments=json.dumps(arguments),
                    )
                ]
            )

        tool_result = json.loads(messages[-1]["content"])
        return fake_response(
            content="Please confirm the proposed change."
        )

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    response = client.post(
        "/assistant/chat",
        json={"message": "Do it"},
    )

    return response, tool_result


def test_assistant_proposes_card_creation_without_writing(monkeypatch):
    before = client.get("/cards").json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_create_card",
        {
            "title": "New card",
            "description": "Draft description",
            "assignee": "Alex",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Please confirm the proposed change.",
        "proposal": {
            "action": "create_card",
            "title": "New card",
            "description": "Draft description",
            "assignee": "Alex",
        },
    }
    assert tool_result["proposal"]["action"] == "create_card"
    assert client.get("/cards").json() == before


def test_create_proposal_treats_null_description_as_empty(monkeypatch):
    before = client.get("/cards").json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_create_card",
        {
            "title": "Null description",
            "description": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["proposal"] == {
        "action": "create_card",
        "title": "Null description",
        "description": "",
    }
    assert client.get("/cards").json() == before


def test_create_proposal_omits_blank_assignee(monkeypatch):
    before = client.get("/cards").json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_create_card",
        {
            "title": "Blank assignee",
            "assignee": "   ",
        },
    )

    assert response.status_code == 200

    proposal = response.json()["proposal"]
    assert proposal == {
        "action": "create_card",
        "title": "Blank assignee",
        "description": "",
    }
    assert "assignee" not in proposal
    assert client.get("/cards").json() == before


def test_text_only_proposal_claim_returns_no_proposal(monkeypatch):
    claim = "I prepared a create-card proposal. Please confirm it."

    def fake_chat_completion(messages, **kwargs):
        return fake_response(content=claim)

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    before = client.get("/cards").json()

    response = client.post(
        "/assistant/chat",
        json={"message": "Create a card titled Demo"},
    )

    assert response.status_code == 200
    body = response.json()

    # The model only claimed a proposal in text. The API must not turn
    # that claim into a structured proposal, so the frontend has nothing
    # to offer for confirmation and no write occurs.
    assert "proposal" not in body
    assert body["reply"] == claim
    assert client.get("/cards").json() == before


def test_assistant_proposes_card_move_without_writing(monkeypatch):
    card = client.post(
        "/cards",
        json={"title": "Move me"},
    ).json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_move_card",
        {"card_id": card["id"], "status": "ready"},
    )

    assert response.status_code == 200
    assert response.json()["proposal"] == {
        "action": "move_card",
        "card_id": card["id"],
        "status": "ready",
    }
    assert tool_result["proposal"]["card_id"] == card["id"]

    current = client.get(f"/cards/{card['id']}").json()
    assert current["status"] == "spec"


def test_assistant_proposes_comment_without_writing(monkeypatch):
    card = client.post(
        "/cards",
        json={"title": "Comment card"},
    ).json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_add_comment",
        {
            "card_id": card["id"],
            "author": "Sam",
            "text": "Looks good.",
        },
    )

    assert response.status_code == 200
    assert response.json()["proposal"] == {
        "action": "add_comment",
        "card_id": card["id"],
        "author": "Sam",
        "text": "Looks good.",
    }
    assert tool_result["proposal"]["text"] == "Looks good."

    comments = client.get(f"/cards/{card['id']}/comments").json()
    assert comments == []


def test_assistant_rejects_move_for_missing_card(monkeypatch):
    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_move_card",
        {"card_id": 9999, "status": "ready"},
    )

    assert response.status_code == 200
    assert "proposal" not in response.json()
    assert "not found" in tool_result["error"]


def test_assistant_rejects_illegal_status_move(monkeypatch):
    card = client.post(
        "/cards",
        json={"title": "Stay in spec"},
    ).json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_move_card",
        {"card_id": card["id"], "status": "done"},
    )

    assert response.status_code == 200
    assert "proposal" not in response.json()
    assert "Cannot move card from spec to done" in tool_result["error"]

    current = client.get(f"/cards/{card['id']}").json()
    assert current["status"] == "spec"


def test_assistant_rejects_invalid_card_proposal(monkeypatch):
    before = client.get("/cards").json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_create_card",
        {"title": ""},
    )

    assert response.status_code == 200
    assert "proposal" not in response.json()
    assert "at least 1 character" in tool_result["error"]
    assert client.get("/cards").json() == before


def test_assistant_rejects_invalid_comment_proposal(monkeypatch):
    card = client.post(
        "/cards",
        json={"title": "Comment validation"},
    ).json()

    response, tool_result = run_single_proposal(
        monkeypatch,
        "propose_add_comment",
        {
            "card_id": card["id"],
            "author": "Sam",
            "text": "",
        },
    )

    assert response.status_code == 200
    assert "proposal" not in response.json()
    assert "at least 1 character" in tool_result["error"]

    comments = client.get(f"/cards/{card['id']}/comments").json()
    assert comments == []


def test_assistant_allows_only_one_proposal(monkeypatch):
    call_count = 0
    tool_results = []

    def fake_chat_completion(messages, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return fake_response(
                tool_calls=[
                    make_tool_call(
                        name="propose_create_card",
                        arguments='{"title": "First"}',
                        call_id="call-1",
                    ),
                    make_tool_call(
                        name="propose_create_card",
                        arguments='{"title": "Second"}',
                        call_id="call-2",
                    ),
                ]
            )

        tool_results.extend(
            json.loads(message["content"])
            for message in messages
            if message["role"] == "tool"
        )
        return fake_response(
            content="Please confirm the first proposal."
        )

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fake_chat_completion,
    )

    response = client.post(
        "/assistant/chat",
        json={"message": "Create two cards"},
    )

    assert response.status_code == 200
    assert response.json()["proposal"]["title"] == "First"
    assert "proposal" in tool_results[0]
    assert "Only one proposal" in tool_results[1]["error"]
    assert client.get("/cards").json() == []


def test_llm_failure_returns_503_without_writes(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("All configured models failed")

    monkeypatch.setattr(
        assistant_service,
        "chat_completion",
        fail,
    )

    before = client.get("/cards").json()

    response = client.post(
        "/assistant/chat",
        json={"message": "Create a card"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "The assistant is temporarily unavailable. "
            "Please try again."
        )
    }
    assert client.get("/cards").json() == before


def test_llm_chat_completion_falls_back_to_next_model(monkeypatch):
    import llm

    attempted_models = []

    class FakeCompletions:
        def create(self, model, messages, **kwargs):
            attempted_models.append(model)

            if model == "first-model":
                raise RuntimeError("model unavailable")

            return SimpleNamespace(choices=[], usage=None)

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm, "Groq", FakeGroq)
    monkeypatch.setattr(
        llm,
        "get_models",
        lambda: ["first-model", "second-model"],
    )

    response = llm.chat_completion(
        messages=[{"role": "user", "content": "Hello"}]
    )

    assert attempted_models == ["first-model", "second-model"]
    assert response.choices == []
