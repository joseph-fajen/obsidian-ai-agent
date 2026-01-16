"""Integration tests for multi-tool workflows.

These tests verify that the three Obsidian tools work correctly together
in realistic user scenarios, using a real temporary vault.
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.features.obsidian_manage_notes.obsidian_manage_notes_tool import (
    register_obsidian_manage_notes_tool,
)
from app.features.obsidian_manage_structure.obsidian_manage_structure_tool import (
    register_obsidian_manage_structure_tool,
)
from app.features.obsidian_query_vault.obsidian_query_vault_tool import (
    register_obsidian_query_vault_tool,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault directory."""
    return tmp_path


@pytest.fixture
def deps(vault_path: Path) -> AgentDependencies:
    """Create test dependencies with vault path."""
    return AgentDependencies(request_id="integration-test", vault_path=vault_path)


@pytest.fixture
def mock_ctx(deps: AgentDependencies) -> AsyncMock:
    """Create a mock RunContext with real dependencies."""
    ctx = AsyncMock(spec=RunContext)
    ctx.deps = deps
    return ctx


@pytest.fixture
def query_tool(mock_ctx: AsyncMock) -> AsyncMock:
    """Get the obsidian_query_vault tool function."""
    ts: FunctionToolset[AgentDependencies] = FunctionToolset()
    register_obsidian_query_vault_tool(ts)
    return ts.tools["obsidian_query_vault"].function


@pytest.fixture
def notes_tool(mock_ctx: AsyncMock) -> AsyncMock:
    """Get the obsidian_manage_notes tool function."""
    ts: FunctionToolset[AgentDependencies] = FunctionToolset()
    register_obsidian_manage_notes_tool(ts)
    return ts.tools["obsidian_manage_notes"].function


@pytest.fixture
def structure_tool(mock_ctx: AsyncMock) -> AsyncMock:
    """Get the obsidian_manage_structure tool function."""
    ts: FunctionToolset[AgentDependencies] = FunctionToolset()
    register_obsidian_manage_structure_tool(ts)
    return ts.tools["obsidian_manage_structure"].function


# =============================================================================
# Workflow 1: Note Lifecycle (Create -> Search -> Update -> Verify)
# =============================================================================


