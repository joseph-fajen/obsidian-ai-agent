"""obsidian_manage_structure tool implementation."""

from __future__ import annotations

from typing import Literal

from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.core.logging import get_logger
from app.features.obsidian_manage_structure.obsidian_manage_structure_schemas import (
    BulkErrorItem,
    BulkStructureItem,
    StructureOperationResult,
)
from app.shared.vault import FolderNode, VaultError, VaultManager

logger = get_logger(__name__)


def register_obsidian_manage_structure_tool(
    toolset: FunctionToolset[AgentDependencies],
) -> None:
    """Register the obsidian_manage_structure tool with the given toolset."""

    @toolset.tool
    async def obsidian_manage_structure(
        ctx: RunContext[AgentDependencies],
        operation: Literal["create_folder", "rename", "delete_folder", "move", "list_structure"],
        path: str = "",
        new_path: str | None = None,
        force: bool = False,
        bulk: bool = False,
        items: list[BulkStructureItem] | None = None,
    ) -> StructureOperationResult:
        """Manage vault folder structure - create, rename, move, delete folders, and view structure.

        Use this when you need to:
        - Create new folders in the vault (including nested paths)
        - Rename files or folders to new names
        - Move files or folders to new locations
        - Delete folders (empty folders, or non-empty with force=True)
        - View the vault's folder/file hierarchy

        Do NOT use this for:
        - Reading note content (use obsidian_manage_notes with operation='read')
        - Creating or updating notes (use obsidian_manage_notes)
        - Deleting individual notes (use obsidian_manage_notes with operation='delete')
        - Searching for notes (use obsidian_query_vault)
        - Finding notes by tag (use obsidian_query_vault with operation='find_by_tag')

        Args:
            operation: "create_folder", "rename", "delete_folder", "move", or "list_structure"
            path: Target path for the operation (folder or file path)
            new_path: Destination path for rename/move operations (required for those)
            force: For delete_folder only - set True to delete non-empty folders
            bulk: Enable bulk mode for move/rename (uses items instead of path/new_path)
            items: List of BulkStructureItem for bulk operations

        Returns:
            StructureOperationResult with success, message, and operation-specific data

        Performance Notes:
            - Single operations: 10-50ms
            - list_structure: O(n) where n = total files/folders in scope
            - Bulk: O(n) for n items, max recommended 50 items

        Examples:
            # Create folder
            obsidian_manage_structure(operation="create_folder", path="projects/new-project")

            # Rename file or folder
            obsidian_manage_structure(operation="rename", path="inbox/old.md",
                new_path="inbox/new-name.md")

            # Move file to archive
            obsidian_manage_structure(operation="move", path="inbox/done.md",
                new_path="archive/2025/done.md")

            # Delete empty folder
            obsidian_manage_structure(operation="delete_folder", path="temp")

            # Delete non-empty folder (destructive)
            obsidian_manage_structure(operation="delete_folder", path="old-archive", force=True)

            # View vault structure
            obsidian_manage_structure(operation="list_structure", path="projects")
        """
        vault = VaultManager(ctx.deps.vault_path)

        logger.info(
            "vault.tool.manage_structure_started",
            operation=operation,
            path=path,
            bulk=bulk,
        )

        if bulk:
            if operation not in ("move", "rename"):
                return StructureOperationResult(
                    success=False,
                    operation=operation,
                    path="",
                    message=f"Bulk mode only supports move and rename operations, not {operation}.",
                )
            if not items:
                return StructureOperationResult(
                    success=False,
                    operation=operation,
                    path="",
                    message="Bulk mode requires items parameter.",
                )
            return await _handle_bulk_operation(vault, operation, items)

        try:
            if operation == "create_folder":
                if not path:
                    return StructureOperationResult(
                        success=False,
                        operation=operation,
                        path="",
                        message="Path is required for create_folder operation.",
                    )
                result = await vault.create_folder(path)
                return StructureOperationResult(
                    success=True,
                    operation=operation,
                    path=result.path,
                    message=f"Successfully created folder: {result.path}",
                )

            elif operation == "rename":
                if not path:
                    return StructureOperationResult(
                        success=False,
                        operation=operation,
                        path="",
                        message="Path is required for rename operation.",
                    )
                if not new_path:
                    return StructureOperationResult(
                        success=False,
                        operation=operation,
                        path=path,
                        message="new_path is required for rename operation.",
                    )
                rename_result = await vault.rename(path, new_path)
                return StructureOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    new_path=rename_result.path,
                    message=f"Successfully renamed {path} to {rename_result.path}",
                )

            elif operation == "delete_folder":
                if not path:
                    return StructureOperationResult(
                        success=False,
                        operation=operation,
                        path="",
                        message="Path is required for delete_folder operation.",
                    )
                await vault.delete_folder(path, force=force)
                return StructureOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Successfully deleted folder: {path}",
                )

            elif operation == "move":
                if not path:
                    return StructureOperationResult(
                        success=False,
                        operation=operation,
                        path="",
                        message="Path is required for move operation.",
                    )
                if not new_path:
                    return StructureOperationResult(
                        success=False,
                        operation=operation,
                        path=path,
                        message="new_path is required for move operation.",
                    )
                move_result = await vault.move(path, new_path)
                return StructureOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    new_path=move_result.path,
                    message=f"Successfully moved {path} to {move_result.path}",
                )

            elif operation == "list_structure":
                structure = await vault.list_structure(path if path else None)
                return StructureOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Found {_count_nodes(structure)} items in structure",
                    structure=structure,
                )

            else:
                return StructureOperationResult(
                    success=False,
                    operation=operation,
                    path=path,
                    message=f"Unknown operation: {operation}",
                )

        except VaultError as e:
            logger.error(
                "vault.tool.manage_structure_failed",
                operation=operation,
                path=path,
                error=str(e),
                exc_info=True,
            )
            return StructureOperationResult(
                success=False,
                operation=operation,
                path=path,
                message=str(e),
            )


def _count_nodes(nodes: list[FolderNode]) -> int:
    """Count total nodes in a structure tree recursively."""
    count = 0
    for node in nodes:
        count += 1
        if node.children:
            count += _count_nodes(node.children)
    return count


async def _handle_bulk_operation(
    vault: VaultManager,
    operation: str,
    items: list[BulkStructureItem],
) -> StructureOperationResult:
    """Handle bulk move/rename operations with best-effort processing."""
    affected = 0
    errors: list[BulkErrorItem] = []

    for item in items:
        try:
            if operation == "move":
                await vault.move(item.path, item.new_path)
            elif operation == "rename":
                await vault.rename(item.path, item.new_path)
            affected += 1
        except VaultError as e:
            errors.append(BulkErrorItem(path=item.path, error=str(e)))

    success = len(errors) == 0
    message = (
        f"Bulk {operation} completed: {affected} succeeded"
        if success
        else f"Bulk {operation} partially completed: {affected} succeeded, {len(errors)} failed"
    )

    return StructureOperationResult(
        success=success,
        operation=operation,
        path="",
        message=message,
        affected_count=affected,
        errors=errors if errors else None,
    )
