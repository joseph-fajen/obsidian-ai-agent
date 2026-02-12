# Feature: Enhanced Search Normalization and Folder Exclusion

## Problem Statement

The `find_by_name` operation fails to find notes with leading underscores (`_040 Linux Education.md`) or punctuation (`Dr. Mary Fu.md`). Additionally, search results include noise from system folders (`copilot/`, `_jasque/`).

## Solution Statement

1. **Enhance `_normalize_name()`** to strip leading underscores, remove punctuation, and collapse whitespace
2. **Add configurable folder exclusion** with two-tier logic: `_jasque/` always excluded, user-configured folders excluded by default but bypassed with explicit path

## Feature Metadata

- **Type**: Enhancement
- **Complexity**: Medium
- **Systems Affected**: VaultManager, preferences schema, AgentDependencies, query tool
- **Dependencies**: None (uses existing libraries)

---

## CONTEXT REFERENCES

### Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `app/shared/vault/manager.py` | 162-164 | Update `_normalize_name()` |
| `app/shared/vault/manager.py` | 121-136 | Add `exclude_folders` to `__init__`, add `_is_excluded()` |
| `app/shared/vault/manager.py` | 828-895 | Update `_find_by_name_directory()` |
| `app/shared/vault/manager.py` | 624-685 | Update `_search_directory()` |
| `app/shared/vault/manager.py` | 717-770 | Update `_find_by_tag_directory()` |
| `app/shared/vault/manager.py` | 928-988 | Update `_find_backlinks()` |
| `app/shared/vault/manager.py` | 1062-1130 | Update `_find_tasks()` |
| `app/features/chat/preferences.py` | 28-34 | Add `search_exclude_folders` to `UserPreferences` |
| `app/features/chat/preferences.py` | 87-115 | Update `PREFERENCES_TEMPLATE` |
| `app/core/agents/types.py` | 10-14 | Add `exclude_folders` to `AgentDependencies` |
| `app/features/chat/openai_routes.py` | 67-76 | Wire exclusions from preferences to deps |
| `app/features/obsidian_query_vault/obsidian_query_vault_tool.py` | 146 | Pass exclusions to VaultManager |

### Patterns to Follow

**Existing hidden check** (`manager.py:158-160`):
```python
def _is_hidden(self, name: str) -> bool:
    return name.startswith(".")
```

**Existing recursive traversal pattern** - all `_*_directory()` methods have early exit on `_is_hidden()`.

---

## IMPLEMENTATION PLAN

### Phase 1: Normalization Fix

Update `_normalize_name()` to handle leading underscores and punctuation.

### Phase 2: Folder Exclusion Infrastructure

Add exclusion support to preferences schema, AgentDependencies, VaultManager constructor, and routing layer.

### Phase 3: Apply Exclusions

Update all recursive query methods to check `_is_excluded()`.

### Phase 4: Testing

Add tests for normalization edge cases and folder exclusion behavior.

---

## STEP-BY-STEP TASKS

### Task 1: UPDATE `_normalize_name()` method

**File**: `app/shared/vault/manager.py` (lines 162-164)

**Replace**:
```python
def _normalize_name(self, name: str) -> str:
    """Normalize a name for comparison (lowercase, spaces/hyphens/underscores equivalent)."""
    return name.casefold().replace("-", " ").replace("_", " ")
```

**With**:
```python
def _normalize_name(self, name: str) -> str:
    """Normalize a name for comparison.

    - Strips leading underscores (common Obsidian index note pattern)
    - Removes punctuation (. , ' ? !)
    - Normalizes case
    - Treats spaces/hyphens/underscores as equivalent
    - Collapses multiple spaces to single space
    """
    # Strip leading underscores
    name = name.lstrip("_")
    # Remove common punctuation
    for char in ".,?!'":
        name = name.replace(char, "")
    # Normalize case and separators
    normalized = name.casefold().replace("-", " ").replace("_", " ")
    # Collapse multiple spaces
    return " ".join(normalized.split())
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k find_by_name`

