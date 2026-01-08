"""Tests for OpenAI-compatible schemas."""

from app.features.chat.openai_schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    TextContentPart,
    normalize_content,
)


def test_chat_message_string_content():
    """Test ChatMessage with simple string content."""
    msg = ChatMessage(role="user", content="Hello, world!")
    assert msg.role == "user"
    assert msg.content == "Hello, world!"


def test_chat_message_array_content():
    """Test ChatMessage with structured array content."""
    msg = ChatMessage(
        role="user",
        content=[TextContentPart(type="text", text="Hello from array!")],
    )
    assert msg.role == "user"
    assert isinstance(msg.content, list)
    assert len(msg.content) == 1


def test_normalize_content_string():
    """Test normalize_content with string input."""
    result = normalize_content("Hello, world!")
    assert result == "Hello, world!"


def test_normalize_content_array():
    """Test normalize_content with array input."""
    result = normalize_content([{"type": "text", "text": "Hello from array!"}])
    assert result == "Hello from array!"


def test_normalize_content_mixed_array():
    """Test normalize_content with mixed text/image array (only extracts text)."""
    result = normalize_content(
        [
            {"type": "text", "text": "Part 1. "},
            {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
            {"type": "text", "text": "Part 2."},
        ]
    )
    assert result == "Part 1. Part 2."


def test_normalize_content_empty_array():
    """Test normalize_content with empty array."""
    result = normalize_content([])
    assert result == ""


def test_normalize_content_array_no_text():
    """Test normalize_content with array containing no text parts."""
    result = normalize_content(
        [
            {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
        ]
    )
    assert result == ""


def test_chat_completion_request_defaults():
    """Test ChatCompletionRequest default values."""
    request = ChatCompletionRequest(messages=[ChatMessage(role="user", content="Hello")])
    assert request.model == "jasque"
    assert request.stream is False
    assert request.temperature is None
    assert request.max_tokens is None
    assert request.stream_options is None


def test_chat_completion_request_with_options():
    """Test ChatCompletionRequest with all options."""
    request = ChatCompletionRequest(
        model="custom-model",
        messages=[ChatMessage(role="user", content="Hello")],
        stream=True,
        temperature=0.7,
        max_tokens=1000,
    )
    assert request.model == "custom-model"
    assert request.stream is True
    assert request.temperature == 0.7
    assert request.max_tokens == 1000


def test_chat_completion_response_structure():
    """Test ChatCompletionResponse structure."""
    from app.features.chat.openai_schemas import (
        ChatCompletionChoice,
        ChatCompletionMessage,
        ChatCompletionUsage,
    )

    response = ChatCompletionResponse(
        id="chatcmpl-123",
        created=1234567890,
        model="jasque",
        choices=[ChatCompletionChoice(message=ChatCompletionMessage(content="Hello!"))],
        usage=ChatCompletionUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )
    assert response.object == "chat.completion"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hello!"
    assert response.choices[0].finish_reason == "stop"
    assert response.usage is not None
    assert response.usage.total_tokens == 15


def test_chat_message_roles():
    """Test all valid message roles."""
    for role in ["system", "user", "assistant"]:
        msg = ChatMessage(role=role, content="Test")  # type: ignore[arg-type]
        assert msg.role == role
