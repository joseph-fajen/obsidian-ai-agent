"""Conversation history validation and truncation utilities.

This module provides defensive layers for handling conversation history:
- Validation of tool call JSON arguments at the API boundary
- Truncation of long conversation histories to reduce costs and error probability
"""

import json

from app.core.logging import get_logger
from app.features.chat.openai_schemas import ChatMessage
from app.shared.vault.exceptions import ConversationHistoryError

logger = get_logger(__name__)


def validate_tool_call_arguments(messages: list[ChatMessage]) -> None:
    """Validate that all tool call arguments contain valid JSON.

    Checks each assistant message with tool_calls for valid JSON in the
    arguments field. Raises ConversationHistoryError on the first invalid entry.

    Args:
        messages: List of chat messages to validate.

    Raises:
        ConversationHistoryError: If any tool call has malformed JSON arguments.
    """
    for index, message in enumerate(messages):
        if message.tool_calls is None:
            continue

        for tool_call in message.tool_calls:
            try:
                json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                logger.warning(
                    "agent.history.validation_failed",
                    message_index=index,
                    tool_call_id=tool_call.id,
                    function_name=tool_call.function.name,
                    error=str(e),
                )
                raise ConversationHistoryError(
                    f"Conversation history contains invalid data (malformed tool call at "
                    f"message {index}). Please start a new conversation in Obsidian Copilot."
                ) from e


def truncate_conversation_history(
    messages: list[ChatMessage],
    max_messages: int,
) -> list[ChatMessage]:
    """Truncate conversation history to a maximum number of messages.

    Keeps the most recent messages, dropping oldest entries first.
    This helps reduce token costs and the probability of encountering
    corrupted entries in older history.

    Args:
        messages: List of chat messages to potentially truncate.
        max_messages: Maximum number of messages to keep. If 0, returns empty list.

    Returns:
        The truncated list of messages (most recent).
    """
    if max_messages <= 0:
        return []

    if len(messages) <= max_messages:
        return messages

    truncated_count = len(messages) - max_messages
    logger.info(
        "agent.history.truncated",
        original_count=len(messages),
        truncated_count=truncated_count,
        remaining_count=max_messages,
    )

    return messages[-max_messages:]
