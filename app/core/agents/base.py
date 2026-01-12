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

### obsidian_query_vault
Search and query the Obsidian vault. Operations:
- search_text: Full-text search across notes (requires query)
- find_by_tag: Find notes with specific tags (requires tags)
- list_notes: List notes in vault or folder
- list_folders: Get folder structure
- get_backlinks: Find notes linking to a specific note
- get_tags: Get all unique tags in vault
- list_tasks: Find task checkboxes

Use response_format="concise" (default) for brief results, "detailed" for full content.

### obsidian_manage_notes
Manage notes - create, read, update, delete, and complete tasks. Operations:
- read: Get full contents of a note
- create: Create a new note (fails if exists)
- update: Replace note content (preserves frontmatter)
- append: Add content to end of note
- delete: Remove a note from vault
- complete_task: Mark a task checkbox as done

Supports bulk operations with bulk=True and items parameter.

### obsidian_manage_structure
Manage vault folder structure. Operations:
- create_folder: Create new folder (creates parents as needed)
- rename: Rename a file or folder (requires new_path)
- delete_folder: Delete a folder (use force=True for non-empty)
- move: Move file/folder to new location (requires new_path)
- list_structure: Get folder tree hierarchy

Supports bulk operations for move/rename with bulk=True and items parameter.

## Guidelines

- Use obsidian_query_vault to FIND notes, then obsidian_manage_notes to MODIFY them
- Use obsidian_manage_structure to organize folders and move/rename files
- Start with concise format, use detailed only if needed
- If search returns no results, suggest alternatives
- Be helpful and conversational while being efficient with tool calls

## Important: File Sync

Changes you make (especially delete) modify files directly. If a note is open in Obsidian,
the UI may not update immediately. If the user reports still seeing a deleted note, suggest
refreshing the file explorer or closing/reopening the note tab.
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
        tools=["obsidian_query_vault", "obsidian_manage_notes", "obsidian_manage_structure"],
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
