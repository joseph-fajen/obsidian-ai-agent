"""Pydantic AI agent infrastructure for Jasque."""

from typing import TYPE_CHECKING

from app.core.agents.base import create_agent, get_agent
from app.core.agents.types import AgentDependencies

if TYPE_CHECKING:
    from pydantic_ai import FunctionToolset

__all__ = ["AgentDependencies", "create_agent", "get_agent"]


def create_obsidian_toolset() -> "FunctionToolset[AgentDependencies]":
    """Lazy import to avoid circular imports.

    Returns:
        FunctionToolset configured with obsidian tools.
    """
    from app.core.agents.tool_registry import (
        create_obsidian_toolset as _create_obsidian_toolset,
    )

    return _create_obsidian_toolset()