---

### Task 2: ADD `search_exclude_folders` to UserPreferences

**File**: `app/features/chat/preferences.py`

**After line 34** (after `response_style` field), add:
```python
    search_exclude_folders: list[str] = Field(
        default_factory=lambda: ["copilot"],
        description="Folders to exclude from search operations",
    )
```

**VALIDATE**: `uv run pytest app/features/chat/tests/test_preferences.py -v`

---

### Task 3: UPDATE PREFERENCES_TEMPLATE

**File**: `app/features/chat/preferences.py` (lines 87-115)

**Add after `response_style` section** (around line 105):
```yaml
# Folders to exclude from search results (default: ["copilot"])
# The _jasque folder is always excluded automatically
search_exclude_folders:
  - copilot
  # - templates  # Uncomment to also exclude templates folder
```

**VALIDATE**: `uv run pytest app/features/chat/tests/test_preferences.py::test_preferences_template_validates_as_schema -v`

---

### Task 4: ADD `exclude_folders` to AgentDependencies

**File**: `app/core/agents/types.py`

**Replace** `AgentDependencies` class:
```python
@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools via RunContext."""

    request_id: str = ""
    vault_path: Path = field(default_factory=lambda: Path("/vault"))
    exclude_folders: list[str] = field(default_factory=list)
```

**VALIDATE**: `uv run mypy app/core/agents/types.py`

---

### Task 5: UPDATE VaultManager constructor

**File**: `app/shared/vault/manager.py`

**Replace** `__init__` (lines 129-135):
```python
def __init__(
    self,
    vault_path: Path,
    exclude_folders: list[str] | None = None,
) -> None:
    """Initialize the VaultManager.

    Args:
        vault_path: Path to the Obsidian vault root.
        exclude_folders: Folders to exclude from search operations.
            Note: _jasque is always excluded regardless of this setting.
    """
    self.vault_path = vault_path.resolve()
    self._exclude_folders = set(exclude_folders or [])
```

**VALIDATE**: `uv run mypy app/shared/vault/manager.py`

---

### Task 6: ADD `_is_excluded()` method

**File**: `app/shared/vault/manager.py`

**After `_is_hidden()` method** (around line 160), add:
```python
def _is_excluded(self, rel_path: str, explicit_path: str | None = None) -> bool:
    """Check if path should be excluded from search.

    Args:
        rel_path: Relative path from vault root.
        explicit_path: If set, user-configured exclusions are bypassed
            (but _jasque is still excluded).

    Returns:
        True if path should be excluded from results.
    """
    parts = rel_path.split("/")
    if not parts or not parts[0]:
        return False
    first_folder = parts[0]

    # _jasque is ALWAYS excluded (system folder)
    if first_folder == "_jasque":
        return True

    # If user provided explicit path, skip user-configured exclusions
    if explicit_path:
        return False

    # Check user-configured exclusions
    return first_folder in self._exclude_folders
```

**VALIDATE**: `uv run mypy app/shared/vault/manager.py`

---

### Task 7: UPDATE openai_routes to wire exclusions

**File**: `app/features/chat/openai_routes.py`

**Replace** deps creation (lines 67-70):
```python
    # Extract exclusions from preferences
    exclude_folders: list[str] = []
    if preferences and preferences.structured.search_exclude_folders:
        exclude_folders = preferences.structured.search_exclude_folders

    deps = AgentDependencies(
        request_id=request_id,
        vault_path=Path(settings.obsidian_vault_path),
        exclude_folders=exclude_folders,
    )
```

**VALIDATE**: `uv run mypy app/features/chat/openai_routes.py`

---

### Task 8: UPDATE obsidian_query_vault tool

**File**: `app/features/obsidian_query_vault/obsidian_query_vault_tool.py`

**Replace** line 146:
```python
vault = VaultManager(ctx.deps.vault_path)
```

