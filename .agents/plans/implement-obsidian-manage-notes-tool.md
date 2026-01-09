# Feature: obsidian_manage_notes Tool

## Overview

Implement `obsidian_manage_notes` - the second of 3 MVP tools. Handles note CRUD + task completion with bulk support.

**Operations:** read, create, update, append, delete, complete_task

## Prerequisites - READ BEFORE IMPLEMENTING

| File | Why |
|------|-----|
| `app/features/obsidian_query_vault/obsidian_query_vault_tool.py` | **Primary pattern** - Copy this structure exactly |
| `app/features/obsidian_query_vault/obsidian_query_vault_schemas.py` | Schema pattern |
| `app/core/agents/tool_registry.py` | Registration pattern |
| `app/shared/vault/manager.py:325-360` | `read_note()` pattern |
| `.agents/reference/mvp-tool-designs.md:63-195` | Tool specification |

## Files to Create

```
app/features/obsidian_manage_notes/
├── __init__.py
├── obsidian_manage_notes_schemas.py
├── obsidian_manage_notes_tool.py
└── tests/
    ├── __init__.py
    └── test_obsidian_manage_notes_tool.py
```

## Files to Modify

- `app/shared/vault/exceptions.py` - Add `NoteAlreadyExistsError`, `TaskNotFoundError`
- `app/shared/vault/__init__.py` - Export new exceptions
- `app/shared/vault/manager.py` - Add 5 new methods + `_atomic_write` helper
- `app/core/agents/tool_registry.py` - Register new tool
- `app/core/agents/base.py` - Update SYSTEM_PROMPT
- `app/shared/vault/tests/test_manager.py` - Add tests for new methods

---

## TASKS

Execute in order. Each task has validation at the end.

---

### Task 1: Add exceptions

**File:** `app/shared/vault/exceptions.py`

Add after `FolderNotFoundError`:

```python
class NoteAlreadyExistsError(VaultError):
    """Exception raised when attempting to create a note that already exists."""
    pass


class TaskNotFoundError(VaultError):
    """Exception raised when a task cannot be found."""
    pass
```

**Validate:** `uv run python -c "from app.shared.vault.exceptions import NoteAlreadyExistsError, TaskNotFoundError; print('OK')"`

---

### Task 2: Update vault exports

**File:** `app/shared/vault/__init__.py`

Add to imports and `__all__`:
- `NoteAlreadyExistsError`
- `TaskNotFoundError`

**Validate:** `uv run python -c "from app.shared.vault import NoteAlreadyExistsError, TaskNotFoundError; print('OK')"`

---

### Task 3: Create feature directory

```bash
mkdir -p app/features/obsidian_manage_notes/tests
touch app/features/obsidian_manage_notes/__init__.py
touch app/features/obsidian_manage_notes/tests/__init__.py
```

---

### Task 4: Create schemas

**File:** `app/features/obsidian_manage_notes/obsidian_manage_notes_schemas.py`

```python
"""Pydantic schemas for obsidian_manage_notes tool."""

from pydantic import BaseModel


class BulkNoteItem(BaseModel):
    """Item for bulk note operations."""
    path: str
    content: str | None = None
    folder: str | None = None
    task_identifier: str | None = None


class BulkErrorItem(BaseModel):
    """Error information for a failed bulk item."""
    path: str
    error: str


class NoteOperationResult(BaseModel):
    """Result from obsidian_manage_notes operations."""
    success: bool
    operation: str
    path: str
    message: str
    content: str | None = None
    affected_count: int | None = None
    errors: list[BulkErrorItem] | None = None
```

**Validate:** `uv run python -c "from app.features.obsidian_manage_notes.obsidian_manage_notes_schemas import NoteOperationResult, BulkNoteItem; print('OK')"`

---

### Task 5: Add VaultManager imports

**File:** `app/shared/vault/manager.py`

Add at top with other imports:
```python
import uuid
```

Update exception imports to include:
```python
from app.shared.vault.exceptions import (
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
    PathTraversalError,
    TaskNotFoundError,
)
```

---

### Task 6: Add `_atomic_write` helper to VaultManager

**File:** `app/shared/vault/manager.py`

Add after `_read_note_content` method (~line 215):

```python
async def _atomic_write(self, path: Path, content: str) -> None:
    """Write content atomically using temp file + replace."""
    temp_path = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
    try:
        async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.replace(temp_path, path)
    except Exception:
        try:
            if await aiofiles.os.path.exists(temp_path):
                await aiofiles.os.remove(temp_path)
        except OSError:
            pass
        raise
```

