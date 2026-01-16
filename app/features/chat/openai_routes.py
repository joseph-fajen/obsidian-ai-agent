"""OpenAI-compatible chat completions endpoint.

This module provides the /chat/completions endpoint for compatibility
with Obsidian Copilot and other OpenAI-compatible clients.

NOTE: This router is mounted at /v1 (not /api/v1) because the OpenAI SDK
automatically appends /chat/completions to the base URL.
"""

import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.agents import AgentDependencies, get_agent
from app.core.config import get_settings
from app.core.logging import get_logger, get_request_id
from app.features.chat.openai_schemas import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
)
from app.features.chat.preferences import VaultPreferences, format_preferences_for_agent
from app.features.chat.streaming import (
    convert_to_pydantic_history,
    extract_last_user_message,
    generate_sse_stream,
)
from app.shared.vault import PreferencesParseError, VaultManager

logger = get_logger(__name__)
router = APIRouter(tags=["openai"])


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    """OpenAI-compatible chat completions endpoint.

    Supports both streaming (stream=true) and non-streaming requests.
    Compatible with Obsidian Copilot plugin.

    The agent's system prompt is defined in app/core/agents/base.py.
    System messages in the request are ignored to avoid duplication.

    Args:
        request: OpenAI-compatible chat completion request.

    Returns:
        ChatCompletionResponse for non-streaming, StreamingResponse for streaming.

    Raises:
        HTTPException: 400 if no user message found, 500 if agent fails.
    """
    agent = get_agent()
    request_id = get_request_id()
    settings = get_settings()
    deps = AgentDependencies(
        request_id=request_id,
        vault_path=Path(settings.obsidian_vault_path),
    )

    # Load user preferences from vault
    vault_manager = VaultManager(deps.vault_path)
    preferences: VaultPreferences | None = None
    try:
        preferences = await vault_manager.load_preferences()
    except PreferencesParseError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Extract the last user message for the agent
    user_message = extract_last_user_message(request.messages)
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message found in request",
        )

    # Prepend preferences context if available
    if preferences:
        prefs_context = format_preferences_for_agent(preferences)
        user_message = f"{prefs_context}\n\n---\n\n{user_message}"

    # Convert history (excluding last user message which becomes the prompt)
    # Find the index of the last user message
    last_user_idx = -1
    for i, msg in enumerate(request.messages):
        if msg.role == "user":
            last_user_idx = i

    # History is everything before the last user message
    history_messages = request.messages[:last_user_idx] if last_user_idx > 0 else []
    message_history = convert_to_pydantic_history(history_messages)

    model_name = request.model or "jasque"

    logger.info(
        "agent.llm.call_started",
        prompt_length=len(user_message),
        history_length=len(message_history),
        stream=request.stream,
        request_id=request_id,
    )

    if request.stream:
        # Streaming response
        include_usage = request.stream_options.include_usage if request.stream_options else False
        return StreamingResponse(
            generate_sse_stream(
                agent=agent,
                user_message=user_message,
                message_history=message_history,
                deps=deps,
                model_name=model_name,
                include_usage=include_usage,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    # Non-streaming response
    try:
        result = await agent.run(user_message, message_history=message_history, deps=deps)

        usage = None
        if result.usage():
            usage_data = result.usage()
            usage = ChatCompletionUsage(
                prompt_tokens=usage_data.input_tokens or 0,
                completion_tokens=usage_data.output_tokens or 0,
                total_tokens=usage_data.total_tokens or 0,
            )

        logger.info(
            "agent.llm.call_completed",
            response_length=len(result.output),
            tokens_prompt=usage.prompt_tokens if usage else None,
            tokens_completion=usage.completion_tokens if usage else None,
            request_id=request_id,
        )

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            created=int(time.time()),
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    message=ChatCompletionMessage(content=result.output),
                )
            ],
            usage=usage,
        )

    except Exception as e:
        logger.error(
            "agent.llm.call_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e!s}",
        ) from e
