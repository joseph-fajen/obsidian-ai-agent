"""Tests for obsidian_manage_structure tool."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.features.obsidian_manage_structure.obsidian_manage_structure_schemas import (
    BulkStructureItem,
)
from app.features.obsidian_manage_structure.obsidian_manage_structure_tool import (
    register_obsidian_manage_structure_tool,
)
from app.shared.vault import (
    FolderAlreadyExistsError,
    FolderNode,
    FolderNotEmptyError,
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
)
from app.shared.vault.manager import FolderInfo, NoteContent


@pytest.fixture
def deps(tmp_path: Path) -> AgentDependencies:
    return AgentDependencies(request_id="test", vault_path=tmp_path)


@pytest.fixture
def toolset() -> FunctionToolset[AgentDependencies]:
    ts: FunctionToolset[AgentDependencies] = FunctionToolset()
    register_obsidian_manage_structure_tool(ts)
    return ts


@pytest.fixture
def mock_ctx(deps: AgentDependencies):
    ctx = AsyncMock(spec=RunContext)
    ctx.deps = deps
    return ctx


# =============================================================================
# Parameter Validation Tests
# =============================================================================


async def test_create_folder_requires_path(mock_ctx, toolset):
    """create_folder operation requires path parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="create_folder", path="")
    assert result.success is False
    assert "path" in result.message.lower()


async def test_delete_folder_requires_path(mock_ctx, toolset):
    """delete_folder operation requires path parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="delete_folder", path="")
    assert result.success is False
    assert "path" in result.message.lower()


async def test_rename_requires_path(mock_ctx, toolset):
    """rename operation requires path parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="rename", path="", new_path="new")
    assert result.success is False
    assert "path" in result.message.lower()


async def test_rename_requires_new_path(mock_ctx, toolset):
    """rename operation requires new_path parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="rename", path="old", new_path=None)
    assert result.success is False
    assert "new_path" in result.message.lower()


async def test_move_requires_path(mock_ctx, toolset):
    """move operation requires path parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="move", path="", new_path="dest")
    assert result.success is False
    assert "path" in result.message.lower()


async def test_move_requires_new_path(mock_ctx, toolset):
    """move operation requires new_path parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="move", path="source", new_path=None)
    assert result.success is False
    assert "new_path" in result.message.lower()


async def test_bulk_requires_items(mock_ctx, toolset):
    """Bulk mode requires items parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(mock_ctx, operation="move", path="", bulk=True, items=None)
    assert result.success is False
    assert "items" in result.message.lower()


async def test_bulk_only_supports_move_rename(mock_ctx, toolset):
    """Bulk mode only supports move and rename operations."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    result = await tool_fn(
        mock_ctx,
        operation="create_folder",
        path="",
        bulk=True,
        items=[BulkStructureItem(path="a", new_path="b")],
    )
    assert result.success is False
    assert "move" in result.message.lower() or "rename" in result.message.lower()


# =============================================================================
# Operation Tests
# =============================================================================


async def test_create_folder_success(mock_ctx, toolset):
    """create_folder operation creates a new folder."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_folder = FolderInfo(path="projects/new", name="new")

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_folder = AsyncMock(return_value=mock_folder)
        result = await tool_fn(mock_ctx, operation="create_folder", path="projects/new")

    assert result.success is True
    assert result.path == "projects/new"


async def test_rename_folder_success(mock_ctx, toolset):
    """rename operation renames a folder."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_folder = FolderInfo(path="projects/new-name", name="new-name")

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.rename = AsyncMock(return_value=mock_folder)
        result = await tool_fn(
            mock_ctx, operation="rename", path="projects/old", new_path="projects/new-name"
        )

    assert result.success is True
    assert result.new_path == "projects/new-name"


async def test_rename_note_success(mock_ctx, toolset):
    """rename operation renames a note."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_note = NoteContent(
        path="inbox/new.md", title="New", content="Content", tags=[], metadata={}
    )

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.rename = AsyncMock(return_value=mock_note)
        result = await tool_fn(
            mock_ctx, operation="rename", path="inbox/old.md", new_path="inbox/new.md"
        )

    assert result.success is True
    assert result.new_path == "inbox/new.md"


async def test_delete_folder_success(mock_ctx, toolset):
    """delete_folder operation deletes a folder."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.delete_folder = AsyncMock(return_value=None)
        result = await tool_fn(mock_ctx, operation="delete_folder", path="temp")

    assert result.success is True
    assert "deleted" in result.message.lower()


async def test_delete_folder_with_force(mock_ctx, toolset):
    """delete_folder operation passes force parameter."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.delete_folder = AsyncMock(return_value=None)
        result = await tool_fn(mock_ctx, operation="delete_folder", path="old", force=True)

    assert result.success is True
    MockVault.return_value.delete_folder.assert_called_with("old", force=True)


async def test_move_note_success(mock_ctx, toolset):
    """move operation moves a note to new location."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_note = NoteContent(
        path="archive/old.md", title="Old", content="Content", tags=[], metadata={}
    )

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.move = AsyncMock(return_value=mock_note)
        result = await tool_fn(
            mock_ctx, operation="move", path="inbox/old.md", new_path="archive/old.md"
        )

    assert result.success is True
    assert result.new_path == "archive/old.md"


async def test_move_folder_success(mock_ctx, toolset):
    """move operation moves a folder to new location."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_folder = FolderInfo(path="archive/project", name="project")

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.move = AsyncMock(return_value=mock_folder)
        result = await tool_fn(
            mock_ctx, operation="move", path="projects/old", new_path="archive/project"
        )

    assert result.success is True
    assert result.new_path == "archive/project"


