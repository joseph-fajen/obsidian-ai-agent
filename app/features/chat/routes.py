"""Chat feature routes for testing the Pydantic AI agent."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.core.agents import AgentDependencies, get_agent
from app.core.agents.types import TokenUsage
from app.core.config import get_settings
from app.core.logging import get_logger, get_request_id
from app.features.chat.schemas import ChatRequest, ChatResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/test", response_model=ChatResponse)
async def test_chat(request: ChatRequest) -> ChatResponse:
    """Test endpoint for the Pydantic AI agent.

    This endpoint allows testing the agent's conversational capabilities
    without any vault tools attached.

    Args:
        request: The chat request containing the user message.

    Returns:
        ChatResponse with the agent's response and usage information.

    Raises:
        HTTPException: 500 if agent execution fails.
    """
    agent = get_agent()
    request_id = get_request_id()
    settings = get_settings()
    deps = AgentDependencies(
        request_id=request_id,
        vault_path=Path(settings.obsidian_vault_path),
    )

    logger.info(
        "agent.llm.call_started",
        prompt_length=len(request.message),
        request_id=request_id,
    )

    try:
        result = await agent.run(request.message, deps=deps)

        usage = None
        if result.usage():
            usage_data = result.usage()
            usage = TokenUsage(
                prompt_tokens=usage_data.input_tokens or 0,
                completion_tokens=usage_data.output_tokens or 0,
                total_tokens=usage_data.total_tokens or 0,
            )

        # Get model name from response
        model_name = "unknown"
        if result.response and result.response.model_name:
            model_name = result.response.model_name

        logger.info(
            "agent.llm.call_completed",
            response_length=len(result.output),
            tokens_prompt=usage.prompt_tokens if usage else None,
            tokens_completion=usage.completion_tokens if usage else None,
            request_id=request_id,
        )

        return ChatResponse(
            response=result.output,
            model=model_name,
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
