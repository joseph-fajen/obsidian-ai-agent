# Enhancement: Exclude Copilot Conversations from `find_by_name`

## Problem Statement

When using `find_by_name` to resolve wikilinks (e.g., `[[Marlowe]]`), copilot conversation logs appear in results alongside actual vault notes. While the prioritization correctly shows main notes first, conversation logs add noise to what should be a focused name-based lookup.

## Solution Statement

Exclude the `copilot` folder from `find_by_name` results only, while preserving its inclusion in `search_text` (where finding past conversations is valuable).

## Feature Metadata

- **Type**: Enhancement (behavior refinement)
- **Complexity**: Low
- **Systems Affected**: `VaultManager.find_by_name()`, `VaultManager._is_excluded()`
- **Dependencies**: None
- **Risk**: Minimal - additive change to exclusion logic

---

## CONTEXT REFERENCES

### Files to Read Before Implementing

| File | Lines | Why |
|------|-------|-----|
| `app/shared/vault/manager.py` | 169-194 | `_is_excluded()` - current exclusion logic |
| `app/shared/vault/manager.py` | 835-890 | `find_by_name()` - method to modify |
| `app/shared/vault/manager.py` | 892-967 | `_find_by_name_directory()` - recursive helper |

### Patterns to Follow

The existing `_is_excluded()` method already handles:
- Hardcoded `_jasque` exclusion
- User-configured exclusions via `self._exclude_folders`
- `explicit_path` bypass for user-specified paths

We'll extend this pattern with operation-specific exclusions.

---

## DESIGN DECISION

**Approach**: Add an optional `operation_exclusions` parameter to `_is_excluded()` that accepts a set of additional folders to exclude for specific operations.

**Why this approach**:
- Keeps exclusion logic centralized in one method
- Easily extensible for future operation-specific exclusions
- Minimal code change
- Clear separation of concerns

**Alternative considered**: Hardcode `copilot` check in `_find_by_name_directory()` - rejected because it spreads exclusion logic across multiple places.

---

## IMPLEMENTATION PLAN

### Task 1: UPDATE `_is_excluded()` signature

**File**: `app/shared/vault/manager.py`

**Change**: Add optional `operation_exclusions` parameter

```python
def _is_excluded(
    self,
    rel_path: str,
    explicit_path: str | None = None,
    operation_exclusions: set[str] | None = None,
) -> bool:
```

**VALIDATE**: `uv run mypy app/shared/vault/manager.py`

### Task 2: UPDATE `_is_excluded()` logic

**File**: `app/shared/vault/manager.py`

**Change**: Check `operation_exclusions` after `_jasque` check, before user-configured exclusions

```python
# _jasque is ALWAYS excluded (system folder)
if first_folder == "_jasque":
    return True

# Operation-specific exclusions (e.g., copilot for find_by_name)
if operation_exclusions and first_folder in operation_exclusions:
    return True

# If user provided explicit path, skip user-configured exclusions
if explicit_path:
    return False

# Check user-configured exclusions
return first_folder in self._exclude_folders
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "excluded"`

### Task 3: ADD class constant for name search exclusions

**File**: `app/shared/vault/manager.py`

**Location**: After existing regex patterns (around line 41)

**Change**: Add constant defining folders excluded from name-based searches

```python
# Folders excluded from name-based searches (find_by_name)
# These contain auto-generated content, not user-created notes
NAME_SEARCH_EXCLUSIONS: set[str] = {"copilot"}
```

**VALIDATE**: `uv run ruff check app/shared/vault/manager.py`

### Task 4: UPDATE `_find_by_name_directory()` to pass exclusions

**File**: `app/shared/vault/manager.py`

**Change**: Pass `NAME_SEARCH_EXCLUSIONS` to `_is_excluded()` call

```python
# Check folder exclusion
rel_path = str(full_path.relative_to(self.vault_path))
if self._is_excluded(
    rel_path,
    explicit_path=explicit_path,
    operation_exclusions=NAME_SEARCH_EXCLUSIONS,
):
    continue
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "find_by_name"`

### Task 5: ADD unit test for copilot exclusion

**File**: `app/shared/vault/tests/test_manager.py`

**Test to add**:
```python
async def test_find_by_name_excludes_copilot_folder(
    tmp_path: Path,
    vault_manager: VaultManager,
) -> None:
    """find_by_name should exclude copilot conversation logs."""
    # Create a real note
    (tmp_path / "Project Notes.md").write_text("# Project Notes\n\nContent here.")

    # Create copilot conversation with same name pattern
    copilot_dir = tmp_path / "copilot" / "copilot-conversations"
    copilot_dir.mkdir(parents=True)
    (copilot_dir / "Project_Notes_conversation.md").write_text("# Chat about Project Notes")

    results = await vault_manager.find_by_name("Project Notes")

    # Should find the real note, not the copilot conversation
    assert len(results) == 1
    assert results[0].path == "Project Notes.md"
    assert "copilot" not in results[0].path
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "copilot"`

### Task 6: ADD unit test confirming search_text still includes copilot

**File**: `app/shared/vault/tests/test_manager.py`

**Test to add**:
```python
async def test_search_text_includes_copilot_folder(
    tmp_path: Path,
    vault_manager: VaultManager,
) -> None:
    """search_text should still include copilot conversations."""
    # Create copilot conversation
    copilot_dir = tmp_path / "copilot" / "copilot-conversations"
    copilot_dir.mkdir(parents=True)
    (copilot_dir / "chat_about_testing.md").write_text("# Discussion about unit testing")

    results = await vault_manager.search_text("unit testing")

    # Should find content in copilot folder
    assert len(results) == 1
    assert "copilot" in results[0].path
```

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "search_text"`

---

## VALIDATION COMMANDS

```bash
# Level 1: Linting
uv run ruff check app/shared/vault/manager.py

# Level 2: Type checking
uv run mypy app/shared/vault/manager.py
uv run pyright app/shared/vault/manager.py

# Level 3: Unit tests
uv run pytest app/shared/vault/tests/test_manager.py -v

# Level 4: Full test suite
uv run pytest -v

# Level 5: Manual validation
# In Obsidian Copilot, ask: "Find the note called Marlowe"
# Expected: No copilot conversations in results
# Then ask: "Search for Marlowe"
# Expected: Copilot conversations MAY appear (search_text behavior unchanged)
```

---

## ACCEPTANCE CRITERIA

- [ ] `find_by_name` excludes `copilot` folder from results
- [ ] `search_text` continues to include `copilot` folder
- [ ] Other operations unchanged (find_by_tag, list_tasks, etc.)
- [ ] Explicit path override still works (searching within copilot directly)
- [ ] All existing tests pass
- [ ] New tests cover the behavior change

---

## NOTES

**Future consideration**: If users want to customize which folders are excluded from name searches, this could be exposed via the preferences system (`_jasque/preferences.md`). For now, hardcoding `copilot` is sufficient.

**Folder variations**: The exclusion checks `first_folder`, so both `copilot/` and `copilot-conversations/` (if at root) would be excluded. The common Obsidian Copilot structure is `copilot/copilot-conversations/`, so excluding `copilot` covers this.
