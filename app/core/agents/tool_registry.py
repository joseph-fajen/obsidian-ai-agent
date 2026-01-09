"""Tool registry - creates toolsets for the Jasque agent."""

from pydantic_ai import FunctionToolset

from app.core.agents.types import AgentDependencies
from app.features.obsidian_query_vault.obsidian_query_vault_tool import (
    register_obsidian_query_vault_tool,
)


def create_obsidian_toolset() -> FunctionToolset[AgentDependencies]:
    """Create a FunctionToolset with all Obsidian vault tools.

    Returns:
        FunctionToolset configured with obsidian_query_vault tool.
        Future tools (obsidian_manage_notes, obsidian_manage_structure)
        will be registered here.
    """
    toolset: FunctionToolset[AgentDependencies] = FunctionToolset()

    # Register query/search tool
    register_obsidian_query_vault_tool(toolset)

    # Future: register_obsidian_manage_notes_tool(toolset)
    # Future: register_obsidian_manage_structure_tool(toolset)

    return toolset
