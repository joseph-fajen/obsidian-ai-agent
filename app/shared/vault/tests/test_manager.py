"""Tests for VaultManager class."""

from pathlib import Path

import pytest

from app.shared.vault import (
    FolderNotFoundError,
    NoteNotFoundError,
    PathTraversalError,
    VaultManager,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault with test notes."""
    # Create test structure
    (tmp_path / "notes").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / ".obsidian").mkdir()  # Should be skipped

    # Create test note with frontmatter and tasks
    note1 = tmp_path / "notes" / "test-note.md"
    note1.write_text("""---
title: Test Note
tags: [project, important]
---

# Test Note

This is test content with a [[link-to-other]] and #inline-tag.

- [ ] Incomplete task
- [x] Completed task
- [ ] Another incomplete task
""")

    # Create another note
    note2 = tmp_path / "projects" / "alpha.md"
    note2.write_text("""---
title: Alpha Project
tags: work
---

# Alpha Project

This is the alpha project with [[test-note]] backlink.

Budget discussion for Q4.
""")

    # Create note without frontmatter
    note3 = tmp_path / "simple.md"
    note3.write_text("""# Simple Note

Just content, no frontmatter.
#standalone-tag
""")

    # Create hidden file (should be skipped)
    (tmp_path / ".hidden.md").write_text("Hidden content")

    return tmp_path


# =============================================================================
# Path Validation Tests
# =============================================================================


def test_validate_path_within_vault(vault_path: Path):
    """Valid path within vault should pass."""
    manager = VaultManager(vault_path)
    result = manager.validate_path("notes/test-note.md")
    assert result == vault_path / "notes" / "test-note.md"


def test_validate_path_empty_returns_root(vault_path: Path):
    """Empty path should return vault root."""
    manager = VaultManager(vault_path)
    result = manager.validate_path("")
    assert result == vault_path


def test_validate_path_traversal_blocked(vault_path: Path):
    """Path traversal should be blocked."""
    manager = VaultManager(vault_path)
    with pytest.raises(PathTraversalError, match="Access denied"):
        manager.validate_path("../../../etc/passwd")


def test_validate_path_double_dots_blocked(vault_path: Path):
    """Path with .. should be blocked."""
    manager = VaultManager(vault_path)
    with pytest.raises(PathTraversalError, match="Access denied"):
        manager.validate_path("notes/../../../etc/passwd")


# =============================================================================
# list_notes Tests
# =============================================================================


async def test_list_notes_empty_vault(tmp_path: Path):
    """Empty vault returns empty list."""
    manager = VaultManager(tmp_path)
    notes = await manager.list_notes()
    assert notes == []


async def test_list_notes_with_files(vault_path: Path):
    """Notes are found and returned with correct info."""
    manager = VaultManager(vault_path)
    notes = await manager.list_notes()

    # Should find 3 notes (not hidden ones)
    assert len(notes) == 3

    paths = {n.path for n in notes}
    assert "notes/test-note.md" in paths
    assert "projects/alpha.md" in paths
    assert "simple.md" in paths


async def test_list_notes_in_folder(vault_path: Path):
    """Notes in specific folder are listed."""
    manager = VaultManager(vault_path)
    notes = await manager.list_notes("notes")

    assert len(notes) == 1
    assert notes[0].path == "notes/test-note.md"
    assert notes[0].title == "Test Note"


async def test_list_notes_skips_hidden(vault_path: Path):
    """Hidden files and folders are skipped."""
    manager = VaultManager(vault_path)
    notes = await manager.list_notes()

    paths = {n.path for n in notes}
    assert ".hidden.md" not in paths
    assert not any(".obsidian" in p for p in paths)


async def test_list_notes_includes_tags(vault_path: Path):
    """Notes include tags from frontmatter and inline."""
    manager = VaultManager(vault_path)
    notes = await manager.list_notes()

    test_note = next(n for n in notes if n.path == "notes/test-note.md")
    assert "project" in test_note.tags
    assert "important" in test_note.tags
    assert "inline-tag" in test_note.tags


async def test_list_notes_folder_not_found(vault_path: Path):
    """Non-existent folder raises error."""
    manager = VaultManager(vault_path)
    with pytest.raises(FolderNotFoundError, match="Folder not found"):
        await manager.list_notes("nonexistent")


# =============================================================================
# list_folders Tests
# =============================================================================


async def test_list_folders(vault_path: Path):
    """Folders are listed correctly."""
    manager = VaultManager(vault_path)
    folders = await manager.list_folders()

    names = {f.name for f in folders}
    assert "notes" in names
    assert "projects" in names
    assert ".obsidian" not in names  # Hidden


async def test_list_folders_nested(vault_path: Path):
    """Folders in specific path are listed."""
    manager = VaultManager(vault_path)
    # Create nested folder
    (vault_path / "projects" / "subproject").mkdir()

    folders = await manager.list_folders("projects")
    assert len(folders) == 1
    assert folders[0].name == "subproject"


# =============================================================================
# read_note Tests
# =============================================================================


async def test_read_note_success(vault_path: Path):
    """Reading a note returns content and metadata."""
    manager = VaultManager(vault_path)
    note = await manager.read_note("notes/test-note.md")

    assert note.title == "Test Note"
    assert "test content" in note.content.lower()
    assert "project" in note.tags
    assert note.metadata.get("title") == "Test Note"


async def test_read_note_not_found(vault_path: Path):
    """Non-existent note raises error."""
    manager = VaultManager(vault_path)
    with pytest.raises(NoteNotFoundError, match="Note not found"):
        await manager.read_note("nonexistent.md")


async def test_read_note_without_frontmatter(vault_path: Path):
    """Note without frontmatter uses filename as title."""
    manager = VaultManager(vault_path)
    note = await manager.read_note("simple.md")

    assert note.title == "simple"  # Filename stem
    assert note.metadata == {}


# =============================================================================
# search_text Tests
# =============================================================================


async def test_search_text_finds_match(vault_path: Path):
    """Search finds matching content."""
    manager = VaultManager(vault_path)
    results = await manager.search_text("budget")

    assert len(results) == 1
    assert results[0].path == "projects/alpha.md"
    assert "budget" in results[0].snippet.lower()


async def test_search_text_case_insensitive(vault_path: Path):
    """Search is case insensitive."""
    manager = VaultManager(vault_path)
    results = await manager.search_text("BUDGET")

    assert len(results) == 1
    assert results[0].path == "projects/alpha.md"


async def test_search_text_in_folder(vault_path: Path):
    """Search can be scoped to folder."""
    manager = VaultManager(vault_path)
    results = await manager.search_text("project", path="notes")

    # "project" is in test-note.md's frontmatter/content
    assert all(r.path.startswith("notes/") for r in results)


async def test_search_text_with_limit(vault_path: Path):
    """Search respects limit."""
    manager = VaultManager(vault_path)
    results = await manager.search_text("the", limit=1)

    assert len(results) <= 1


async def test_search_text_no_results(vault_path: Path):
    """Search with no matches returns empty list."""
    manager = VaultManager(vault_path)
    results = await manager.search_text("xyznonexistent")

    assert results == []


# =============================================================================
# find_by_tag Tests
# =============================================================================


async def test_find_by_tag_frontmatter(vault_path: Path):
    """Find notes with frontmatter tags."""
    manager = VaultManager(vault_path)
    results = await manager.find_by_tag(["project"])

    assert len(results) >= 1
    paths = {r.path for r in results}
    assert "notes/test-note.md" in paths


async def test_find_by_tag_inline(vault_path: Path):
    """Find notes with inline tags."""
    manager = VaultManager(vault_path)
    results = await manager.find_by_tag(["inline-tag"])

    assert len(results) == 1
    assert results[0].path == "notes/test-note.md"


async def test_find_by_tag_multiple(vault_path: Path):
    """Find notes matching any of multiple tags."""
    manager = VaultManager(vault_path)
    results = await manager.find_by_tag(["work", "important"])

    paths = {r.path for r in results}
    assert "projects/alpha.md" in paths  # has "work"
    assert "notes/test-note.md" in paths  # has "important"


async def test_find_by_tag_with_hash(vault_path: Path):
    """Tags with # prefix are handled."""
    manager = VaultManager(vault_path)
    results = await manager.find_by_tag(["#standalone-tag"])

    assert len(results) == 1
    assert results[0].path == "simple.md"


async def test_find_by_tag_in_folder(vault_path: Path):
    """Find by tag can be scoped to folder."""
    manager = VaultManager(vault_path)
    results = await manager.find_by_tag(["project"], path="notes")

    assert len(results) == 1
    assert results[0].path == "notes/test-note.md"


# =============================================================================
# get_backlinks Tests
# =============================================================================


async def test_get_backlinks(vault_path: Path):
    """Find notes linking to specified note."""
    manager = VaultManager(vault_path)
    results = await manager.get_backlinks("notes/test-note.md")

    assert len(results) == 1
    assert results[0].path == "projects/alpha.md"
    assert "test-note" in results[0].context


async def test_get_backlinks_not_found(vault_path: Path):
    """Backlinks for non-existent note raises error."""
    manager = VaultManager(vault_path)
    with pytest.raises(NoteNotFoundError):
        await manager.get_backlinks("nonexistent.md")


async def test_get_backlinks_with_limit(vault_path: Path):
    """Backlinks respects limit."""
    manager = VaultManager(vault_path)
    results = await manager.get_backlinks("notes/test-note.md", limit=0)

    assert results == []


# =============================================================================
# get_tags Tests
# =============================================================================


async def test_get_tags_all_unique(vault_path: Path):
    """Get all unique tags in vault."""
    manager = VaultManager(vault_path)
    tags = await manager.get_tags()

    assert "project" in tags
    assert "important" in tags
    assert "inline-tag" in tags
    assert "work" in tags
    assert "standalone-tag" in tags

    # Should be unique (no duplicates)
    assert len(tags) == len(set(tags))


async def test_get_tags_sorted(vault_path: Path):
    """Tags are returned sorted."""
    manager = VaultManager(vault_path)
    tags = await manager.get_tags()

    assert tags == sorted(tags)


# =============================================================================
# list_tasks Tests
# =============================================================================


async def test_list_tasks_incomplete(vault_path: Path):
    """Find incomplete tasks."""
    manager = VaultManager(vault_path)
    tasks = await manager.list_tasks()

    # Should find 2 incomplete tasks (default excludes completed)
    assert len(tasks) == 2
    assert all(not t.completed for t in tasks)

    texts = {t.task_text for t in tasks}
    assert "Incomplete task" in texts
    assert "Another incomplete task" in texts


async def test_list_tasks_include_completed(vault_path: Path):
    """Find all tasks including completed."""
    manager = VaultManager(vault_path)
    tasks = await manager.list_tasks(include_completed=True)

    # Should find 3 tasks total
    assert len(tasks) == 3

    completed = [t for t in tasks if t.completed]
    assert len(completed) == 1
    assert completed[0].task_text == "Completed task"


async def test_list_tasks_in_folder(vault_path: Path):
    """Find tasks in specific folder."""
    manager = VaultManager(vault_path)
    tasks = await manager.list_tasks(path="notes")

    assert len(tasks) >= 2
    assert all(t.path.startswith("notes/") for t in tasks)


async def test_list_tasks_with_limit(vault_path: Path):
    """Tasks respects limit."""
    manager = VaultManager(vault_path)
    tasks = await manager.list_tasks(limit=1)

    assert len(tasks) == 1


async def test_list_tasks_includes_line_number(vault_path: Path):
    """Tasks include line numbers."""
    manager = VaultManager(vault_path)
    tasks = await manager.list_tasks()

    assert all(t.line_number > 0 for t in tasks)


# =============================================================================
# Edge Cases
# =============================================================================


async def test_handles_unicode_content(tmp_path: Path):
    """Manager handles unicode content correctly."""
    manager = VaultManager(tmp_path)

    note = tmp_path / "unicode.md"
    note.write_text(
        """---
title: Unicode Test
tags: [emoji, japanese]
---

# Unicode Test

Content with emoji: 🎉 and Japanese: 日本語
""",
        encoding="utf-8",
    )

    notes = await manager.list_notes()
    assert len(notes) == 1

    content = await manager.read_note("unicode.md")
    assert "🎉" in content.content
    assert "日本語" in content.content
