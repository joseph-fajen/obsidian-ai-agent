"""Streaming utilities for OpenAI-compatible SSE responses.

This module provides:
- Message history conversion (OpenAI → Pydantic AI format)
- SSE streaming generator using agent.iter()
- Helper functions for content normalization
"""

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    UserPromptPart,
)

from app.core.agents.types import AgentDependencies
from app.core.logging import get_logger
from app.features.chat.openai_schemas import (
    ChatCompletionChunk,
    ChatCompletionUsage,
    ChatMessage,
    ChunkChoice,
    DeltaContent,
    normalize_content,
)

logger = get_logger(__name__)


def extract_last_user_message(messages: list[ChatMessage]) -> str:
    """Get the last user message for the agent prompt.

    Args:
        messages: List of chat messages from the request.

    Returns:
        The content of the last user message, or empty string if none found.
    """
    for msg in reversed(messages):
        if msg.role == "user":
            # Handle both string and list content
            if isinstance(msg.content, str):
                return msg.content
            return normalize_content(msg.content)
    return ""


def convert_to_pydantic_history(messages: list[ChatMessage]) -> list[ModelMessage]:
    """Convert OpenAI messages to Pydantic AI message history.

    Note: System messages are ignored - the agent has its own SYSTEM_PROMPT
    defined in app/core/agents/base.py.

    Args:
        messages: List of OpenAI-format chat messages.

    Returns:
        List of Pydantic AI ModelMessage objects (ModelRequest/ModelResponse).
    """
    history: list[ModelMessage] = []

    for msg in messages:
        # Normalize content (handle string or array format)
        if isinstance(msg.content, str):
            content = msg.content
        else:
            content = normalize_content(msg.content)

        if msg.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif msg.role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
        # System messages are ignored - agent has its own instructions

    return history


async def generate_sse_stream(
    agent: Agent[AgentDependencies, str],
    user_message: str,
    message_history: list[ModelMessage],
    deps: AgentDependencies,
    model_name: str,
    include_usage: bool = False,
) -> AsyncIterator[str]:
    """Generate OpenAI-compatible SSE chunks from Pydantic AI agent.

    Uses agent.iter() with node.stream() to extract TextPartDelta events.
    Yields SSE-formatted strings: 'data: {json}\\n\\n'

    Args:
        agent: The Pydantic AI agent instance.
        user_message: The current user message to process.
        message_history: Previous conversation history.
        deps: Agent dependencies (request_id, etc.).
        model_name: Model name to include in chunks.
        include_usage: Whether to include token usage in final chunk.

    Yields:
        SSE-formatted strings for each chunk.
    """
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    logger.info(
        "agent.llm.streaming_started",
        chat_id=chat_id,
        model=model_name,
        history_length=len(message_history),
    )

    # First chunk: role announcement
    first_chunk = ChatCompletionChunk(
        id=chat_id,
        created=created,
        model=model_name,
        choices=[ChunkChoice(delta=DeltaContent(role="assistant"))],
    )
    yield f"data: {first_chunk.model_dump_json()}\n\n"

    total_content = ""
    usage_data: dict[str, Any] | None = None

    try:
        async with agent.iter(user_message, message_history=message_history, deps=deps) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as stream:
                        async for event in stream:
                            content: str | None = None

                            # Handle PartStartEvent - contains initial text content!
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart) and event.part.content:
                                    content = event.part.content
                            # Handle PartDeltaEvent - contains subsequent text deltas
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    content = event.delta.content_delta

                            # Yield content if we extracted any
                            if content:
                                total_content += content
                                content_chunk = ChatCompletionChunk(
                                    id=chat_id,
                                    created=created,
                                    model=model_name,
                                    choices=[ChunkChoice(delta=DeltaContent(content=content))],
                                )
                                yield f"data: {content_chunk.model_dump_json()}\n\n"

            # Get usage after run completes
            if include_usage:
                run_usage = run.usage()
                usage_data = {
                    "prompt_tokens": run_usage.input_tokens or 0,
                    "completion_tokens": run_usage.output_tokens or 0,
                    "total_tokens": run_usage.total_tokens or 0,
                }

        logger.info(
            "agent.llm.streaming_completed",
            chat_id=chat_id,
            response_length=len(total_content),
        )

    except Exception as e:
        error_str = str(e)

        # Detect history parse errors (corrupted JSON in tool call arguments)
        # These manifest as ValueError with "EOF while parsing" or "Expecting" messages
        is_history_error = isinstance(e, ValueError) and (
            "EOF while parsing" in error_str or "Expecting" in error_str
        )

        if is_history_error:
            logger.error(
                "agent.llm.history_parse_failed",
                chat_id=chat_id,
                error=error_str,
                exc_info=True,
            )
            user_message = (
                "Conversation history contains corrupted data. "
                "Please start a new conversation in Obsidian Copilot."
            )
        else:
            logger.error(
                "agent.llm.streaming_failed",
                chat_id=chat_id,
                error=error_str,
                error_type=type(e).__name__,
                exc_info=True,
            )
            user_message = f"Error: {error_str}"

        # Send error as final content chunk
        error_chunk = ChatCompletionChunk(
            id=chat_id,
            created=created,
            model=model_name,
            choices=[
                ChunkChoice(
                    delta=DeltaContent(content=f"\n\n[{user_message}]"),
                    finish_reason="stop",
                )
            ],
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Final chunk: finish_reason
    final_chunk = ChatCompletionChunk(
        id=chat_id,
        created=created,
        model=model_name,
        choices=[ChunkChoice(delta=DeltaContent(), finish_reason="stop")],
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"

    # Optional: usage chunk (if stream_options.include_usage)
    if include_usage and usage_data:
        usage_chunk = ChatCompletionChunk(
            id=chat_id,
            created=created,
            model=model_name,
            choices=[],
            usage=ChatCompletionUsage(**usage_data),
        )
        yield f"data: {usage_chunk.model_dump_json()}\n\n"

    # Termination signal
    yield "data: [DONE]\n\n"
