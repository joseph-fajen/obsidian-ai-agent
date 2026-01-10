"""obsidian_manage_notes tool implementation."""

from __future__ import annotations

from typing import Literal

from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.core.logging import get_logger
from app.features.obsidian_manage_notes.obsidian_manage_notes_schemas import (
    BulkErrorItem,
    BulkNoteItem,
    NoteOperationResult,
)
from app.shared.vault import VaultError, VaultManager

logger = get_logger(__name__)


def register_obsidian_manage_notes_tool(
    toolset: FunctionToolset[AgentDependencies],
) -> None:
    """Register the obsidian_manage_notes tool with the given toolset."""

    @toolset.tool
    async def obsidian_manage_notes(
        ctx: RunContext[AgentDependencies],
        operation: Literal["read", "create", "update", "append", "delete", "complete_task"],
        path: str,
        content: str | None = None,
        folder: str | None = None,
        task_identifier: str | None = None,
        bulk: bool = False,
        items: list[BulkNoteItem] | None = None,
    ) -> NoteOperationResult:
        """Manage notes in the Obsidian vault - create, read, update, delete, and complete tasks.

        Use this when you need to:
        - Read the full content of a specific note you know the path to
        - Create new notes with content (meeting notes, daily notes, ideas)
        - Update or replace existing note content
        - Append content to the end of an existing note (journals, logs)
        - Delete notes that are no longer needed
        - Mark task checkboxes as complete (- [ ] becomes - [x])

        Do NOT use this for:
        - Finding notes (use obsidian_query_vault with search_text or find_by_tag)
        - Listing notes or folders (use obsidian_query_vault with list_notes/list_folders)
        - Finding tasks (use obsidian_query_vault with list_tasks first)
        - Managing folders (use obsidian_manage_structure instead)

        Args:
            operation: "read", "create", "update", "append", "delete", or "complete_task"
            path: Note path relative to vault root (e.g., "projects/roadmap.md")
            content: Note content for create/update/append operations
            folder: Target folder for create (prepended to path)
            task_identifier: Line number or task text for complete_task
            bulk: Enable bulk mode (uses items instead of path/content)
            items: List of BulkNoteItem for bulk operations

        Returns:
            NoteOperationResult with success, message, and operation-specific data

        Performance Notes:
            - Single operations: 10-150ms
            - Bulk: O(n), max recommended 50 items

        Examples:
            # Read note
            obsidian_manage_notes(operation="read", path="projects/roadmap.md")

            # Create note in folder
            obsidian_manage_notes(operation="create", path="2025-01-15.md",
                folder="daily", content="# Daily Note")

            # Complete task by text
            obsidian_manage_notes(operation="complete_task", path="tasks.md",
                task_identifier="Buy groceries")
        """
        vault = VaultManager(ctx.deps.vault_path)

        logger.info(
            "vault.tool.manage_notes_started",
            operation=operation,
            path=path,
            bulk=bulk,
        )

        if bulk:
            if not items:
                return NoteOperationResult(
                    success=False,
                    operation=operation,
                    path="",
                    message="Bulk mode requires items parameter.",
                )
            return await _handle_bulk_operation(vault, operation, items)

        try:
            if operation == "read":
                note = await vault.read_note(path)
                return NoteOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Successfully read note: {path}",
                    content=note.content,
                )

            elif operation == "create":
                if not content:
                    return NoteOperationResult(
                        success=False,
                        operation=operation,
                        path=path,
                        message="Content is required for create operation.",
                    )
                note = await vault.create_note(path, content, folder)
                return NoteOperationResult(
                    success=True,
                    operation=operation,
                    path=note.path,
                    message=f"Successfully created note: {note.path}",
                )

            elif operation == "update":
                if not content:
                    return NoteOperationResult(
                        success=False,
                        operation=operation,
                        path=path,
                        message="Content is required for update operation.",
                    )
                await vault.update_note(path, content)
                return NoteOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Successfully updated note: {path}",
                )

            elif operation == "append":
                if not content:
                    return NoteOperationResult(
                        success=False,
                        operation=operation,
                        path=path,
                        message="Content is required for append operation.",
                    )
                await vault.append_note(path, content)
                return NoteOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Successfully appended to note: {path}",
                )

            elif operation == "delete":
                await vault.delete_note(path)
                return NoteOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Successfully deleted note: {path}",
                )

            elif operation == "complete_task":
                if not task_identifier:
                    return NoteOperationResult(
                        success=False,
                        operation=operation,
                        path=path,
                        message="Task identifier is required for complete_task operation.",
                    )
                task = await vault.complete_task(path, task_identifier)
                return NoteOperationResult(
                    success=True,
                    operation=operation,
                    path=path,
                    message=f"Successfully completed task: '{task.task_text}'",
                )

            else:
                return NoteOperationResult(
                    success=False,
                    operation=operation,
                    path=path,
                    message=f"Unknown operation: {operation}",
                )

        except VaultError as e:
            logger.error(
                "vault.tool.manage_notes_failed",
                operation=operation,
                path=path,
                error=str(e),
                exc_info=True,
            )
            return NoteOperationResult(
                success=False,
                operation=operation,
                path=path,
                message=str(e),
            )


async def _handle_bulk_operation(
    vault: VaultManager,
    operation: str,
    items: list[BulkNoteItem],
) -> NoteOperationResult:
    """Handle bulk note operations with best-effort processing."""
    affected = 0
    errors: list[BulkErrorItem] = []

    for item in items:
        try:
            if operation == "read":
                await vault.read_note(item.path)
            elif operation == "create":
                if not item.content:
                    errors.append(BulkErrorItem(path=item.path, error="Content required"))
                    continue
                await vault.create_note(item.path, item.content, item.folder)
            elif operation == "update":
                if not item.content:
                    errors.append(BulkErrorItem(path=item.path, error="Content required"))
                    continue
                await vault.update_note(item.path, item.content)
            elif operation == "append":
                if not item.content:
                    errors.append(BulkErrorItem(path=item.path, error="Content required"))
                    continue
                await vault.append_note(item.path, item.content)
            elif operation == "delete":
                await vault.delete_note(item.path)
            elif operation == "complete_task":
                if not item.task_identifier:
                    errors.append(BulkErrorItem(path=item.path, error="Task identifier required"))
                    continue
                await vault.complete_task(item.path, item.task_identifier)
            affected += 1
        except VaultError as e:
            errors.append(BulkErrorItem(path=item.path, error=str(e)))

    success = len(errors) == 0
    message = (
        f"Bulk {operation} completed: {affected} succeeded"
        if success
        else f"Bulk {operation} partially completed: {affected} succeeded, {len(errors)} failed"
    )

    return NoteOperationResult(
        success=success,
        operation=operation,
        path="",
        message=message,
        affected_count=affected,
        errors=errors if errors else None,
    )
