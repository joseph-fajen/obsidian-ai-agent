"""Tests for obsidian_manage_notes tool."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.features.obsidian_manage_notes.obsidian_manage_notes_schemas import BulkNoteItem
from app.features.obsidian_manage_notes.obsidian_manage_notes_tool import (
    register_obsidian_manage_notes_tool,
)
from app.shared.vault import NoteAlreadyExistsError, NoteNotFoundError, TaskNotFoundError
from app.shared.vault.manager import NoteContent, TaskInfo


@pytest.fixture
def deps(tmp_path: Path) -> AgentDependencies:
    return AgentDependencies(request_id="test", vault_path=tmp_path)


@pytest.fixture
def toolset() -> FunctionToolset[AgentDependencies]:
    ts: FunctionToolset[AgentDependencies] = FunctionToolset()
    register_obsidian_manage_notes_tool(ts)
    return ts


@pytest.fixture
def mock_ctx(deps: AgentDependencies):
    ctx = AsyncMock(spec=RunContext)
    ctx.deps = deps
    return ctx


# =============================================================================
# Parameter Validation Tests
# =============================================================================


async def test_create_requires_content(mock_ctx, toolset):
    """Create operation requires content parameter."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    result = await tool_fn(mock_ctx, operation="create", path="test.md", content=None)
    assert result.success is False
    assert "content" in result.message.lower()


async def test_complete_task_requires_identifier(mock_ctx, toolset):
    """complete_task operation requires task_identifier parameter."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    result = await tool_fn(
        mock_ctx, operation="complete_task", path="test.md", task_identifier=None
    )
    assert result.success is False


async def test_bulk_requires_items(mock_ctx, toolset):
    """Bulk mode requires items parameter."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    result = await tool_fn(mock_ctx, operation="create", path="", bulk=True, items=None)
    assert result.success is False


# =============================================================================
# Operation Tests
# =============================================================================


async def test_read_success(mock_ctx, toolset):
    """Read operation returns note content."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Content", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.read_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(mock_ctx, operation="read", path="test.md")

    assert result.success is True
    assert result.content == "# Content"


async def test_create_success(mock_ctx, toolset):
    """Create operation creates a new note."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(mock_ctx, operation="create", path="test.md", content="# Test")

    assert result.success is True


async def test_update_success(mock_ctx, toolset):
    """Update operation updates note content."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# New", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.update_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(mock_ctx, operation="update", path="test.md", content="# New")

    assert result.success is True


async def test_append_success(mock_ctx, toolset):
    """Append operation adds content to note."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(
        path="test.md", title="Test", content="# Old\n\nAppended", tags=[], metadata={}
    )

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.append_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(mock_ctx, operation="append", path="test.md", content="\n\nAppended")

    assert result.success is True


async def test_delete_success(mock_ctx, toolset):
    """Delete operation removes note."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.delete_note = AsyncMock(return_value=None)
        result = await tool_fn(mock_ctx, operation="delete", path="test.md")

    assert result.success is True


async def test_complete_task_success(mock_ctx, toolset):
    """complete_task operation marks task as done."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_task = TaskInfo(path="test.md", task_text="Buy groceries", completed=True, line_number=3)

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.complete_task = AsyncMock(return_value=mock_task)
        result = await tool_fn(
            mock_ctx,
            operation="complete_task",
            path="test.md",
            task_identifier="Buy groceries",
        )

    assert result.success is True
    assert "Buy groceries" in result.message


# =============================================================================
# Error Handling Tests
# =============================================================================


async def test_error_handling_note_not_found(mock_ctx, toolset):
    """Vault errors are caught and returned as failed result."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.read_note = AsyncMock(side_effect=NoteNotFoundError("Not found"))
        result = await tool_fn(mock_ctx, operation="read", path="missing.md")

    assert result.success is False
    assert "not found" in result.message.lower()


async def test_error_handling_note_exists(mock_ctx, toolset):
    """NoteAlreadyExistsError is caught for create operation."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_note = AsyncMock(
            side_effect=NoteAlreadyExistsError("Already exists")
        )
        result = await tool_fn(mock_ctx, operation="create", path="existing.md", content="# New")

    assert result.success is False
    assert "exists" in result.message.lower()


async def test_error_handling_task_not_found(mock_ctx, toolset):
    """TaskNotFoundError is caught for complete_task operation."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.complete_task = AsyncMock(
            side_effect=TaskNotFoundError("Task not found")
        )
        result = await tool_fn(
            mock_ctx,
            operation="complete_task",
            path="test.md",
            task_identifier="nonexistent",
        )

    assert result.success is False


# =============================================================================
# Bulk Operation Tests
# =============================================================================


async def test_bulk_create_success(mock_ctx, toolset):
    """Bulk create operation processes multiple items."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(
            mock_ctx,
            operation="create",
            path="",
            bulk=True,
            items=[
                BulkNoteItem(path="a.md", content="# A"),
                BulkNoteItem(path="b.md", content="# B"),
            ],
        )

    assert result.success is True
    assert result.affected_count == 2


async def test_bulk_partial_failure(mock_ctx, toolset):
    """Bulk operation reports partial failures."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_note = AsyncMock(
            side_effect=[mock_note, NoteAlreadyExistsError("Exists")]
        )
        result = await tool_fn(
            mock_ctx,
            operation="create",
            path="",
            bulk=True,
            items=[
                BulkNoteItem(path="a.md", content="# A"),
                BulkNoteItem(path="b.md", content="# B"),
            ],
        )

    assert result.success is False
    assert result.affected_count == 1
    assert len(result.errors) == 1


async def test_bulk_missing_content(mock_ctx, toolset):
    """Bulk create with missing content adds to errors."""
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(
            mock_ctx,
            operation="create",
            path="",
            bulk=True,
            items=[
                BulkNoteItem(path="a.md", content="# A"),
                BulkNoteItem(path="b.md", content=None),  # Missing content
            ],
        )

    assert result.success is False
    assert result.affected_count == 1
    assert len(result.errors) == 1
    assert "Content required" in result.errors[0].error
