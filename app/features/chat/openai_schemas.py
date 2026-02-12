"""OpenAI-compatible schemas for chat completions API.

These schemas match the OpenAI Chat Completions API format to ensure
compatibility with Obsidian Copilot and other OpenAI-compatible clients.
"""

from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, Field

# =============================================================================
# Content Parts (for multi-modal support)
# =============================================================================


class TextContentPart(BaseModel):
    """Text content part in a message."""

    type: Literal["text"]
    text: str


class ImageUrlContent(BaseModel):
    """Image URL content details."""

    url: str
    detail: str | None = None


class ImageContentPart(BaseModel):
    """Image content part in a message."""

    type: Literal["image_url"]
    image_url: str | ImageUrlContent


ContentPart = Annotated[TextContentPart | ImageContentPart, Field(discriminator="type")]


# =============================================================================
# Tool Call Models (for conversation history validation)
# =============================================================================


class ToolCallFunction(BaseModel):
    """Function details in a tool call."""

    name: str
    arguments: str  # JSON string - this is what we validate


class ToolCall(BaseModel):
    """A tool call from the assistant."""

    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


# =============================================================================
# Request Models
# =============================================================================


class ChatMessage(BaseModel):
    """A message in the chat conversation.

    Content can be either a simple string or a list of content parts
    (for multi-modal support like text + images).
    """

    role: Literal["system", "user", "assistant"]
    content: str | list[ContentPart]
    tool_calls: list[ToolCall] | None = None  # Only present on assistant messages


class StreamOptions(BaseModel):
    """Options for streaming responses."""

    include_usage: bool = False


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = "jasque"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    stream_options: StreamOptions | None = None


# =============================================================================
# Non-Streaming Response Models
# =============================================================================


class ChatCompletionMessage(BaseModel):
    """Message in a chat completion response."""

    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    """A choice in the chat completion response."""

    index: int = 0
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length", "tool_calls"] = "stop"


class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response (non-streaming)."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage | None = None


# =============================================================================
# Streaming Response Models (SSE Chunks)
# =============================================================================


class DeltaContent(BaseModel):
    """Incremental content in a streaming chunk."""

    role: str | None = None
    content: str | None = None


class ChunkChoice(BaseModel):
    """A choice in a streaming chunk."""

    index: int = 0
    delta: DeltaContent
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    """OpenAI-compatible streaming chunk."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]
    usage: ChatCompletionUsage | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def normalize_content(content: str | list[Any]) -> str:
    """Extract plain text from OpenAI message content.

    Handles both string content and structured array format.
    Mirrors obsidian-copilot's extractTextFromChunk() logic.

    Args:
        content: Either a string or list of content parts (dicts or Pydantic models).

    Returns:
        The extracted text content as a single string.
    """
    if isinstance(content, str):
        return content
    # content is a list - could be dicts or Pydantic models
    result_parts: list[str] = []
    for item in content:
        # Handle both dict and Pydantic model formats
        if isinstance(item, dict):
            item_dict = cast(dict[str, Any], item)
            if item_dict.get("type") == "text":
                text_value = item_dict.get("text", "")
                if isinstance(text_value, str):
                    result_parts.append(text_value)
        elif hasattr(item, "type") and item.type == "text":
            # It's a Pydantic model with type="text" (TextContentPart)
            text_attr = getattr(item, "text", "")
            if isinstance(text_attr, str):
                result_parts.append(text_attr)
    return "".join(result_parts)
