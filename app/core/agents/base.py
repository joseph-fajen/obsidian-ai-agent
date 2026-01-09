"""Base Pydantic AI agent for Jasque."""

import os
from functools import lru_cache

from pydantic_ai import Agent

from app.core.agents.types import AgentDependencies
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Jasque, an AI assistant for Obsidian vault management.

You help users interact with their Obsidian vault using natural language.

## Available Tools

You have access to the following tool:

### obsidian_query_vault
Search and query the Obsidian vault. Operations:
- search_text: Full-text search across notes (requires query param)
- find_by_tag: Find notes with specific tags (requires tags param)
- list_notes: List notes in vault or folder
- list_folders: Get folder structure
- get_backlinks: Find notes linking to a specific note (requires path param)
- get_tags: Get all unique tags in vault
- list_tasks: Find task checkboxes

Use response_format="concise" (default) for brief results, "detailed" for full content.

## Guidelines

- Always use the appropriate tool to answer questions about the vault
- When searching, start with concise format and only use detailed if needed
- If a search returns no results, suggest alternative queries
- Be helpful and conversational while being efficient with tool calls
- For tasks that require reading or modifying notes, inform the user those
  capabilities will be added soon (obsidian_manage_notes, obsidian_manage_structure)
"""


def create_agent() -> Agent[AgentDependencies, str]:
    """Create a new Pydantic AI agent instance with tools.

    Returns:
        A configured Pydantic AI Agent with AgentDependencies and string output.
    """
    settings = get_settings()

    # Set API key in environment for Pydantic AI to use
    # (pydantic-settings loads from .env but doesn't export to os.environ)
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    model_name = f"anthropic:{settings.anthropic_model}"
    logger.info("agent.lifecycle.creating", model=settings.anthropic_model)

    # Create toolset with registered tools
    # Import here to avoid circular import
    from app.core.agents.tool_registry import create_obsidian_toolset

    toolset = create_obsidian_toolset()

    agent: Agent[AgentDependencies, str] = Agent(
        model_name,
        deps_type=AgentDependencies,
        output_type=str,
        instructions=SYSTEM_PROMPT,
        toolsets=[toolset],
    )

    logger.info(
        "agent.lifecycle.created",
        model=settings.anthropic_model,
        tools=["obsidian_query_vault"],
    )
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
