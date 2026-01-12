# Feature: obsidian_manage_structure Tool

Complete the MVP by implementing the third tool for folder management operations.

## Overview

| Aspect | Details |
|--------|---------|
| **Goal** | 5 operations: create_folder, rename, delete_folder, move, list_structure |
| **Pattern** | Mirror `obsidian_manage_notes` tool structure |
| **Bulk Support** | move and rename operations |

## User Story

As an Obsidian vault user, I want to organize my vault folders through natural language, so that I can manage structure without manual file operations.

---

## CONTEXT REFERENCES - READ BEFORE IMPLEMENTING

| File | Why |
|------|-----|
| `app/features/obsidian_manage_notes/obsidian_manage_notes_tool.py` | Tool pattern to mirror |
| `app/features/obsidian_manage_notes/obsidian_manage_notes_schemas.py` | Schema pattern |
| `app/shared/vault/manager.py` lines 400-450 | VaultManager method pattern |
| `app/shared/vault/exceptions.py` | Exception pattern |
| `app/core/agents/tool_registry.py` | Registration pattern |
| `.agents/reference/mvp-tool-designs.md` lines 367-556 | Tool specification |

### New Files to Create

```
app/features/obsidian_manage_structure/
├── __init__.py
├── obsidian_manage_structure_schemas.py
├── obsidian_manage_structure_tool.py
└── tests/
    ├── __init__.py
    └── test_obsidian_manage_structure_tool.py
```

---

## IMPLEMENTATION TASKS

### Task 1: ADD Exceptions

**File:** `app/shared/vault/exceptions.py`

Add after `TaskNotFoundError`:
```python
class FolderAlreadyExistsError(VaultError):
    """Folder already exists at the specified path."""

class FolderNotEmptyError(VaultError):
    """Folder is not empty and force=False."""
```

**Update** `app/shared/vault/__init__.py` to export both.

**VALIDATE:** `uv run python -c "from app.shared.vault import FolderAlreadyExistsError, FolderNotEmptyError; print('OK')"`

---

### Task 2: ADD FolderNode Dataclass

**File:** `app/shared/vault/manager.py`

Add after existing dataclasses (~line 50):
```python
@dataclass
class FolderNode:
    """A node in the vault folder tree structure."""
    name: str
    path: str
    node_type: Literal["folder", "note"]
    children: list[FolderNode] | None = None
```

**Update** `app/shared/vault/__init__.py` to export `FolderNode`.

**VALIDATE:** `uv run python -c "from app.shared.vault import FolderNode; print('OK')"`

---

### Task 3: IMPLEMENT create_folder Method

**File:** `app/shared/vault/manager.py`

```python
async def create_folder(self, path: str) -> FolderInfo:
    """Create a folder, including any necessary parent folders."""
    full_path = self.validate_path(path)
    if await aiofiles.os.path.exists(full_path):
        raise FolderAlreadyExistsError(
            f"Folder already exists: {path}. Use a different path or delete existing folder first."
        )
    await aiofiles.os.makedirs(full_path, exist_ok=False)
    logger.info("vault.structure.folder_created", path=path)
    return FolderInfo(path=path, name=full_path.name)
```

**VALIDATE:** `uv run mypy app/shared/vault/manager.py --no-error-summary`

---

### Task 4: IMPLEMENT rename Method

**File:** `app/shared/vault/manager.py`

```python
async def rename(self, path: str, new_path: str) -> FolderInfo | NoteContent:
    """Rename a file or folder."""
    full_path = self.validate_path(path)
    full_new_path = self.validate_path(new_path)

    if not await aiofiles.os.path.exists(full_path):
        if path.endswith(".md"):
            raise NoteNotFoundError(f"Note not found: {path}. Use obsidian_query_vault to list notes.")
        raise FolderNotFoundError(f"Folder not found: {path}. Use list_structure to see folders.")

    if await aiofiles.os.path.exists(full_new_path):
        if new_path.endswith(".md"):
            raise NoteAlreadyExistsError(f"Note already exists: {new_path}.")
        raise FolderAlreadyExistsError(f"Folder already exists: {new_path}.")

    await aiofiles.os.rename(full_path, full_new_path)
    logger.info("vault.structure.renamed", old_path=path, new_path=new_path)

    if await aiofiles.os.path.isfile(full_new_path):
        return await self.read_note(new_path)
    return FolderInfo(path=new_path, name=full_new_path.name)
```

---

### Task 5: IMPLEMENT delete_folder Method

**File:** `app/shared/vault/manager.py`