---

### Task 7: Add `create_note` method to VaultManager

Add after `read_note` method:

```python
async def create_note(
    self,
    path: str,
    content: str,
    folder: str | None = None,
) -> NoteContent:
    """Create a new note in the vault."""
    if folder:
        full_rel_path = f"{folder.rstrip('/')}/{path.lstrip('/')}"
    else:
        full_rel_path = path

    if not full_rel_path.endswith(".md"):
        full_rel_path += ".md"

    full_path = self.validate_path(full_rel_path)

    if await aiofiles.os.path.exists(full_path):
        raise NoteAlreadyExistsError(
            f"Note already exists: {full_rel_path}. "
            "Use operation='update' to modify existing notes."
        )

    parent = full_path.parent
    if not await aiofiles.os.path.exists(parent):
        await aiofiles.os.makedirs(parent, exist_ok=True)

    await self._atomic_write(full_path, content)
    logger.info("vault.notes.create_completed", path=full_rel_path)

    return await self.read_note(full_rel_path)
```

---

### Task 8: Add `update_note` method to VaultManager

```python
async def update_note(
    self,
    path: str,
    content: str,
    preserve_frontmatter: bool = True,
) -> NoteContent:
    """Update an existing note's content."""
    full_path = self.validate_path(path)

    if not await aiofiles.os.path.exists(full_path):
        raise NoteNotFoundError(
            f"Note not found: {path}. "
            "Use obsidian_query_vault with operation='list_notes' to see available notes."
        )

    if preserve_frontmatter:
        existing = await self._read_note_content(full_path)
        if existing:
            try:
                post = frontmatter.loads(existing)
                post.content = content
                final_content = frontmatter.dumps(post, sort_keys=False)
            except Exception:
                final_content = content
        else:
            final_content = content
    else:
        final_content = content

    await self._atomic_write(full_path, final_content)
    logger.info("vault.notes.update_completed", path=path)

    return await self.read_note(path)
```

---

### Task 9: Add `append_note` method to VaultManager

```python
async def append_note(self, path: str, content: str) -> NoteContent:
    """Append content to an existing note."""
    full_path = self.validate_path(path)

    if not await aiofiles.os.path.exists(full_path):
        raise NoteNotFoundError(
            f"Note not found: {path}. "
            "Use obsidian_query_vault with operation='list_notes' to see available notes."
        )

    existing = await self._read_note_content(full_path)
    if existing is None:
        raise NoteNotFoundError(f"Could not read note: {path}")

    if existing and not existing.endswith("\n"):
        new_content = existing + "\n" + content
    else:
        new_content = (existing or "") + content

    await self._atomic_write(full_path, new_content)
    logger.info("vault.notes.append_completed", path=path)

    return await self.read_note(path)
```

---

### Task 10: Add `delete_note` method to VaultManager

```python
async def delete_note(self, path: str) -> None:
    """Delete a note from the vault."""
    full_path = self.validate_path(path)

    if not await aiofiles.os.path.exists(full_path):
        raise NoteNotFoundError(
            f"Note not found: {path}. "
            "Use obsidian_query_vault with operation='list_notes' to see available notes."
        )

    await aiofiles.os.remove(full_path)
    logger.info("vault.notes.delete_completed", path=path)
```

---

### Task 11: Add `complete_task` method to VaultManager

