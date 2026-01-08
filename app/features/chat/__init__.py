"""Chat feature - OpenAI-compatible API endpoint."""

from app.features.chat.openai_routes import router as openai_router
from app.features.chat.routes import router

__all__ = ["openai_router", "router"]
