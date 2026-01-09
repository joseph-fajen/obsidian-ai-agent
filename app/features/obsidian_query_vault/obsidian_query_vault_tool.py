"""obsidian_query_vault tool implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.core.logging import get_logger
from app.features.obsidian_query_vault.obsidian_query_vault_schemas import (
    QueryResult,
    QueryResultItem,
)
from app.shared.vault import VaultError, VaultManager

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def register_obsidian_query_vault_tool(
    toolset: FunctionToolset[AgentDependencies],
) -> None:
    """Register the obsidian_query_vault tool with the given toolset."""

    @toolset.tool
    async def obsidian_query_vault(
        ctx: RunContext[AgentDependencies],
        operation: Literal[
            "search_text",
            "find_by_tag",
            "list_notes",
            "list_folders",
            "get_backlinks",
            "get_tags",
            "list_tasks",
        ],
        query: str | None = None,
        path: str | None = None,
        tags: list[str] | None = None,
        include_completed: bool = False,
        response_format: Literal["detailed", "concise"] = "concise",
        limit: int = 50,
    ) -> QueryResult:
        """Search and query the Obsidian vault for notes, tags, tasks, and relationships.

        Use this when you need to:
        - Find notes by content (search_text) - for locating relevant information
        - Find notes by tag (find_by_tag) - when user mentions tags or categories
        - Browse vault structure (list_notes, list_folders) - for navigation and overview
        - Discover note connections (get_backlinks) - for exploring relationships
        - Get all tags (get_tags) - for understanding vault organization
        - Find tasks (list_tasks) - for task management queries

        Do NOT use this for:
        - Reading full note content - use obsidian_manage_notes with operation='read' instead
        - Creating or modifying notes - use obsidian_manage_notes instead
        - Managing folders - use obsidian_manage_structure instead
        - Completing tasks - use obsidian_manage_notes with operation='complete_task'

        Args:
            operation: The query operation to perform:
                - "search_text": Full-text search across notes (requires query param)
                - "find_by_tag": Find notes with specific tags (requires tags param)
                - "list_notes": List all notes, optionally in a folder (path optional)
                - "list_folders": Get folder structure (path optional)
                - "get_backlinks": Find notes linking to a note (requires path param)
                - "get_tags": Get all unique tags in vault (no params needed)
                - "list_tasks": Find tasks/checkboxes (path optional)
            query: Search string for search_text operation. Case-insensitive.
                Example: "meeting notes", "project plan", "bug fix"
            path: Folder or note path to scope the operation.
                Examples: "projects/", "daily/2025-01-15.md", "inbox"
                Omit to search entire vault.
            tags: List of tags for find_by_tag operation. Matches notes with ANY tag.
                Examples: ["project", "urgent"], ["#work"], ["status/active"]
            include_completed: For list_tasks, whether to include completed tasks.
                Default False - only shows incomplete tasks.
            response_format: Control response detail level:
                - "concise" (default): Paths, titles, minimal metadata (~50 tokens/item)
                - "detailed": Include snippets, full tags, timestamps (~150 tokens/item)
                Always start with concise; use detailed only if more context needed.
            limit: Maximum results to return. Default 50. Use smaller values for
                faster responses. Use larger (up to 100) for comprehensive searches.

        Returns:
            QueryResult containing:
            - success: True if operation completed, False on error
            - operation: The operation that was performed
            - total_count: Number of results found
            - results: List of QueryResultItem with matching items
            - truncated: True if results were limited
            - message: Error details or helpful hints

        Performance Notes:
            - Concise format: ~50 tokens per result (recommended)
            - Detailed format: ~150 tokens per result (use sparingly)
            - list_notes/list_folders: Fast, O(n) vault scan
            - search_text: Slower, reads file contents
            - get_backlinks: Reads all files to find links
            - Always prefer smaller limits for faster responses

        Examples:
            # Search for meeting notes
            obsidian_query_vault(
                operation="search_text",
                query="weekly standup",
                response_format="concise"
            )

            # Find all project-tagged notes
            obsidian_query_vault(
                operation="find_by_tag",
                tags=["project", "active"],
                limit=20
            )

            # List notes in a specific folder
            obsidian_query_vault(
                operation="list_notes",
                path="projects/",
                response_format="detailed"
            )

            # Find incomplete tasks
            obsidian_query_vault(
                operation="list_tasks",
                include_completed=False,
                limit=10
            )
        """
        vault = VaultManager(ctx.deps.vault_path)

        logger.info(
            "vault.tool.query_started",
            operation=operation,
            path=path,
            query=query,
            tags=tags,
        )

        try:
            items: list[QueryResultItem] = []

            if operation == "search_text":
                if not query:
                    return QueryResult(
                        success=False,
                        operation=operation,
                        total_count=0,
                        results=[],
                        message="Query parameter is required for search_text operation. "
                        "Example: query='meeting notes'",
                    )

                search_results = await vault.search_text(query, path=path, limit=limit)
                items = [
                    QueryResultItem(
                        path=r.path,
                        title=r.title,
                        snippet=r.snippet if response_format == "detailed" else None,
                        line_number=r.line_number,
                    )
                    for r in search_results
                ]

            elif operation == "find_by_tag":
                if not tags:
                    return QueryResult(
                        success=False,
                        operation=operation,
                        total_count=0,
                        results=[],
                        message="Tags parameter is required for find_by_tag operation. "
                        "Example: tags=['project', 'urgent']",
                    )

                tag_results = await vault.find_by_tag(tags, path=path, limit=limit)
                items = [
                    QueryResultItem(
                        path=r.path,
                        title=r.title,
                        tags=r.tags if response_format == "detailed" else None,
                        modified=r.modified if response_format == "detailed" else None,
                    )
                    for r in tag_results
                ]

            elif operation == "list_notes":
                note_results = await vault.list_notes(folder=path)
                limited_notes = note_results[:limit]
                items = [
                    QueryResultItem(
                        path=r.path,
                        title=r.title,
                        tags=r.tags if response_format == "detailed" else None,
                        modified=r.modified if response_format == "detailed" else None,
                    )
                    for r in limited_notes
                ]

            elif operation == "list_folders":
                folder_results = await vault.list_folders(path=path)
                limited_folders = folder_results[:limit]
                items = [
                    QueryResultItem(
                        path=r.path,
                        title=r.name,
                    )
                    for r in limited_folders
                ]

            elif operation == "get_backlinks":
                if not path:
                    return QueryResult(
                        success=False,
                        operation=operation,
                        total_count=0,
                        results=[],
                        message="Path parameter is required for get_backlinks operation. "
                        "Example: path='concepts/zettelkasten.md'",
                    )

                backlink_results = await vault.get_backlinks(path, limit=limit)
                items = [
                    QueryResultItem(
                        path=r.path,
                        title=r.title,
                        snippet=r.context if response_format == "detailed" else None,
                    )
                    for r in backlink_results
                ]

            elif operation == "get_tags":
                all_tags = await vault.get_tags()
                # Tags are strings, create items for each
                items = [
                    QueryResultItem(
                        path="",  # Tags don't have paths
                        title=tag,
                    )
                    for tag in all_tags[:limit]
                ]

            elif operation == "list_tasks":
                task_results = await vault.list_tasks(
                    path=path,
                    include_completed=include_completed,
                    limit=limit,
                )
                items = [
                    QueryResultItem(
                        path=r.path,
                        task_text=r.task_text,
                        task_completed=r.completed,
                        line_number=r.line_number,
                    )
                    for r in task_results
                ]

            else:
                return QueryResult(
                    success=False,
                    operation=operation,
                    total_count=0,
                    results=[],
                    message=f"Unknown operation: {operation}. "
                    "Valid operations: search_text, find_by_tag, list_notes, "
                    "list_folders, get_backlinks, get_tags, list_tasks",
                )

            truncated = len(items) >= limit

            logger.info(
                "vault.tool.query_completed",
                operation=operation,
                count=len(items),
                truncated=truncated,
            )

            message = None
            if len(items) == 0:
                message = "No results found. Try broadening your search or checking the path."

            return QueryResult(
                success=True,
                operation=operation,
                total_count=len(items),
                results=items,
                truncated=truncated,
                message=message,
            )

        except VaultError as e:
            logger.error(
                "vault.tool.query_failed",
                operation=operation,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return QueryResult(
                success=False,
                operation=operation,
                total_count=0,
                results=[],
                message=str(e),
            )