```python
async def delete_folder(self, path: str, force: bool = False) -> None:
    """Delete a folder. Use force=True for non-empty folders."""
    full_path = self.validate_path(path)

    if not await aiofiles.os.path.exists(full_path):
        raise FolderNotFoundError(f"Folder not found: {path}.")
    if not await aiofiles.os.path.isdir(full_path):
        raise FolderNotFoundError(f"Path is not a folder: {path}. Use obsidian_manage_notes to delete notes.")

    contents = await aiofiles.os.listdir(full_path)
    if contents and not force:
        raise FolderNotEmptyError(f"Folder not empty: {path}. Use force=True or empty folder first.")

    if force and contents:
        import asyncio
        import shutil
        await asyncio.to_thread(shutil.rmtree, full_path)
    else:
        await aiofiles.os.rmdir(full_path)

    logger.info("vault.structure.folder_deleted", path=path, force=force)
```

---

### Task 6: IMPLEMENT move Method

**File:** `app/shared/vault/manager.py`

```python
async def move(self, path: str, new_path: str) -> FolderInfo | NoteContent:
    """Move a file or folder to a new location. Creates parent dirs if needed."""
    full_path = self.validate_path(path)
    full_new_path = self.validate_path(new_path)

    if not await aiofiles.os.path.exists(full_path):
        if path.endswith(".md"):
            raise NoteNotFoundError(f"Note not found: {path}.")
        raise FolderNotFoundError(f"Folder not found: {path}.")

    if await aiofiles.os.path.exists(full_new_path):
        if new_path.endswith(".md"):
            raise NoteAlreadyExistsError(f"Destination exists: {new_path}.")
        raise FolderAlreadyExistsError(f"Destination exists: {new_path}.")

    parent = full_new_path.parent
    if not await aiofiles.os.path.exists(parent):
        await aiofiles.os.makedirs(parent, exist_ok=True)

    await aiofiles.os.rename(full_path, full_new_path)
    logger.info("vault.structure.moved", old_path=path, new_path=new_path)

    if await aiofiles.os.path.isfile(full_new_path):
        return await self.read_note(new_path)
    return FolderInfo(path=new_path, name=full_new_path.name)
```

---

### Task 7: IMPLEMENT list_structure Method

**File:** `app/shared/vault/manager.py`

```python
async def list_structure(self, path: str | None = None) -> list[FolderNode]:
    """Get hierarchical folder/file tree structure."""
    if path:
        full_path = self.validate_path(path)
        if not await aiofiles.os.path.exists(full_path):
            raise FolderNotFoundError(f"Folder not found: {path}.")
    else:
        full_path = self.vault_path
    return await self._build_structure_tree(full_path, path or "")

async def _build_structure_tree(self, full_path: Path, rel_path: str) -> list[FolderNode]:
    """Recursively build folder tree structure."""
    nodes: list[FolderNode] = []
    try:
        entries = await aiofiles.os.listdir(full_path)
    except OSError:
        return nodes

    for name in sorted(entries):
        if self._is_hidden(name):
            continue
        entry_path = full_path / name
        entry_rel = f"{rel_path}/{name}".lstrip("/")
        is_dir = await aiofiles.os.path.isdir(entry_path)

        if is_dir:
            children = await self._build_structure_tree(entry_path, entry_rel)
            nodes.append(FolderNode(name=name, path=entry_rel, node_type="folder", children=children))
        elif name.endswith(".md"):
            nodes.append(FolderNode(name=name, path=entry_rel, node_type="note", children=None))
    return nodes
```

**VALIDATE:** `uv run mypy app/shared/vault/manager.py --no-error-summary`

---

### Task 8: ADD VaultManager Tests

**File:** `app/shared/vault/tests/test_manager.py`

Add test classes for new methods. Follow existing test patterns. Cover:

**TestCreateFolder:** success, nested creation, already exists error
**TestRename:** folder rename, note rename, not found error, destination exists
**TestDeleteFolder:** empty folder, non-empty requires force, force deletes recursively
**TestMove:** move note, move folder, creates parent dirs, not found error
**TestListStructure:** root listing, nested children, skips hidden files

Each test: create temp files/folders, call method, assert results.

**VALIDATE:** `uv run pytest app/shared/vault/tests/test_manager.py -v --tb=short`

---

### Task 9: CREATE Feature Directory

```bash
mkdir -p app/features/obsidian_manage_structure/tests
touch app/features/obsidian_manage_structure/__init__.py
touch app/features/obsidian_manage_structure/tests/__init__.py
```

---

### Task 10: CREATE Schemas

**File:** `app/features/obsidian_manage_structure/obsidian_manage_structure_schemas.py`

```python
"""Schemas for obsidian_manage_structure tool."""
from pydantic import BaseModel
from app.shared.vault import FolderNode

class BulkStructureItem(BaseModel):
    """Item for bulk structure operations (move/rename)."""
    path: str
    new_path: str

class BulkErrorItem(BaseModel):
    """Error information for a failed bulk item."""
    path: str
    error: str

class StructureOperationResult(BaseModel):
    """Result from obsidian_manage_structure operations."""
    success: bool
    operation: str
    path: str
    message: str
    new_path: str | None = None
    affected_count: int | None = None
    errors: list[BulkErrorItem] | None = None
    structure: list[FolderNode] | None = None
```