```python
async def complete_task(self, path: str, task_identifier: str) -> TaskInfo:
    """Mark a task as complete using cascading match: line number -> exact -> substring."""
    full_path = self.validate_path(path)

    if not await aiofiles.os.path.exists(full_path):
        raise NoteNotFoundError(
            f"Note not found: {path}. "
            "Use obsidian_query_vault with operation='list_notes' to see available notes."
        )

    content = await self._read_note_content(full_path)
    if content is None:
        raise NoteNotFoundError(f"Could not read note: {path}")

    # Find all tasks
    tasks: list[tuple[re.Match[str], int, str, bool]] = []
    for match in TASK_PATTERN.finditer(content):
        checkbox = match.group(2)
        task_text = match.group(3).strip()
        line_num = content[: match.start()].count("\n") + 1
        completed = checkbox.lower() == "x"
        tasks.append((match, line_num, task_text, completed))

    if not tasks:
        raise TaskNotFoundError(
            f"No tasks found in {path}. "
            "Use obsidian_query_vault with operation='list_tasks' to find notes with tasks."
        )

    # Find target task
    target_match: re.Match[str] | None = None
    target_info: tuple[int, str, bool] | None = None

    # 1. Try line number
    try:
        line_num = int(task_identifier)
        for match, ln, text, completed in tasks:
            if ln == line_num:
                if completed:
                    raise TaskNotFoundError(f"Task at line {line_num} is already completed: '{text}'")
                target_match = match
                target_info = (ln, text, completed)
                break
        if target_match is None:
            task_lines = [str(ln) for _, ln, _, _ in tasks]
            raise TaskNotFoundError(f"No task at line {line_num}. Tasks at lines: {', '.join(task_lines)}")
    except ValueError:
        id_lower = task_identifier.lower()

        # 2. Exact match
        exact = [(m, ln, t, c) for m, ln, t, c in tasks if t.lower() == id_lower and not c]
        if len(exact) == 1:
            target_match, ln, text, _ = exact[0]
            target_info = (ln, text, False)
        elif len(exact) == 0:
            # 3. Substring match
            substr = [(m, ln, t, c) for m, ln, t, c in tasks if id_lower in t.lower() and not c]
            if len(substr) == 1:
                target_match, ln, text, _ = substr[0]
                target_info = (ln, text, False)
            elif len(substr) > 1:
                matches_str = ", ".join([f"'{t}' (line {ln})" for _, ln, t, _ in substr])
                raise TaskNotFoundError(f"Multiple tasks match '{task_identifier}': {matches_str}")
            else:
                available = ", ".join([f"'{t}'" for _, _, t, c in tasks if not c])
                raise TaskNotFoundError(f"Task not found: '{task_identifier}'. Available: {available or 'none'}")
        else:
            matches_str = ", ".join([f"'{t}' (line {ln})" for _, ln, t, _ in exact])
            raise TaskNotFoundError(f"Multiple tasks match '{task_identifier}': {matches_str}")

    if target_match is None or target_info is None:
        raise TaskNotFoundError(f"Could not find task: '{task_identifier}'")

    # Replace checkbox
    line_num, task_text, _ = target_info
    replacement = f"{target_match.group(1)}- [x] {target_match.group(3)}"
    new_content = content[: target_match.start()] + replacement + content[target_match.end():]

    await self._atomic_write(full_path, new_content)
    logger.info("vault.notes.complete_task_completed", path=path, task=task_text)

    return TaskInfo(path=path, task_text=task_text, completed=True, line_number=line_num)
```

**Validate Tasks 5-11:** `uv run mypy app/shared/vault/manager.py`

---

### Task 12: Create tool implementation

**File:** `app/features/obsidian_manage_notes/obsidian_manage_notes_tool.py`

```python
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
                    success=False, operation=operation, path="",
                    message="Bulk mode requires items parameter.",
                )
            return await _handle_bulk_operation(vault, operation, items)

        try:
            if operation == "read":
                note = await vault.read_note(path)
                return NoteOperationResult(
                    success=True, operation=operation, path=path,
                    message=f"Successfully read note: {path}", content=note.content,
                )

            elif operation == "create":
                if not content:
                    return NoteOperationResult(
                        success=False, operation=operation, path=path,
                        message="Content is required for create operation.",
                    )
                note = await vault.create_note(path, content, folder)
                return NoteOperationResult(
                    success=True, operation=operation, path=note.path,
                    message=f"Successfully created note: {note.path}",
                )

            elif operation == "update":
                if not content:
                    return NoteOperationResult(
                        success=False, operation=operation, path=path,
                        message="Content is required for update operation.",
                    )
                await vault.update_note(path, content)
                return NoteOperationResult(
                    success=True, operation=operation, path=path,
                    message=f"Successfully updated note: {path}",
                )

            elif operation == "append":
                if not content:
                    return NoteOperationResult(
                        success=False, operation=operation, path=path,
                        message="Content is required for append operation.",
                    )
                await vault.append_note(path, content)
                return NoteOperationResult(
                    success=True, operation=operation, path=path,
                    message=f"Successfully appended to note: {path}",
                )

            elif operation == "delete":
                await vault.delete_note(path)
                return NoteOperationResult(
                    success=True, operation=operation, path=path,
                    message=f"Successfully deleted note: {path}",
                )

            elif operation == "complete_task":
                if not task_identifier:
                    return NoteOperationResult(
                        success=False, operation=operation, path=path,
                        message="Task identifier is required for complete_task operation.",
                    )
                task = await vault.complete_task(path, task_identifier)
                return NoteOperationResult(
                    success=True, operation=operation, path=path,
                    message=f"Successfully completed task: '{task.task_text}'",
                )

            else:
                return NoteOperationResult(
                    success=False, operation=operation, path=path,
                    message=f"Unknown operation: {operation}",
                )

        except VaultError as e:
            logger.error(
                "vault.tool.manage_notes_failed",
                operation=operation, path=path, error=str(e), exc_info=True,
            )
            return NoteOperationResult(
                success=False, operation=operation, path=path, message=str(e),
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
        if success else
        f"Bulk {operation} partially completed: {affected} succeeded, {len(errors)} failed"
    )

    return NoteOperationResult(
        success=success, operation=operation, path="", message=message,
        affected_count=affected, errors=errors if errors else None,
    )
```

