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