**With**:
```python
vault = VaultManager(ctx.deps.vault_path, exclude_folders=list(ctx.deps.exclude_folders))
```

**VALIDATE**: `uv run mypy app/features/obsidian_query_vault/`

---

### Task 9: UPDATE `_find_by_name_directory()` with exclusion

**File**: `app/shared/vault/manager.py`

**In `_find_by_name_directory()` method**, after the `_is_hidden()` check (around line 851), add:
```python
            if self._is_hidden(entry):
                continue

            # Check folder exclusion
            entry_rel = f"{rel_path}/{entry}".lstrip("/") if rel_path else entry
            if self._is_excluded(entry_rel, explicit_path=None):
                continue
```

**Note**: Also need to pass `path` parameter through to track explicit path. Update signature:
```python
async def _find_by_name_directory(
    self,
    path: Path,
    query_normalized: str,
    exact_matches: list[NoteInfo],
    contains_matches: list[NoteInfo],
    title_matches: list[NoteInfo],
    explicit_path: str | None = None,
) -> None:
```

And update the recursive call and initial call from `find_by_name()`.

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k find_by_name`

---

### Task 10: UPDATE `_search_directory()` with exclusion

**File**: `app/shared/vault/manager.py`

**In `_search_directory()` method**, add exclusion check after `_is_hidden()`:
```python
            if self._is_hidden(entry):
                continue

            rel_path = str((path / entry).relative_to(self.vault_path))
            if self._is_excluded(rel_path, explicit_path=self._current_explicit_path):
                continue
```

**Note**: Need to track explicit_path through the call chain. Update `search_text()` to store it temporarily.

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k search`

---

### Task 11: UPDATE `_find_by_tag_directory()` with exclusion

**File**: `app/shared/vault/manager.py`

**Same pattern as Task 10** - add exclusion check after `_is_hidden()`.

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k find_by_tag`

---

### Task 12: UPDATE `_find_backlinks()` with exclusion

**File**: `app/shared/vault/manager.py`

**Same pattern** - add exclusion check after `_is_hidden()`.

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k backlink`

---

### Task 13: UPDATE `_find_tasks()` with exclusion

**File**: `app/shared/vault/manager.py`

**Same pattern** - add exclusion check after `_is_hidden()`.

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k task`

---

### Task 14: ADD normalization edge case tests

**File**: `app/shared/vault/tests/test_manager.py`

**Add tests**:
```python
# After existing find_by_name tests

async def test_find_by_name_leading_underscore(tmp_path: Path):
    """Find note with leading underscore in filename."""
    (tmp_path / "_040 Linux Education.md").write_text("# Linux\n\nContent")
    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("040 Linux Education")
    assert len(results) >= 1
    assert results[0].path == "_040 Linux Education.md"


async def test_find_by_name_punctuation(tmp_path: Path):
    """Find note with punctuation in filename."""
    (tmp_path / "Dr. Mary Fu.md").write_text("# Doctor\n\nContent")
    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("Dr Mary Fu")
    assert len(results) >= 1
    assert results[0].path == "Dr. Mary Fu.md"


async def test_find_by_name_multiple_underscores(tmp_path: Path):
    """Find note with multiple leading underscores."""
    (tmp_path / "___test_note.md").write_text("# Test\n\nContent")
    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("test note")
    assert len(results) >= 1
    assert results[0].path == "___test_note.md"
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "leading_underscore or punctuation or multiple_underscore"`

---

### Task 15: ADD folder exclusion tests

**File**: `app/shared/vault/tests/test_manager.py`

**Add tests**:
```python
# Folder exclusion tests

async def test_find_by_name_excludes_jasque_folder(tmp_path: Path):
    """_jasque folder is always excluded from search."""
    (tmp_path / "_jasque").mkdir()
    (tmp_path / "_jasque" / "preferences.md").write_text("# Prefs")
    (tmp_path / "preferences.md").write_text("# Real Prefs")

    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("preferences")

    assert len(results) == 1
    assert results[0].path == "preferences.md"