@pytest.mark.asyncio
async def test_note_lifecycle_create_search_update_verify(
    mock_ctx: AsyncMock,
    query_tool: AsyncMock,
    notes_tool: AsyncMock,
) -> None:
    """Test complete note lifecycle: create, search, update, read back."""
    # Step 1: Create a note
    create_result = await notes_tool(
        mock_ctx,
        operation="create",
        path="projects/my-project.md",
        content="# My Project\n\nThis is a test project about Python.",
    )
    assert create_result.success is True, f"Create failed: {create_result.message}"

    # Step 2: Search for the note by content
    search_result = await query_tool(
        mock_ctx,
        operation="search_text",
        query="Python",
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert search_result.success is True, f"Search failed: {search_result.message}"
    assert search_result.total_count >= 1, "Should find at least one matching note"
    paths = [item.path for item in search_result.results]
    assert "projects/my-project.md" in paths, "Created note should appear in search"

    # Step 3: Update the note
    update_result = await notes_tool(
        mock_ctx,
        operation="update",
        path="projects/my-project.md",
        content="# My Project\n\nThis is an updated project about Python and FastAPI.",
    )
    assert update_result.success is True, f"Update failed: {update_result.message}"

    # Step 4: Read back and verify the update
    read_result = await notes_tool(
        mock_ctx,
        operation="read",
        path="projects/my-project.md",
    )
    assert read_result.success is True, f"Read failed: {read_result.message}"
    assert "FastAPI" in read_result.content, "Updated content should include FastAPI"
    assert "updated project" in read_result.content, "Content should reflect update"


@pytest.mark.asyncio
async def test_note_lifecycle_create_append_read(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
) -> None:
    """Test appending to a note preserves original content."""
    # Step 1: Create a note
    await notes_tool(
        mock_ctx,
        operation="create",
        path="journal/daily.md",
        content="# Daily Log\n\n## Morning\nHad coffee.",
    )

    # Step 2: Append to the note
    append_result = await notes_tool(
        mock_ctx,
        operation="append",
        path="journal/daily.md",
        content="\n## Afternoon\nWorked on integration tests.",
    )
    assert append_result.success is True

    # Step 3: Read back and verify both sections exist
    read_result = await notes_tool(
        mock_ctx,
        operation="read",
        path="journal/daily.md",
    )
    assert "Morning" in read_result.content, "Original content should be preserved"
    assert "Had coffee" in read_result.content
    assert "Afternoon" in read_result.content, "Appended content should exist"
    assert "integration tests" in read_result.content


# =============================================================================
# Workflow 2: Folder Organization (Create folder -> Move note -> List structure)
# =============================================================================


@pytest.mark.asyncio
async def test_folder_organization_workflow(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    structure_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test folder organization: create note, create folder, move note, verify."""
    # Step 1: Create a note at root level
    create_result = await notes_tool(
        mock_ctx,
        operation="create",
        path="loose-note.md",
        content="# A Loose Note\n\nThis note needs to be organized.",
    )
    assert create_result.success is True

    # Step 2: Create an archive folder
    folder_result = await structure_tool(
        mock_ctx,
        operation="create_folder",
        path="archive/2026",
    )
    assert folder_result.success is True, f"Create folder failed: {folder_result.message}"

    # Step 3: Move the note into the archive folder
    move_result = await structure_tool(
        mock_ctx,
        operation="move",
        path="loose-note.md",
        new_path="archive/2026/loose-note.md",
    )
    assert move_result.success is True, f"Move failed: {move_result.message}"

    # Step 4: Verify the note is no longer at root
    root_notes = await query_tool(
        mock_ctx,
        operation="list_notes",
        query=None,
        path="",
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    root_paths = [item.path for item in root_notes.results]
    assert "loose-note.md" not in root_paths, "Note should no longer be at root"

    # Step 5: Verify the note exists in the new location
    archive_notes = await query_tool(
        mock_ctx,
        operation="list_notes",
        query=None,
        path="archive/2026",
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    archive_paths = [item.path for item in archive_notes.results]
    assert "archive/2026/loose-note.md" in archive_paths, "Note should be in archive folder"

    # Step 6: Verify folder structure
    structure_result = await structure_tool(
        mock_ctx,
        operation="list_structure",
        path="",
    )
    assert structure_result.success is True
    # The structure should contain the archive folder


@pytest.mark.asyncio
async def test_rename_note_and_verify(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    structure_tool: AsyncMock,
) -> None:
    """Test renaming a note and verifying content is preserved."""
    # Step 1: Create a note with typo in name
    await notes_tool(
        mock_ctx,
        operation="create",
        path="projcts/readme.md",  # typo: projcts
        content="# Project README\n\nImportant documentation.",
    )

    # Step 2: Create correct folder
    await structure_tool(
        mock_ctx,
        operation="create_folder",
        path="projects",
    )

    # Step 3: Rename (move) to correct location
    rename_result = await structure_tool(
        mock_ctx,
        operation="move",
        path="projcts/readme.md",
        new_path="projects/readme.md",
    )
    assert rename_result.success is True

    # Step 4: Read from new location and verify content
    read_result = await notes_tool(
        mock_ctx,
        operation="read",
        path="projects/readme.md",
    )
    assert read_result.success is True
    assert "Important documentation" in read_result.content


# =============================================================================
# Workflow 3: Task Management (Create task -> List tasks -> Complete -> Verify)
# =============================================================================


@pytest.mark.asyncio
async def test_task_management_workflow(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test task management: create tasks, list them, complete one, verify."""
    # Step 1: Create a note with tasks
    create_result = await notes_tool(
        mock_ctx,
        operation="create",
        path="todos/sprint-1.md",
        content="""# Sprint 1 Tasks

- [ ] Write integration tests
- [ ] Fix failing unit tests
- [ ] Update documentation
- [x] Set up CI pipeline
""",
    )
    assert create_result.success is True

    # Step 2: List incomplete tasks
    list_result = await query_tool(
        mock_ctx,
        operation="list_tasks",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert list_result.success is True
    assert list_result.total_count == 3, f"Should have 3 incomplete tasks, got {list_result.total_count}"

    # Verify specific tasks
    task_texts = [item.task_text for item in list_result.results]
    assert "Write integration tests" in task_texts
    assert "Fix failing unit tests" in task_texts
    assert "Update documentation" in task_texts
    assert "Set up CI pipeline" not in task_texts  # Already complete

    # Step 3: Complete a task by text
    complete_result = await notes_tool(
        mock_ctx,
        operation="complete_task",
        path="todos/sprint-1.md",
        task_identifier="Write integration tests",
    )
    assert complete_result.success is True, f"Complete failed: {complete_result.message}"

    # Step 4: Verify task is now complete
    list_after = await query_tool(
        mock_ctx,
        operation="list_tasks",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert list_after.total_count == 2, "Should now have 2 incomplete tasks"
    remaining_texts = [item.task_text for item in list_after.results]
    assert "Write integration tests" not in remaining_texts, "Completed task should not appear"

    # Step 5: Verify we can see all tasks including completed
    list_all = await query_tool(
        mock_ctx,
        operation="list_tasks",
        query=None,
        path=None,
        tags=None,
        include_completed=True,
        response_format="concise",
        limit=50,
    )
    assert list_all.total_count == 4, "Should have 4 total tasks (including completed)"


@pytest.mark.asyncio
async def test_complete_task_by_line_number(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test completing a task by line number."""
    # Step 1: Create a note with tasks
    await notes_tool(
        mock_ctx,
        operation="create",
        path="tasks.md",
        content="# Tasks\n\n- [ ] First task\n- [ ] Second task\n- [ ] Third task\n",
    )

    # Step 2: List tasks to get line numbers (path=None searches whole vault)
    list_result = await query_tool(
        mock_ctx,
        operation="list_tasks",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="detailed",  # Get line numbers
        limit=50,
    )
    assert list_result.total_count == 3

    # Find the line number for "Second task"
    second_task = next(item for item in list_result.results if "Second" in item.task_text)
    line_number = second_task.line_number
    assert line_number is not None

    # Step 3: Complete by line number
    complete_result = await notes_tool(
        mock_ctx,
        operation="complete_task",
        path="tasks.md",
        task_identifier=str(line_number),
    )
    assert complete_result.success is True

    # Step 4: Verify only 2 tasks remain incomplete
    list_after = await query_tool(
        mock_ctx,
        operation="list_tasks",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert list_after.total_count == 2
    remaining = [item.task_text for item in list_after.results]
    assert "Second task" not in remaining


# =============================================================================
# Workflow 4: Tag-based Organization
# =============================================================================


@pytest.mark.asyncio
async def test_tag_based_search_workflow(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test finding notes by tags across the vault."""
    # Step 1: Create notes with different tags
    await notes_tool(
        mock_ctx,
        operation="create",
        path="work/project-a.md",
        content="# Project A\n#work #priority-high\n\nUrgent project.",
    )
    await notes_tool(
        mock_ctx,
        operation="create",
        path="work/project-b.md",
        content="# Project B\n#work #priority-low\n\nBacklog project.",
    )
    await notes_tool(
        mock_ctx,
        operation="create",
        path="personal/hobby.md",
        content="# My Hobby\n#personal\n\nFun stuff.",
    )

    # Step 2: Get all tags in vault
    tags_result = await query_tool(
        mock_ctx,
        operation="get_tags",
        query=None,
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert tags_result.success is True
    tag_names = [item.title for item in tags_result.results]
    assert "work" in tag_names
    assert "personal" in tag_names
    assert "priority-high" in tag_names

    # Step 3: Find all work-related notes
    work_notes = await query_tool(
        mock_ctx,
        operation="find_by_tag",
        query=None,
        path=None,
        tags=["work"],
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert work_notes.success is True
    assert work_notes.total_count == 2, "Should find 2 work notes"
    work_paths = [item.path for item in work_notes.results]
    assert "work/project-a.md" in work_paths
    assert "work/project-b.md" in work_paths
    assert "personal/hobby.md" not in work_paths

    # Step 4: Find high priority notes
    priority_notes = await query_tool(
        mock_ctx,
        operation="find_by_tag",
        query=None,
        path=None,
        tags=["priority-high"],
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert priority_notes.total_count == 1
    assert priority_notes.results[0].path == "work/project-a.md"


# =============================================================================
# Workflow 5: Backlinks Discovery
# =============================================================================


@pytest.mark.asyncio
async def test_backlinks_discovery_workflow(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test discovering backlinks between notes."""
    # Step 1: Create an index note
    await notes_tool(
        mock_ctx,
        operation="create",
        path="index.md",
        content="# Index\n\nThis is the main entry point.",
    )

    # Step 2: Create notes that link to the index
    await notes_tool(
        mock_ctx,
        operation="create",
        path="notes/topic-a.md",
        content="# Topic A\n\nSee the [[index]] for more info.",
    )
    await notes_tool(
        mock_ctx,
        operation="create",
        path="notes/topic-b.md",
        content="# Topic B\n\nRefer to [[index]] and [[notes/topic-a]].",
    )
    await notes_tool(
        mock_ctx,
        operation="create",
        path="notes/standalone.md",
        content="# Standalone\n\nNo links here.",
    )

    # Step 3: Get backlinks to index.md
    backlinks = await query_tool(
        mock_ctx,
        operation="get_backlinks",
        query=None,
        path="index.md",
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert backlinks.success is True
    assert backlinks.total_count == 2, f"Index should have 2 backlinks, got {backlinks.total_count}"
    linking_paths = [item.path for item in backlinks.results]
    assert "notes/topic-a.md" in linking_paths
    assert "notes/topic-b.md" in linking_paths
    assert "notes/standalone.md" not in linking_paths


# =============================================================================
# Workflow 6: Delete Operations
# =============================================================================


@pytest.mark.asyncio
async def test_delete_note_workflow(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test deleting a note and verifying it's gone."""
    # Step 1: Create a note
    await notes_tool(
        mock_ctx,
        operation="create",
        path="temp/to-delete.md",
        content="# Temporary\n\nThis will be deleted.",
    )

    # Step 2: Verify it exists
    search_before = await query_tool(
        mock_ctx,
        operation="search_text",
        query="Temporary",
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert search_before.total_count >= 1

    # Step 3: Delete the note
    delete_result = await notes_tool(
        mock_ctx,
        operation="delete",
        path="temp/to-delete.md",
    )
    assert delete_result.success is True

    # Step 4: Verify it's gone
    search_after = await query_tool(
        mock_ctx,
        operation="search_text",
        query="Temporary",
        path=None,
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    assert search_after.total_count == 0, "Deleted note should not appear in search"


@pytest.mark.asyncio
async def test_delete_folder_workflow(
    mock_ctx: AsyncMock,
    notes_tool: AsyncMock,
    structure_tool: AsyncMock,
    query_tool: AsyncMock,
) -> None:
    """Test deleting a folder with contents."""
    # Step 1: Create folder structure with notes
    await notes_tool(
        mock_ctx,
        operation="create",
        path="old-project/readme.md",
        content="# Old Project\n\nArchived.",
    )
    await notes_tool(
        mock_ctx,
        operation="create",
        path="old-project/notes.md",
        content="# Notes\n\nOld notes.",
    )

    # Step 2: Try to delete without force (should fail)
    delete_no_force = await structure_tool(
        mock_ctx,
        operation="delete_folder",
        path="old-project",
    )
    assert delete_no_force.success is False, "Should fail without force flag"
    assert "not empty" in delete_no_force.message.lower()

    # Step 3: Delete with force
    delete_force = await structure_tool(
        mock_ctx,
        operation="delete_folder",
        path="old-project",
        force=True,
    )
    assert delete_force.success is True

    # Step 4: Verify folder and contents are gone
    list_result = await query_tool(
        mock_ctx,
        operation="list_notes",
        query=None,
        path="",
        tags=None,
        include_completed=False,
        response_format="concise",
        limit=50,
    )
    paths = [item.path for item in list_result.results]
    assert "old-project/readme.md" not in paths
    assert "old-project/notes.md" not in paths