**VALIDATE:** `uv run mypy app/features/obsidian_manage_structure/`

---

### Task 11: CREATE Tool Implementation

**File:** `app/features/obsidian_manage_structure/obsidian_manage_structure_tool.py`

**Structure:** Follow `obsidian_manage_notes_tool.py` exactly:

1. `register_obsidian_manage_structure_tool(toolset)` wrapper function
2. `@toolset.tool` decorated async function with:
   - `operation: Literal["create_folder", "rename", "delete_folder", "move", "list_structure"]`
   - `path: str = ""`
   - `new_path: str | None = None`
   - `force: bool = False`
   - `bulk: bool = False`
   - `items: list[BulkStructureItem] | None = None`
3. Comprehensive docstring with "Use this when" / "Do NOT use this for" / Args / Examples
4. If/elif dispatch for each operation with parameter validation
5. VaultError exception handling returning `StructureOperationResult(success=False, ...)`
6. `_handle_bulk_operation()` helper for bulk move/rename

**Key docstring guidance:**
- Use for: folder creation, renaming files/folders, moving, deleting folders, viewing structure
- Do NOT use for: reading notes, creating notes, searching, deleting individual notes

**VALIDATE:** `uv run mypy app/features/obsidian_manage_structure/`

---

### Task 12: UPDATE Tool Registry

**File:** `app/core/agents/tool_registry.py`

Add import and call `register_obsidian_manage_structure_tool(toolset)` in `create_obsidian_toolset()`.

**VALIDATE:** `uv run python -c "from app.core.agents.tool_registry import create_obsidian_toolset; ts = create_obsidian_toolset(); print('obsidian_manage_structure' in ts.tools)"`

---

### Task 13: UPDATE SYSTEM_PROMPT

**File:** `app/core/agents/base.py`

Add to SYSTEM_PROMPT after obsidian_manage_notes section:
```
### obsidian_manage_structure
Manage vault folder structure. Operations:
- create_folder: Create new folder (creates parents as needed)
- rename: Rename a file or folder (requires new_path)
- delete_folder: Delete a folder (use force=True for non-empty)
- move: Move file/folder to new location (requires new_path)
- list_structure: Get folder tree hierarchy

Supports bulk operations for move/rename with bulk=True and items parameter.
```

Update logger to include `"obsidian_manage_structure"` in tools list.

**VALIDATE:** `uv run python -c "from app.core.agents.base import SYSTEM_PROMPT; print('obsidian_manage_structure' in SYSTEM_PROMPT)"`

---

### Task 14: CREATE Tool Tests

**File:** `app/features/obsidian_manage_structure/tests/test_obsidian_manage_structure_tool.py`

Follow `test_obsidian_manage_notes_tool.py` pattern exactly:

**Fixtures:** `deps`, `toolset`, `mock_ctx`

**Test Classes:**
- `TestParameterValidation`: path required for create/delete, new_path required for rename/move
- `TestOperationSuccess`: mock VaultManager, verify success=True for each operation
- `TestErrorHandling`: mock exceptions, verify success=False with message
- `TestBulkOperations`: bulk move/rename success, partial failure, unsupported operation error

**Mocking pattern:**
```python
with patch("app.features.obsidian_manage_structure.obsidian_manage_structure_tool.VaultManager") as MockVault:
    MockVault.return_value.method = AsyncMock(return_value=mock_result)
    result = await tool_fn(mock_ctx, operation="...", ...)
```

**VALIDATE:** `uv run pytest app/features/obsidian_manage_structure/tests/ -v --tb=short`

---

## VALIDATION COMMANDS

Run all in sequence:

```bash
# Syntax & Style
uv run ruff check .
uv run ruff format --check .

# Type Checking
uv run mypy app/
uv run pyright app/

# Tests
uv run pytest -v

# Manual Test (after starting server)
uv run uvicorn app.main:app --reload --port 8123
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jasque","messages":[{"role":"user","content":"List the folder structure of my vault"}]}'
```

---

## ACCEPTANCE CRITERIA

- [ ] All 5 operations functional
- [ ] Bulk operations work for move/rename
- [ ] All validation commands pass (ruff, mypy, pyright, pytest)
- [ ] ~30 new tests passing
- [ ] Manual test with Obsidian Copilot succeeds

---

## COMPLETION CHECKLIST

- [ ] Tasks 1-2: Exceptions + FolderNode added
- [ ] Tasks 3-7: VaultManager methods implemented
- [ ] Task 8: VaultManager tests added
- [ ] Tasks 9-11: Feature slice created
- [ ] Tasks 12-13: Registry + SYSTEM_PROMPT updated
- [ ] Task 14: Tool tests added
- [ ] All validation passes

---

## NOTES

- Single filesystem (Docker volume) - no cross-device handling needed
- `force=True` uses `shutil.rmtree` via `asyncio.to_thread`
- No wikilink updates on rename/move (MVP limitation)
- Recursive delete is destructive - requires explicit `force=True`
