"""Base Pydantic AI agent for Jasque."""

import os
from functools import lru_cache

from pydantic_ai import Agent

from app.core.agents.types import AgentDependencies
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Jasque, an AI assistant for Obsidian vault management.

You help users interact with their Obsidian vault through natural language.
You can search notes, create and modify content, manage tasks, and organize folders.

Be concise and helpful. When you don't have access to a tool needed for a task,
explain what you would need to accomplish it.

Current capabilities:
- Conversational responses
- (Tools will be added in future updates)
"""


def create_agent() -> Agent[AgentDependencies, str]:
    """Create a new Pydantic AI agent instance.

    Returns:
        A configured Pydantic AI Agent with AgentDependencies and string output.
    """
    settings = get_settings()

    # Set API key in environment for Pydantic AI to use
    # (pydantic-settings loads from .env but doesn't export to os.environ)
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    model_name = f"anthropic:{settings.anthropic_model}"
    logger.info("agent.lifecycle.creating", model=settings.anthropic_model)

    agent: Agent[AgentDependencies, str] = Agent(
        model_name,
        deps_type=AgentDependencies,
        output_type=str,
        instructions=SYSTEM_PROMPT,
    )

    logger.info("agent.lifecycle.created", model=settings.anthropic_model)
    return agent


@lru_cache(maxsize=1)
def get_agent() -> Agent[AgentDependencies, str]:
    """Get the cached singleton agent instance.

    The @lru_cache decorator ensures the agent is only created once
    and reused across the application lifecycle.

    Returns:
        The singleton agent instance.
    """
    return create_agent()