async def test_list_structure_success(mock_ctx, toolset):
    """list_structure operation returns folder tree."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_structure = [
        FolderNode(name="projects", path="projects", node_type="folder", children=[]),
        FolderNode(name="note.md", path="note.md", node_type="note", children=None),
    ]

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.list_structure = AsyncMock(return_value=mock_structure)
        result = await tool_fn(mock_ctx, operation="list_structure", path="")

    assert result.success is True
    assert result.structure is not None
    assert len(result.structure) == 2


async def test_list_structure_with_path(mock_ctx, toolset):
    """list_structure operation can be scoped to a folder."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_structure = [
        FolderNode(name="alpha.md", path="projects/alpha.md", node_type="note", children=None),
    ]

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.list_structure = AsyncMock(return_value=mock_structure)
        result = await tool_fn(mock_ctx, operation="list_structure", path="projects")

    assert result.success is True
    MockVault.return_value.list_structure.assert_called_with("projects")


# =============================================================================
# Error Handling Tests
# =============================================================================


async def test_error_handling_folder_not_found(mock_ctx, toolset):
    """FolderNotFoundError is caught and returned as failed result."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.delete_folder = AsyncMock(
            side_effect=FolderNotFoundError("Folder not found: nonexistent")
        )
        result = await tool_fn(mock_ctx, operation="delete_folder", path="nonexistent")

    assert result.success is False
    assert "not found" in result.message.lower()


async def test_error_handling_folder_already_exists(mock_ctx, toolset):
    """FolderAlreadyExistsError is caught for create_folder operation."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.create_folder = AsyncMock(
            side_effect=FolderAlreadyExistsError("Folder already exists")
        )
        result = await tool_fn(mock_ctx, operation="create_folder", path="existing")

    assert result.success is False
    assert "exists" in result.message.lower()


async def test_error_handling_folder_not_empty(mock_ctx, toolset):
    """FolderNotEmptyError is caught for delete_folder operation."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.delete_folder = AsyncMock(
            side_effect=FolderNotEmptyError("Folder not empty")
        )
        result = await tool_fn(mock_ctx, operation="delete_folder", path="non-empty")

    assert result.success is False
    assert "not empty" in result.message.lower()


async def test_error_handling_note_not_found_on_rename(mock_ctx, toolset):
    """NoteNotFoundError is caught for rename operation."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.rename = AsyncMock(side_effect=NoteNotFoundError("Note not found"))
        result = await tool_fn(mock_ctx, operation="rename", path="missing.md", new_path="new.md")

    assert result.success is False


async def test_error_handling_note_already_exists_on_move(mock_ctx, toolset):
    """NoteAlreadyExistsError is caught for move operation."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.move = AsyncMock(
            side_effect=NoteAlreadyExistsError("Destination exists")
        )
        result = await tool_fn(mock_ctx, operation="move", path="source.md", new_path="existing.md")

    assert result.success is False
    assert "exists" in result.message.lower()


# =============================================================================
# Bulk Operation Tests
# =============================================================================


async def test_bulk_move_success(mock_ctx, toolset):
    """Bulk move operation processes multiple items."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_note = NoteContent(path="archive/a.md", title="A", content="Content", tags=[], metadata={})

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.move = AsyncMock(return_value=mock_note)
        result = await tool_fn(
            mock_ctx,
            operation="move",
            path="",
            bulk=True,
            items=[
                BulkStructureItem(path="inbox/a.md", new_path="archive/a.md"),
                BulkStructureItem(path="inbox/b.md", new_path="archive/b.md"),
            ],
        )

    assert result.success is True
    assert result.affected_count == 2


async def test_bulk_rename_success(mock_ctx, toolset):
    """Bulk rename operation processes multiple items."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_folder = FolderInfo(path="projects/new", name="new")

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.rename = AsyncMock(return_value=mock_folder)
        result = await tool_fn(
            mock_ctx,
            operation="rename",
            path="",
            bulk=True,
            items=[
                BulkStructureItem(path="old1", new_path="new1"),
                BulkStructureItem(path="old2", new_path="new2"),
            ],
        )

    assert result.success is True
    assert result.affected_count == 2


async def test_bulk_partial_failure(mock_ctx, toolset):
    """Bulk operation reports partial failures."""
    tool_fn = toolset.tools["obsidian_manage_structure"].function
    mock_folder = FolderInfo(path="new", name="new")

    with patch(
        "app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager"
    ) as MockVault:
        MockVault.return_value.move = AsyncMock(
            side_effect=[mock_folder, NoteNotFoundError("Not found")]
        )
        result = await tool_fn(
            mock_ctx,
            operation="move",
            path="",
            bulk=True,
            items=[
                BulkStructureItem(path="a.md", new_path="archive/a.md"),
                BulkStructureItem(path="b.md", new_path="archive/b.md"),
            ],
        )

    assert result.success is False
    assert result.affected_count == 1
    assert result.errors is not None
    assert len(result.errors) == 1
