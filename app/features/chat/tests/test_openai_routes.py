"""Tests for OpenAI-compatible chat completions endpoint."""

import os
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_environment():
    """Set up test environment."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "ANTHROPIC_MODEL": "claude-sonnet-4-5",
    }
    with patch.dict(os.environ, env_vars):
        from app.core.agents.base import get_agent
        from app.core.config import get_settings

        get_settings.cache_clear()
        get_agent.cache_clear()
        yield
        get_settings.cache_clear()
        get_agent.cache_clear()


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_agent_run():
    """Mock the agent.run() method for non-streaming."""
    mock_result = MagicMock()
    mock_result.output = "Hello! I'm Jasque, your AI assistant."
    mock_response = MagicMock()
    mock_response.model_name = "claude-sonnet-4-5"
    mock_result.response = mock_response
    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 15
    mock_usage.total_tokens = 25
    mock_result.usage.return_value = mock_usage
    return mock_result


def test_chat_completions_non_streaming(client, mock_agent_run):
    """Test non-streaming chat completion response format."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [{"role": "user", "content": "Hello!"}],
                "stream": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "jasque"
        assert len(data["choices"]) == 1
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert data["choices"][0]["message"]["content"] == "Hello! I'm Jasque, your AI assistant."
        assert data["choices"][0]["finish_reason"] == "stop"


def test_chat_completions_returns_usage(client, mock_agent_run):
    """Test that usage information is returned."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [{"role": "user", "content": "Hello!"}],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usage"]["prompt_tokens"] == 10
        assert data["usage"]["completion_tokens"] == 15
        assert data["usage"]["total_tokens"] == 25


def test_chat_completions_with_history(client, mock_agent_run):
    """Test that message history is passed to agent."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [
                    {"role": "user", "content": "What's 2+2?"},
                    {"role": "assistant", "content": "4"},
                    {"role": "user", "content": "And 3+3?"},
                ],
            },
        )

        assert response.status_code == 200
        # Verify agent.run was called with message_history
        mock_agent.run.assert_called_once()
        call_kwargs = mock_agent.run.call_args.kwargs
        assert "message_history" in call_kwargs
        assert len(call_kwargs["message_history"]) == 2  # First user + assistant


def test_chat_completions_empty_messages(client):
    """Test error response when no messages provided."""
    response = client.post(
        "/v1/chat/completions",
        json={"model": "jasque", "messages": []},
    )

    assert response.status_code == 400
    assert "No user message found" in response.json()["detail"]


def test_chat_completions_no_user_message(client):
    """Test error response when no user message in messages."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "jasque",
            "messages": [{"role": "assistant", "content": "Hello!"}],
        },
    )

    assert response.status_code == 400
    assert "No user message found" in response.json()["detail"]


def test_chat_completions_error_handling(client):
    """Test error response format on agent failure."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = Exception("API Error")
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [{"role": "user", "content": "Hello!"}],
            },
        )

        assert response.status_code == 500
        assert "Agent execution failed" in response.json()["detail"]


def test_chat_completions_streaming_returns_sse(client):
    """Test streaming response returns SSE format."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        # We need to mock the entire streaming generator for this test
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent

        # Patch the generate_sse_stream function to return a simple generator
        async def mock_stream(*args: Any, **kwargs: Any) -> AsyncIterator[str]:
            yield 'data: {"id":"test","object":"chat.completion.chunk","created":1234567890,"model":"jasque","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}\n\n'
            yield 'data: {"id":"test","object":"chat.completion.chunk","created":1234567890,"model":"jasque","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n'
            yield 'data: {"id":"test","object":"chat.completion.chunk","created":1234567890,"model":"jasque","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
            yield "data: [DONE]\n\n"

        with patch(
            "app.features.chat.openai_routes.generate_sse_stream", return_value=mock_stream()
        ):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "jasque",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": True,
                },
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Check the response content
            content = response.text
            assert "data: " in content
            assert "chat.completion.chunk" in content
            assert "[DONE]" in content


def test_chat_completions_array_content(client, mock_agent_run):
    """Test handling of array content format (multi-modal)."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What's in this image?"},
                        ],
                    }
                ],
            },
        )

        assert response.status_code == 200
        # Verify the message was processed correctly
        mock_agent.run.assert_called_once()


def test_chat_completions_system_message_ignored(client, mock_agent_run):
    """Test that system messages are ignored (agent has own prompt)."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"},
                ],
            },
        )

        assert response.status_code == 200
        # System message should be ignored in history
        call_kwargs = mock_agent.run.call_args.kwargs
        # History should be empty since system is ignored and only the last user msg is prompt
        assert len(call_kwargs["message_history"]) == 0


# =============================================================================
# Conversation History Resilience Tests
# =============================================================================


def test_chat_completions_rejects_malformed_tool_calls(client):
    """Test that malformed tool call arguments return HTTP 400 with actionable message."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "jasque",
            "messages": [
                {"role": "user", "content": "Hello"},
                {
                    "role": "assistant",
                    "content": "Using a tool",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "obsidian_query_vault",
                                "arguments": "{invalid json",  # Malformed JSON
                            },
                        }
                    ],
                },
                {"role": "user", "content": "What happened?"},
            ],
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "malformed tool call" in detail.lower() or "invalid data" in detail.lower()
    assert "start a new conversation" in detail.lower()


def test_chat_completions_accepts_valid_tool_calls(client, mock_agent_run):
    """Test that valid tool call arguments are accepted."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": [
                    {"role": "user", "content": "List my notes"},
                    {
                        "role": "assistant",
                        "content": "Let me check your vault",
                        "tool_calls": [
                            {
                                "id": "call_valid",
                                "type": "function",
                                "function": {
                                    "name": "obsidian_query_vault",
                                    "arguments": '{"operation": "list_notes"}',  # Valid JSON
                                },
                            }
                        ],
                    },
                    {"role": "user", "content": "Thanks!"},
                ],
            },
        )

        assert response.status_code == 200


def test_chat_completions_truncates_long_history(client, mock_agent_run):
    """Test that long conversation history is truncated to max_messages."""
    with patch("app.features.chat.openai_routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent

        # Create a conversation with more messages than the default limit (50)
        # We'll use 60 messages (30 pairs of user/assistant)
        messages = []
        for i in range(30):
            messages.append({"role": "user", "content": f"Message {i}"})
            messages.append({"role": "assistant", "content": f"Response {i}"})
        # Add final user message (this becomes the prompt, not part of history)
        messages.append({"role": "user", "content": "Final question"})

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "jasque",
                "messages": messages,
            },
        )

        assert response.status_code == 200
        # Agent should have been called with truncated history
        call_kwargs = mock_agent.run.call_args.kwargs
        # History is truncated to max_conversation_messages (default 50)
        assert len(call_kwargs["message_history"]) <= 50


def test_chat_completions_handles_truncated_json_error_message(client):
    """Test that truncated JSON (EOF while parsing) returns actionable error."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "jasque",
            "messages": [
                {"role": "user", "content": "Create a note"},
                {
                    "role": "assistant",
                    "content": "Creating",
                    "tool_calls": [
                        {
                            "id": "call_456",
                            "type": "function",
                            "function": {
                                "name": "obsidian_manage_notes",
                                # Truncated JSON (simulating corrupted history)
                                "arguments": '{"operation": "create", "path": "test.md", "content": "Hello',
                            },
                        }
                    ],
                },
                {"role": "user", "content": "Did it work?"},
            ],
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    # Should mention the issue and suggest starting a new conversation
    assert "start a new conversation" in detail.lower()