**Validate:** `uv run mypy app/features/obsidian_manage_notes/`

---

### Task 13: Create feature exports

**File:** `app/features/obsidian_manage_notes/__init__.py`

```python
"""obsidian_manage_notes feature - Note lifecycle management tool."""

from app.features.obsidian_manage_notes.obsidian_manage_notes_schemas import (
    BulkErrorItem,
    BulkNoteItem,
    NoteOperationResult,
)
from app.features.obsidian_manage_notes.obsidian_manage_notes_tool import (
    register_obsidian_manage_notes_tool,
)

__all__ = [
    "BulkErrorItem",
    "BulkNoteItem",
    "NoteOperationResult",
    "register_obsidian_manage_notes_tool",
]
```

---

### Task 14: Register tool

**File:** `app/core/agents/tool_registry.py`

Add import:
```python
from app.features.obsidian_manage_notes.obsidian_manage_notes_tool import (
    register_obsidian_manage_notes_tool,
)
```

Add in `create_obsidian_toolset()` after query tool registration:
```python
register_obsidian_manage_notes_tool(toolset)
```

**Validate:** `uv run python -c "from app.core.agents.tool_registry import create_obsidian_toolset; ts = create_obsidian_toolset(); print(list(ts.tools.keys()))"`

---

### Task 15: Update SYSTEM_PROMPT

**File:** `app/core/agents/base.py`

Replace SYSTEM_PROMPT with:

```python
SYSTEM_PROMPT = """You are Jasque, an AI assistant for Obsidian vault management.

You help users interact with their Obsidian vault using natural language.

## Available Tools

### obsidian_query_vault
Search and query the Obsidian vault. Operations:
- search_text: Full-text search across notes (requires query)
- find_by_tag: Find notes with specific tags (requires tags)
- list_notes: List notes in vault or folder
- list_folders: Get folder structure
- get_backlinks: Find notes linking to a specific note
- get_tags: Get all unique tags in vault
- list_tasks: Find task checkboxes

Use response_format="concise" (default) for brief results, "detailed" for full content.

### obsidian_manage_notes
Manage notes - create, read, update, delete, and complete tasks. Operations:
- read: Get full contents of a note
- create: Create a new note (fails if exists)
- update: Replace note content (preserves frontmatter)
- append: Add content to end of note
- delete: Remove a note from vault
- complete_task: Mark a task checkbox as done

Supports bulk operations with bulk=True and items parameter.

## Guidelines

- Use obsidian_query_vault to FIND notes, then obsidian_manage_notes to MODIFY them
- Start with concise format, use detailed only if needed
- If search returns no results, suggest alternatives
- Be helpful and conversational while being efficient with tool calls
- Folder management (create folder, move, rename) coming soon via obsidian_manage_structure
"""
```

**Validate:** `uv run python -c "from app.core.agents.base import SYSTEM_PROMPT; print('manage_notes' in SYSTEM_PROMPT)"`

---

### Task 16: Add VaultManager tests

**File:** `app/shared/vault/tests/test_manager.py`

Add imports at top:
```python
from app.shared.vault.exceptions import NoteAlreadyExistsError, TaskNotFoundError
```

Add test functions:

```python
# =============================================================================
# Create Note Tests
# =============================================================================


async def test_create_note_success(tmp_path: Path) -> None:
    manager = VaultManager(tmp_path)
    result = await manager.create_note("test.md", "# Test Note\n\nContent.")
    assert result.path == "test.md"
    assert (tmp_path / "test.md").exists()


async def test_create_note_with_folder(tmp_path: Path) -> None:
    manager = VaultManager(tmp_path)
    result = await manager.create_note("note.md", "# Note", folder="projects/new")
    assert result.path == "projects/new/note.md"
    assert (tmp_path / "projects" / "new" / "note.md").exists()


async def test_create_note_already_exists(tmp_path: Path) -> None:
    (tmp_path / "existing.md").write_text("# Existing")
    manager = VaultManager(tmp_path)
    with pytest.raises(NoteAlreadyExistsError):
        await manager.create_note("existing.md", "# New")


async def test_create_note_adds_md_extension(tmp_path: Path) -> None:
    manager = VaultManager(tmp_path)
    result = await manager.create_note("test", "# Test")
    assert result.path == "test.md"


# =============================================================================
# Update Note Tests
# =============================================================================


async def test_update_note_success(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Old")
    manager = VaultManager(tmp_path)
    result = await manager.update_note("test.md", "# New")
    assert "# New" in (tmp_path / "test.md").read_text()


async def test_update_note_preserves_frontmatter(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("---\ntitle: My Title\n---\n\n# Old")
    manager = VaultManager(tmp_path)
    await manager.update_note("test.md", "# New")
    content = (tmp_path / "test.md").read_text()
    assert "title: My Title" in content
    assert "# New" in content


async def test_update_note_not_found(tmp_path: Path) -> None:
    manager = VaultManager(tmp_path)
    with pytest.raises(NoteNotFoundError):
        await manager.update_note("nonexistent.md", "content")


# =============================================================================
# Append Note Tests
# =============================================================================


async def test_append_note_success(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Title\n\nOriginal.")
    manager = VaultManager(tmp_path)
    await manager.append_note("test.md", "\n\nAppended.")
    content = (tmp_path / "test.md").read_text()
    assert "Original." in content
    assert "Appended." in content


async def test_append_note_adds_newline(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("No newline")
    manager = VaultManager(tmp_path)
    await manager.append_note("test.md", "Appended")
    assert (tmp_path / "test.md").read_text() == "No newline\nAppended"


async def test_append_note_not_found(tmp_path: Path) -> None:
    manager = VaultManager(tmp_path)
    with pytest.raises(NoteNotFoundError):
        await manager.append_note("nonexistent.md", "content")


# =============================================================================
# Delete Note Tests
# =============================================================================


async def test_delete_note_success(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Delete me")
    manager = VaultManager(tmp_path)
    await manager.delete_note("test.md")
    assert not (tmp_path / "test.md").exists()


async def test_delete_note_not_found(tmp_path: Path) -> None:
    manager = VaultManager(tmp_path)
    with pytest.raises(NoteNotFoundError):
        await manager.delete_note("nonexistent.md")


# =============================================================================
# Complete Task Tests
# =============================================================================


async def test_complete_task_by_text_exact(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Tasks\n\n- [ ] Buy groceries\n- [ ] Call mom")
    manager = VaultManager(tmp_path)
    result = await manager.complete_task("test.md", "Buy groceries")
    assert "- [x] Buy groceries" in (tmp_path / "test.md").read_text()
    assert result.task_text == "Buy groceries"


async def test_complete_task_by_substring(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Tasks\n\n- [ ] Buy groceries from store\n- [ ] Call mom")
    manager = VaultManager(tmp_path)
    await manager.complete_task("test.md", "groceries")
    assert "- [x] Buy groceries from store" in (tmp_path / "test.md").read_text()


async def test_complete_task_by_line_number(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Tasks\n\n- [ ] First task\n- [ ] Second task")
    manager = VaultManager(tmp_path)
    await manager.complete_task("test.md", "3")
    assert "- [x] First task" in (tmp_path / "test.md").read_text()


async def test_complete_task_multiple_matches_error(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Tasks\n\n- [ ] Buy groceries\n- [ ] Buy milk")
    manager = VaultManager(tmp_path)
    with pytest.raises(TaskNotFoundError) as exc:
        await manager.complete_task("test.md", "Buy")
    assert "Multiple" in str(exc.value)


async def test_complete_task_not_found(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("# Tasks\n\n- [ ] Existing task")
    manager = VaultManager(tmp_path)
    with pytest.raises(TaskNotFoundError):
        await manager.complete_task("test.md", "nonexistent")


async def test_complete_task_preserves_indentation(tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text("- [ ] Parent\n  - [ ] Nested task")
    manager = VaultManager(tmp_path)
    await manager.complete_task("test.md", "Nested task")
    assert "  - [x] Nested task" in (tmp_path / "test.md").read_text()
```

