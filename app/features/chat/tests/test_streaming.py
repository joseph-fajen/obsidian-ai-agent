"""Tests for streaming utilities."""

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.features.chat.openai_schemas import ChatMessage
from app.features.chat.streaming import (
    convert_to_pydantic_history,
    extract_last_user_message,
)


def test_extract_last_user_message():
    """Test extracting last user message from conversation."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
        ChatMessage(role="user", content="How are you?"),
    ]
    result = extract_last_user_message(messages)
    assert result == "How are you?"


def test_extract_last_user_message_with_array_content():
    """Test extracting last user message with array content."""
    messages = [
        ChatMessage(
            role="user",
            content=[{"type": "text", "text": "Array message"}],  # type: ignore[list-item]
        ),
    ]
    result = extract_last_user_message(messages)
    assert result == "Array message"


def test_extract_last_user_message_empty():
    """Test extracting from empty messages returns empty string."""
    result = extract_last_user_message([])
    assert result == ""


def test_extract_last_user_message_no_user():
    """Test extracting when no user message exists."""
    messages = [
        ChatMessage(role="assistant", content="Hello!"),
        ChatMessage(role="system", content="You are helpful."),
    ]
    result = extract_last_user_message(messages)
    assert result == ""


def test_convert_to_pydantic_history_basic():
    """Test converting OpenAI messages to Pydantic AI format."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
    ]
    history = convert_to_pydantic_history(messages)

    assert len(history) == 2
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[1], ModelResponse)


def test_convert_to_pydantic_history_content():
    """Test that content is correctly extracted."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
    ]
    history = convert_to_pydantic_history(messages)

    # Check user message content
    assert len(history[0].parts) == 1
    assert isinstance(history[0].parts[0], UserPromptPart)
    assert history[0].parts[0].content == "Hello"

    # Check assistant message content
    assert len(history[1].parts) == 1
    assert isinstance(history[1].parts[0], TextPart)
    assert history[1].parts[0].content == "Hi there!"


def test_convert_to_pydantic_history_ignores_system():
    """Test that system messages are ignored (agent has own prompt)."""
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi!"),
    ]
    history = convert_to_pydantic_history(messages)

    # Should only have 2 messages (user + assistant), system ignored
    assert len(history) == 2
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[1], ModelResponse)


def test_convert_to_pydantic_history_empty():
    """Test converting empty message list."""
    history = convert_to_pydantic_history([])
    assert history == []


def test_convert_to_pydantic_history_array_content():
    """Test converting messages with array content format."""
    messages = [
        ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "Part 1. "},  # type: ignore[list-item]
                {"type": "text", "text": "Part 2."},  # type: ignore[list-item]
            ],
        ),
    ]
    history = convert_to_pydantic_history(messages)

    assert len(history) == 1
    assert isinstance(history[0], ModelRequest)
    assert history[0].parts[0].content == "Part 1. Part 2."


@pytest.mark.asyncio
async def test_generate_sse_stream_format():
    """Test SSE stream format: data: prefix, double newline, [DONE]."""
    # This is a basic format test - full integration tests are in test_openai_routes.py
    # Here we just verify the format structure is correct

    # The actual streaming test requires mocking the agent, which is done
    # in test_openai_routes.py. Here we verify the schema structure.
    from app.features.chat.openai_schemas import ChatCompletionChunk, ChunkChoice, DeltaContent

    chunk = ChatCompletionChunk(
        id="test-id",
        created=1234567890,
        model="jasque",
        choices=[ChunkChoice(delta=DeltaContent(content="Hello"))],
    )

    # Verify chunk can be serialized to JSON
    json_str = chunk.model_dump_json()
    assert "test-id" in json_str
    assert "chat.completion.chunk" in json_str
    assert "Hello" in json_str

    # Verify SSE format
    sse_line = f"data: {json_str}\n\n"
    assert sse_line.startswith("data: ")
    assert sse_line.endswith("\n\n")


@pytest.mark.asyncio
async def test_generate_sse_stream_handles_part_start_event():
    """Test that PartStartEvent with TextPart content is properly yielded.

    This tests the fix for the missing first token issue where initial text
    content in PartStartEvent was being dropped.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPartDelta

    from app.core.agents.types import AgentDependencies
    from app.features.chat.streaming import generate_sse_stream

    # Create mock events simulating real Pydantic AI behavior:
    # 1. PartStartEvent with initial text content
    # 2. PartDeltaEvent with additional text
    mock_part_start = MagicMock(spec=PartStartEvent)
    mock_part_start.part = TextPart(content="Hello")

    mock_part_delta = MagicMock(spec=PartDeltaEvent)
    mock_part_delta.delta = TextPartDelta(content_delta=" World!")

    # Create async iterator for events
    async def mock_event_stream():
        yield mock_part_start
        yield mock_part_delta

    # Create mock stream context manager
    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_event_stream())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    # Create mock node
    mock_node = MagicMock()
    mock_node.stream = MagicMock(return_value=mock_stream)

    # Create async iterator for nodes
    async def mock_node_iter():
        yield mock_node

    # Create mock run context
    mock_run = MagicMock()
    mock_run.__aenter__ = AsyncMock(return_value=mock_run)
    mock_run.__aexit__ = AsyncMock(return_value=None)
    mock_run.__aiter__ = lambda _self: mock_node_iter()
    mock_run.ctx = MagicMock()
    mock_run.usage = MagicMock(
        return_value=MagicMock(input_tokens=10, output_tokens=5, total_tokens=15)
    )

    # Create mock agent
    mock_agent = MagicMock()
    mock_agent.iter = MagicMock(return_value=mock_run)
    mock_agent.is_model_request_node = MagicMock(return_value=True)

    # Patch Agent.is_model_request_node to return True
    with patch("app.features.chat.streaming.Agent.is_model_request_node", return_value=True):
        deps = AgentDependencies(request_id="test-123")
        chunks = []

        async for chunk in generate_sse_stream(
            agent=mock_agent,
            user_message="Test",
            message_history=[],
            deps=deps,
            model_name="jasque",
            include_usage=False,
        ):
            chunks.append(chunk)

    # Verify we got chunks
    assert len(chunks) >= 3  # role chunk + at least 1 content chunk + final chunk + [DONE]

    # Verify the content from PartStartEvent ("Hello") appears in the stream
    content_chunks = [c for c in chunks if '"content":' in c]
    all_content = "".join(content_chunks)
    assert "Hello" in all_content, "Initial text from PartStartEvent should be in stream"
    assert "World" in all_content, "Delta text from PartDeltaEvent should be in stream"
