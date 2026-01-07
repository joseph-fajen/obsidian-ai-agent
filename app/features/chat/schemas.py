"""Schemas for chat feature endpoints."""

from pydantic import BaseModel, Field

from app.core.agents.types import TokenUsage


class ChatRequest(BaseModel):
    """Request schema for the test chat endpoint."""

    message: str = Field(..., min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    """Response schema for the test chat endpoint."""

    response: str
    model: str
    usage: TokenUsage | None = None
