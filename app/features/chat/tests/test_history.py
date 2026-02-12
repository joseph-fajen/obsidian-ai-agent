"""Tests for conversation history validation and truncation."""

import pytest

from app.features.chat.history import (
    truncate_conversation_history,
    validate_tool_call_arguments,
)
from app.features.chat.openai_schemas import ChatMessage, ToolCall, ToolCallFunction
from app.shared.vault.exceptions import ConversationHistoryError

# =============================================================================
# Validation Tests
# =============================================================================


def test_validate_tool_call_arguments_valid_json():
    """Valid JSON in tool call arguments should pass validation."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(
            role="assistant",
            content="Using a tool",
            tool_calls=[
                ToolCall(
                    id="call_123",
                    function=ToolCallFunction(
                        name="obsidian_query_vault",
                        arguments='{"operation": "list_notes", "path": "projects"}',
                    ),
                )
            ],
        ),
    ]
    # Should not raise
    validate_tool_call_arguments(messages)


def test_validate_tool_call_arguments_invalid_json():
    """Malformed JSON in tool call arguments should raise ConversationHistoryError."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(
            role="assistant",
            content="Using a tool",
            tool_calls=[
                ToolCall(
                    id="call_123",
                    function=ToolCallFunction(
                        name="obsidian_query_vault",
                        arguments="{invalid json",  # Malformed JSON
                    ),
                )
            ],
        ),
    ]
    with pytest.raises(ConversationHistoryError) as exc_info:
        validate_tool_call_arguments(messages)

    assert "malformed tool call at message 1" in str(exc_info.value)
    assert "start a new conversation" in str(exc_info.value)


def test_validate_tool_call_arguments_truncated_json():
    """Truncated JSON (EOF while parsing) should raise ConversationHistoryError."""
    messages = [
        ChatMessage(
            role="assistant",
            content="Tool response",
            tool_calls=[
                ToolCall(
                    id="call_456",
                    function=ToolCallFunction(
                        name="obsidian_manage_notes",
                        arguments='{"operation": "create", "path": "test.md", "content": "Hello',
                    ),
                )
            ],
        ),
    ]
    with pytest.raises(ConversationHistoryError) as exc_info:
        validate_tool_call_arguments(messages)

    assert "malformed tool call at message 0" in str(exc_info.value)


def test_validate_tool_call_arguments_no_tool_calls():
    """Messages without tool_calls should pass validation."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
        ChatMessage(role="user", content="How are you?"),
    ]
    # Should not raise
    validate_tool_call_arguments(messages)


def test_validate_tool_call_arguments_empty_list():
    """Empty message list should pass validation."""
    validate_tool_call_arguments([])


def test_validate_tool_call_arguments_empty_tool_calls():
    """Empty tool_calls array should pass validation."""
    messages = [
        ChatMessage(
            role="assistant",
            content="No tools used",
            tool_calls=[],
        ),
    ]
    # Should not raise
    validate_tool_call_arguments(messages)


def test_validate_tool_call_arguments_multiple_tool_calls():
    """Multiple tool calls should all be validated."""
    messages = [
        ChatMessage(
            role="assistant",
            content="Using multiple tools",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=ToolCallFunction(
                        name="tool_1",
                        arguments='{"valid": true}',
                    ),
                ),
                ToolCall(
                    id="call_2",
                    function=ToolCallFunction(
                        name="tool_2",
                        arguments="{broken",  # Invalid
                    ),
                ),
            ],
        ),
    ]
    with pytest.raises(ConversationHistoryError):
        validate_tool_call_arguments(messages)


def test_validate_tool_call_arguments_valid_json_string():
    """Valid JSON string (like '123') should pass - it's valid JSON."""
    messages = [
        ChatMessage(
            role="assistant",
            content="Simple args",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=ToolCallFunction(
                        name="tool_1",
                        arguments='"just a string"',  # Valid JSON string
                    ),
                ),
            ],
        ),
    ]
    # Should not raise
    validate_tool_call_arguments(messages)


# =============================================================================
# Truncation Tests
# =============================================================================


def test_truncate_conversation_history_under_limit():
    """Messages under limit should be returned unchanged."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi!"),
    ]
    result = truncate_conversation_history(messages, max_messages=10)
    assert result == messages
    assert len(result) == 2


def test_truncate_conversation_history_over_limit():
    """Messages over limit should be truncated, keeping most recent."""
    messages = [
        ChatMessage(role="user", content="Message 1"),
        ChatMessage(role="assistant", content="Response 1"),
        ChatMessage(role="user", content="Message 2"),
        ChatMessage(role="assistant", content="Response 2"),
        ChatMessage(role="user", content="Message 3"),
    ]
    result = truncate_conversation_history(messages, max_messages=3)

    assert len(result) == 3
    # Should keep the 3 most recent (last 3: Message 2, Response 2, Message 3)
    assert result[0].content == "Message 2"
    assert result[1].content == "Response 2"
    assert result[2].content == "Message 3"


def test_truncate_conversation_history_exact_limit():
    """Messages at exact limit should not be truncated."""
    messages = [
        ChatMessage(role="user", content="Message 1"),
        ChatMessage(role="assistant", content="Response 1"),
        ChatMessage(role="user", content="Message 2"),
    ]
    result = truncate_conversation_history(messages, max_messages=3)

    assert len(result) == 3
    assert result == messages


def test_truncate_conversation_history_empty():
    """Empty message list should return empty."""
    result = truncate_conversation_history([], max_messages=10)
    assert result == []


def test_truncate_conversation_history_zero_limit():
    """Zero max_messages should return empty list."""
    messages = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi!"),
    ]
    result = truncate_conversation_history(messages, max_messages=0)
    assert result == []


def test_truncate_conversation_history_negative_limit():
    """Negative max_messages should return empty list."""
    messages = [
        ChatMessage(role="user", content="Hello"),
    ]
    result = truncate_conversation_history(messages, max_messages=-5)
    assert result == []


def test_truncate_conversation_history_preserves_tool_calls():
    """Truncation should preserve tool_calls on assistant messages."""
    messages = [
        ChatMessage(role="user", content="Old message"),
        ChatMessage(
            role="assistant",
            content="Tool response",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=ToolCallFunction(
                        name="test_tool",
                        arguments='{"key": "value"}',
                    ),
                )
            ],
        ),
        ChatMessage(role="user", content="Recent message"),
    ]
    result = truncate_conversation_history(messages, max_messages=2)

    assert len(result) == 2
    # Should keep the last 2 messages
    assert result[0].tool_calls is not None
    assert len(result[0].tool_calls) == 1
    assert result[0].tool_calls[0].id == "call_1"