async def test_find_by_name_excludes_configured_folder(tmp_path: Path):
    """User-configured folders are excluded."""
    (tmp_path / "copilot").mkdir()
    (tmp_path / "copilot" / "conversation.md").write_text("# Chat")
    (tmp_path / "notes.md").write_text("# Notes")

    manager = VaultManager(tmp_path, exclude_folders=["copilot"])
    results = await manager.find_by_name("conversation")

    assert len(results) == 0


async def test_find_by_name_explicit_path_bypasses_exclusion(tmp_path: Path):
    """Explicit path parameter bypasses user exclusions (but not _jasque)."""
    (tmp_path / "copilot").mkdir()
    (tmp_path / "copilot" / "conversation.md").write_text("# Chat")

    manager = VaultManager(tmp_path, exclude_folders=["copilot"])
    results = await manager.find_by_name("conversation", path="copilot")

    assert len(results) == 1
    assert results[0].path == "copilot/conversation.md"


async def test_search_text_excludes_folders(tmp_path: Path):
    """search_text respects folder exclusions."""
    (tmp_path / "copilot").mkdir()
    (tmp_path / "copilot" / "chat.md").write_text("meeting notes here")
    (tmp_path / "real.md").write_text("meeting notes here")

    manager = VaultManager(tmp_path, exclude_folders=["copilot"])
    results = await manager.search_text("meeting")

    assert len(results) == 1
    assert results[0].path == "real.md"
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "excludes"`

---

### Task 16: ADD preferences schema test for new field

**File**: `app/features/chat/tests/test_preferences.py`

**Add test**:
```python
def test_user_preferences_search_exclude_folders_default() -> None:
    """UserPreferences should have default exclusion for copilot folder."""
    prefs = UserPreferences()
    assert prefs.search_exclude_folders == ["copilot"]


def test_user_preferences_search_exclude_folders_custom() -> None:
    """UserPreferences should accept custom exclusion list."""
    prefs = UserPreferences(search_exclude_folders=["copilot", "templates"])
    assert "templates" in prefs.search_exclude_folders
```

**VALIDATE**: `uv run pytest app/features/chat/tests/test_preferences.py -v`

---

### Task 17: RUN full validation

```bash
# Level 1: Linting
uv run ruff check .

# Level 2: Type checking
uv run mypy app/
uv run pyright app/

# Level 3: All tests
uv run pytest -v

# Level 4: Verify test count increased
# Should be 314 + ~10 new tests = ~324 tests
```

---

## VALIDATION COMMANDS

```bash
# Quick validation during implementation
uv run ruff check app/shared/vault/manager.py app/features/chat/preferences.py
uv run mypy app/shared/vault/ app/features/chat/ app/core/agents/
uv run pytest app/shared/vault/tests/test_manager.py -v

# Full validation
uv run ruff check .
uv run mypy app/
uv run pyright app/
uv run pytest -v
```

---

## ACCEPTANCE CRITERIA

- [ ] `find_by_name("040 Linux Education")` finds `_040 Linux Education.md`
- [ ] `find_by_name("Dr Mary Fu")` finds `Dr. Mary Fu.md`
- [ ] `_jasque/` folder always excluded from all search operations
- [ ] `copilot/` folder excluded by default (configurable via preferences)
- [ ] Explicit `path` parameter bypasses user exclusions
- [ ] All 314+ tests pass
- [ ] No type errors (mypy, pyright)
- [ ] No linting errors (ruff)

---

## NOTES

**Design decisions:**
- Two-tier exclusion: `_jasque/` hardcoded, user folders configurable
- Explicit path bypasses user exclusions but not system exclusions
- ASCII punctuation only for MVP (CJK can be added later)
- Simple prefix matching (no glob patterns needed)

**Deferred:**
- CJK/Unicode punctuation handling
- Glob pattern support for exclusions
- Per-operation exclusion configuration