**Validate:** `uv run pytest app/shared/vault/tests/test_manager.py -v -k "create_note or update_note or append_note or delete_note or complete_task"`

---

### Task 17: Create tool tests

**File:** `app/features/obsidian_manage_notes/tests/test_obsidian_manage_notes_tool.py`

```python
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


# Parameter validation tests

async def test_create_requires_content(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    result = await tool_fn(mock_ctx, operation="create", path="test.md", content=None)
    assert result.success is False
    assert "content" in result.message.lower()


async def test_complete_task_requires_identifier(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    result = await tool_fn(mock_ctx, operation="complete_task", path="test.md", task_identifier=None)
    assert result.success is False


async def test_bulk_requires_items(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    result = await tool_fn(mock_ctx, operation="create", path="", bulk=True, items=None)
    assert result.success is False


# Operation tests

async def test_read_success(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Content", tags=[], metadata={})

    with patch("app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager") as MockVault:
        MockVault.return_value.read_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(mock_ctx, operation="read", path="test.md")

    assert result.success is True
    assert result.content == "# Content"


async def test_create_success(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch("app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager") as MockVault:
        MockVault.return_value.create_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(mock_ctx, operation="create", path="test.md", content="# Test")

    assert result.success is True


async def test_complete_task_success(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_task = TaskInfo(path="test.md", task_text="Buy groceries", completed=True, line_number=3)

    with patch("app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager") as MockVault:
        MockVault.return_value.complete_task = AsyncMock(return_value=mock_task)
        result = await tool_fn(mock_ctx, operation="complete_task", path="test.md", task_identifier="Buy groceries")

    assert result.success is True
    assert "Buy groceries" in result.message


async def test_error_handling(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function

    with patch("app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager") as MockVault:
        MockVault.return_value.read_note = AsyncMock(side_effect=NoteNotFoundError("Not found"))
        result = await tool_fn(mock_ctx, operation="read", path="missing.md")

    assert result.success is False
    assert "not found" in result.message.lower()


# Bulk tests

async def test_bulk_success(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch("app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager") as MockVault:
        MockVault.return_value.create_note = AsyncMock(return_value=mock_note)
        result = await tool_fn(
            mock_ctx, operation="create", path="", bulk=True,
            items=[BulkNoteItem(path="a.md", content="# A"), BulkNoteItem(path="b.md", content="# B")],
        )

    assert result.success is True
    assert result.affected_count == 2


async def test_bulk_partial_failure(mock_ctx, toolset):
    tool_fn = toolset.tools["obsidian_manage_notes"].function
    mock_note = NoteContent(path="test.md", title="Test", content="# Test", tags=[], metadata={})

    with patch("app.features.obsidian_manage_notes.obsidian_manage_notes_tool.VaultManager") as MockVault:
        MockVault.return_value.create_note = AsyncMock(side_effect=[mock_note, NoteAlreadyExistsError("Exists")])
        result = await tool_fn(
            mock_ctx, operation="create", path="", bulk=True,
            items=[BulkNoteItem(path="a.md", content="# A"), BulkNoteItem(path="b.md", content="# B")],
        )

    assert result.success is False
    assert result.affected_count == 1
    assert len(result.errors) == 1
```

**Validate:** `uv run pytest app/features/obsidian_manage_notes/tests/ -v`

---

### Task 18: Run full validation

```bash
uv run ruff check .
uv run ruff format .
uv run mypy app/
uv run pyright app/
uv run pytest -v
```

All must pass.

---

## ACCEPTANCE CRITERIA

- [ ] 6 operations: read, create, update, append, delete, complete_task
- [ ] Bulk operations with affected_count and errors
- [ ] Atomic writes via temp file + replace
- [ ] Frontmatter preserved during updates
- [ ] Task completion with line number and text matching
- [ ] All validation commands pass
- [ ] VaultManager tests pass
- [ ] Tool tests pass
- [ ] SYSTEM_PROMPT updated
- [ ] Tool registered
