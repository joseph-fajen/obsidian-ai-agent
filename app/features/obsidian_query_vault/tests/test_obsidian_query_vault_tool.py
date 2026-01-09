"""Tests for obsidian_query_vault tool."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.features.obsidian_query_vault import (
    register_obsidian_query_vault_tool,
)
from app.shared.vault import (
    FolderNotFoundError,
    NoteNotFoundError,
)
from app.shared.vault.manager import (
    BacklinkResult,
    FolderInfo,
    NoteInfo,
    SearchResult,
    TaskInfo,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault for tests."""
    return tmp_path


@pytest.fixture
def deps(vault_path: Path) -> AgentDependencies:
    """Create test dependencies."""
    return AgentDependencies(request_id="test-request", vault_path=vault_path)


@pytest.fixture
def toolset() -> FunctionToolset[AgentDependencies]:
    """Create a toolset with the tool registered."""
    ts: FunctionToolset[AgentDependencies] = FunctionToolset()
    register_obsidian_query_vault_tool(ts)
    return ts


@pytest.fixture
def mock_ctx(deps: AgentDependencies):
    """Create a mock RunContext."""
    ctx = AsyncMock(spec=RunContext)
    ctx.deps = deps
    return ctx


# =============================================================================
# Parameter Validation Tests
# =============================================================================


async def test_search_text_requires_query(mock_ctx, toolset):
    """search_text requires query parameter."""
    # Get the tool function from the toolset
    tool_fn = toolset.tools["obsidian_query_vault"].function

    result = await tool_fn(
        mock_ctx,
        operation="search_text",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )

    assert result.success is False
    assert "Query parameter is required" in result.message


async def test_find_by_tag_requires_tags(mock_ctx, toolset):
    """find_by_tag requires tags parameter."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    result = await tool_fn(
        mock_ctx,
        operation="find_by_tag",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )

    assert result.success is False
    assert "Tags parameter is required" in result.message


async def test_get_backlinks_requires_path(mock_ctx, toolset):
    """get_backlinks requires path parameter."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    result = await tool_fn(
        mock_ctx,
        operation="get_backlinks",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )

    assert result.success is False
    assert "Path parameter is required" in result.message


# =============================================================================
# Operation Tests with Mocked VaultManager
# =============================================================================


async def test_search_text_returns_results(mock_ctx, toolset):
    """search_text returns search results."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        SearchResult(
            path="notes/test.md",
            title="Test Note",
            snippet="This is a test snippet",
            line_number=5,
        )
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.search_text.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="search_text",
            query="test",
            path=None,
            tags=None,
            include_completed=False,
            response_format="detailed",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "search_text"
        assert len(result.results) == 1
        assert result.results[0].path == "notes/test.md"
        assert result.results[0].snippet == "This is a test snippet"


async def test_find_by_tag_returns_results(mock_ctx, toolset):
    """find_by_tag returns matching notes."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        NoteInfo(
            path="projects/alpha.md",
            title="Alpha Project",
            tags=["project", "active"],
            modified=None,
        )
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.find_by_tag.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="find_by_tag",
            query=None,
            path=None,
            tags=["project"],
            include_completed=False,
            response_format="detailed",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "find_by_tag"
        assert len(result.results) == 1
        assert result.results[0].path == "projects/alpha.md"


async def test_list_notes_returns_notes(mock_ctx, toolset):
    """list_notes returns all notes."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        NoteInfo(path="note1.md", title="Note 1", tags=[], modified=None),
        NoteInfo(path="note2.md", title="Note 2", tags=["tag"], modified=None),
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.list_notes.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="list_notes",
            query=None,
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "list_notes"
        assert len(result.results) == 2


async def test_list_folders_returns_folders(mock_ctx, toolset):
    """list_folders returns folder structure."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        FolderInfo(path="projects", name="projects"),
        FolderInfo(path="daily", name="daily"),
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.list_folders.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="list_folders",
            query=None,
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "list_folders"
        assert len(result.results) == 2
        assert result.results[0].title == "projects"


async def test_get_backlinks_returns_links(mock_ctx, toolset):
    """get_backlinks returns linking notes."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        BacklinkResult(
            path="other.md",
            title="Other Note",
            context="Links to [[target]]",
        )
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.get_backlinks.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="get_backlinks",
            query=None,
            path="target.md",
            tags=None,
            include_completed=False,
            response_format="detailed",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "get_backlinks"
        assert len(result.results) == 1
        assert result.results[0].snippet == "Links to [[target]]"


async def test_get_tags_returns_all_tags(mock_ctx, toolset):
    """get_tags returns unique tags."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = ["project", "active", "archived"]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.get_tags.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="get_tags",
            query=None,
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "get_tags"
        assert len(result.results) == 3
        assert result.results[0].title == "project"


async def test_list_tasks_returns_tasks(mock_ctx, toolset):
    """list_tasks returns task items."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        TaskInfo(
            path="todo.md",
            task_text="Complete feature",
            completed=False,
            line_number=10,
        )
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.list_tasks.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="list_tasks",
            query=None,
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is True
        assert result.operation == "list_tasks"
        assert len(result.results) == 1
        assert result.results[0].task_text == "Complete feature"
        assert result.results[0].task_completed is False


# =============================================================================
# Error Handling Tests
# =============================================================================


async def test_vault_error_returns_failure(mock_ctx, toolset):
    """VaultError returns success=False."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.list_notes.side_effect = FolderNotFoundError("Not found")
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="list_notes",
            query=None,
            path="nonexistent",
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is False
        assert "Not found" in result.message


async def test_note_not_found_error(mock_ctx, toolset):
    """NoteNotFoundError returns helpful message."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.get_backlinks.side_effect = NoteNotFoundError(
            "Note not found: missing.md"
        )
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="get_backlinks",
            query=None,
            path="missing.md",
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is False
        assert "missing.md" in result.message


# =============================================================================
# Response Format Tests
# =============================================================================


async def test_concise_format_excludes_details(mock_ctx, toolset):
    """Concise format excludes snippets and extra metadata."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    mock_results = [
        SearchResult(
            path="notes/test.md",
            title="Test Note",
            snippet="This is a test snippet",
            line_number=5,
        )
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.search_text.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="search_text",
            query="test",
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is True
        assert result.results[0].snippet is None  # Excluded in concise


# =============================================================================
# Limit and Truncation Tests
# =============================================================================


async def test_results_truncated_at_limit(mock_ctx, toolset):
    """Results are truncated and marked as truncated."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    # Create 5 mock results
    mock_results = [
        NoteInfo(path=f"note{i}.md", title=f"Note {i}", tags=[], modified=None) for i in range(5)
    ]

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.list_notes.return_value = mock_results
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="list_notes",
            query=None,
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=3,
        )

        assert result.success is True
        assert len(result.results) == 3  # Limited
        assert result.truncated is True


# =============================================================================
# Empty Results Tests
# =============================================================================


async def test_empty_results_message(mock_ctx, toolset):
    """Empty results include helpful message."""
    tool_fn = toolset.tools["obsidian_query_vault"].function

    with patch(
        "app.features.obsidian_query_vault.obsidian_query_vault_tool.VaultManager"
    ) as MockVault:
        mock_vault_instance = AsyncMock()
        mock_vault_instance.search_text.return_value = []
        MockVault.return_value = mock_vault_instance

        result = await tool_fn(
            mock_ctx,
            operation="search_text",
            query="xyznonexistent",
            path=None,
            tags=None,
            include_completed=False,
            response_format="concise",
            limit=50,
        )

        assert result.success is True
        assert result.total_count == 0
        assert "No results found" in result.message
