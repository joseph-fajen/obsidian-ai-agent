"""obsidian_query_vault feature - vault search and discovery tool."""

from app.features.obsidian_query_vault.obsidian_query_vault_schemas import (
    QueryResult,
    QueryResultItem,
)
from app.features.obsidian_query_vault.obsidian_query_vault_tool import (
    register_obsidian_query_vault_tool,
)

__all__ = [
    "QueryResult",
    "QueryResultItem",
    "register_obsidian_query_vault_tool",
]
