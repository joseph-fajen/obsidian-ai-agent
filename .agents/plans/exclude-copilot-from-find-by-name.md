# Feature: Exclude Copilot Folder from find_by_name

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

When using the `find_by_name` operation to resolve wikilinks (e.g., `[[Marlowe]]`), Obsidian Copilot conversation logs from the `copilot/` folder appear in results, adding noise to what should be focused name-based lookups. This enhancement excludes the `copilot` folder specifically from `find_by_name` results while preserving its inclusion in `search_text` where finding past conversations is valuable.

## User Story

As a Jasque user
I want find_by_name to exclude auto-generated copilot conversation logs
So that wikilink resolution returns actual vault notes without noise from chat history

## Problem Statement

The `find_by_name` operation returns copilot conversation logs alongside actual vault notes. While the prioritization correctly shows main notes first, conversation logs add noise to what should be a focused name-based lookup for wikilink resolution.

## Solution Statement

Extend the existing `_is_excluded()` method with an optional `operation_exclusions` parameter that accepts a set of additional folders to exclude for specific operations. Create a module-level constant `NAME_SEARCH_EXCLUSIONS` containing `{"copilot"}` and pass it only from `_find_by_name_directory()`.

## Feature Metadata

**Feature Type**: Enhancement (behavior refinement)
**Estimated Complexity**: Low
**Primary Systems Affected**: `VaultManager._is_excluded()`, `VaultManager._find_by_name_directory()`
**Dependencies**: None

---

## CONTEXT REFERENCES

### Relevant Codebase Files - READ THESE BEFORE IMPLEMENTING!

| File | Lines | Why |
|------|-------|-----|
| `app/shared/vault/manager.py` | 38-40 | Module-level constants pattern (regex patterns) |
| `app/shared/vault/manager.py` | 169-194 | `_is_excluded()` - method to extend |
| `app/shared/vault/manager.py` | 916-926 | `_find_by_name_directory()` - call site to modify |
| `app/shared/vault/tests/test_manager.py` | 1079-1140 | Existing folder exclusion tests - pattern to follow |

### New Files to Create

None - all changes are modifications to existing files.

### Patterns to Follow

**Module-level Constants** (from `manager.py` lines 38-40):
```python
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
TASK_PATTERN = re.compile(r"^(\s*)-\s*\[([ xX])\]\s*(.+)$", re.MULTILINE)
TAG_PATTERN = re.compile(r"#([a-zA-Z][a-zA-Z0-9_/-]*)")
```
New constant should be placed after these, with similar comment style.

**Exclusion Logic** (from `_is_excluded()` lines 185-194):
```python
# _jasque is ALWAYS excluded (system folder)
if first_folder == "_jasque":
    return True

# If user provided explicit path, skip user-configured exclusions
if explicit_path:
    return False

# Check user-configured exclusions
return first_folder in self._exclude_folders
```
Operation exclusions should be checked after `_jasque` but before explicit_path bypass.

**Test Pattern** (from `test_manager.py` lines 1083-1093):
```python
async def test_find_by_name_excludes_jasque_folder(tmp_path: Path):
    """_jasque folder is always excluded from search."""
    (tmp_path / "_jasque").mkdir()
    (tmp_path / "_jasque" / "preferences.md").write_text("# Prefs")
    (tmp_path / "preferences.md").write_text("# Real Prefs")

    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("preferences")

    assert len(results) == 1
    assert results[0].path == "preferences.md"
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Add the module-level constant defining folders excluded from name searches.

### Phase 2: Core Implementation

Extend `_is_excluded()` with the new optional parameter and update its logic.

### Phase 3: Integration

Update `_find_by_name_directory()` to pass the exclusions constant.

### Phase 4: Testing & Validation

Add tests verifying:
1. `find_by_name` excludes `copilot` folder
2. `search_text` still includes `copilot` folder

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: ADD module-level constant for name search exclusions

**File**: `app/shared/vault/manager.py`

**Location**: After `TAG_PATTERN` (line 41), before the dataclass section

**IMPLEMENT**: Add constant defining folders excluded from name-based searches

```python
# Folders excluded from name-based searches (find_by_name)
# These contain auto-generated content, not user-created notes
NAME_SEARCH_EXCLUSIONS: set[str] = {"copilot"}
```

**PATTERN**: Follow existing constant style (lines 38-40)
**VALIDATE**: `uv run ruff check app/shared/vault/manager.py`

---

### Task 2: UPDATE `_is_excluded()` signature

**File**: `app/shared/vault/manager.py`

**Location**: Line 169

**IMPLEMENT**: Add optional `operation_exclusions` parameter

Change from:
```python
def _is_excluded(self, rel_path: str, explicit_path: str | None = None) -> bool:
```

To:
```python
def _is_excluded(
    self,
    rel_path: str,
    explicit_path: str | None = None,
    operation_exclusions: set[str] | None = None,
) -> bool:
```

**PATTERN**: Multi-line signature style matches other methods in file
**IMPORTS**: None needed - `set` is builtin
**VALIDATE**: `uv run mypy app/shared/vault/manager.py`

---

### Task 3: UPDATE `_is_excluded()` docstring

**File**: `app/shared/vault/manager.py`

**Location**: Lines 170-178

**IMPLEMENT**: Update docstring to document new parameter

```python
"""Check if path should be excluded from search.

Args:
    rel_path: Relative path from vault root.
    explicit_path: If set, user-configured exclusions are bypassed
        (but _jasque is still excluded).
    operation_exclusions: Additional folders to exclude for specific
        operations (e.g., copilot for find_by_name).

Returns:
    True if path should be excluded from results.
"""
```

**VALIDATE**: `uv run ruff check app/shared/vault/manager.py`

---

### Task 4: UPDATE `_is_excluded()` logic

**File**: `app/shared/vault/manager.py`

**Location**: After the `_jasque` check (line 187), before `explicit_path` check

**IMPLEMENT**: Add operation-specific exclusion check

Insert after `if first_folder == "_jasque": return True`:
```python
# Operation-specific exclusions (e.g., copilot for find_by_name)
if operation_exclusions and first_folder in operation_exclusions:
    return True
```

The full logic block should now be:
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

**GOTCHA**: Operation exclusions are NOT bypassed by explicit_path - this is intentional (copilot should always be excluded from find_by_name, even if user searches within copilot folder)
**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "excluded" --no-header -q`

---

### Task 5: UPDATE `_find_by_name_directory()` to pass exclusions

**File**: `app/shared/vault/manager.py`

**Location**: Line 924 (the `_is_excluded()` call)

**IMPLEMENT**: Pass `NAME_SEARCH_EXCLUSIONS` to the exclusion check

Change from:
```python
if self._is_excluded(rel_path, explicit_path=explicit_path):
```

To:
```python
if self._is_excluded(
    rel_path,
    explicit_path=explicit_path,
    operation_exclusions=NAME_SEARCH_EXCLUSIONS,
):
```

**PATTERN**: Multi-line call style for readability
**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "find_by_name" --no-header -q`

---

### Task 6: ADD test for copilot exclusion from find_by_name

**File**: `app/shared/vault/tests/test_manager.py`

**Location**: After `test_find_by_name_explicit_path_cannot_bypass_jasque` (around line 1128)

**IMPLEMENT**: Add test verifying copilot folder is excluded

```python
async def test_find_by_name_excludes_copilot_folder(tmp_path: Path):
    """find_by_name excludes copilot conversation logs."""
    # Create a real note
    (tmp_path / "Project Notes.md").write_text("# Project Notes\n\nContent here.")

    # Create copilot conversation with matching name pattern
    copilot_dir = tmp_path / "copilot" / "copilot-conversations"
    copilot_dir.mkdir(parents=True)
    (copilot_dir / "Project_Notes_conversation.md").write_text("# Chat about Project Notes")

    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("Project Notes")

    # Should find the real note, not the copilot conversation
    assert len(results) == 1
    assert results[0].path == "Project Notes.md"
    assert "copilot" not in results[0].path
```

**PATTERN**: Mirror `test_find_by_name_excludes_jasque_folder` structure (lines 1083-1093)
**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "copilot" --no-header -q`

---

### Task 7: ADD test confirming search_text still includes copilot

**File**: `app/shared/vault/tests/test_manager.py`

**Location**: After the new copilot exclusion test

**IMPLEMENT**: Add test verifying search_text still finds copilot content

```python
async def test_search_text_includes_copilot_folder(tmp_path: Path):
    """search_text should still include copilot conversations (not excluded)."""
    # Create copilot conversation
    copilot_dir = tmp_path / "copilot" / "copilot-conversations"
    copilot_dir.mkdir(parents=True)
    (copilot_dir / "chat_about_testing.md").write_text("# Discussion about unit testing")

    manager = VaultManager(tmp_path)
    results = await manager.search_text("unit testing")

    # Should find content in copilot folder
    assert len(results) == 1
    assert "copilot" in results[0].path
```

**PATTERN**: Similar structure to `test_search_text_excludes_folders` (lines 1131-1140)
**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k "search_text_includes" --no-header -q`

---

## TESTING STRATEGY

### Unit Tests

Two new tests added:
1. `test_find_by_name_excludes_copilot_folder` - Verifies copilot excluded from name search
2. `test_search_text_includes_copilot_folder` - Verifies copilot NOT excluded from text search

### Regression Tests

All existing tests must pass - the change is additive and should not affect other operations.

### Edge Cases

- Copilot folder with nested structure (`copilot/copilot-conversations/`)
- Notes with "copilot" in the name (should still be found)
- Empty copilot folder (no crash)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check app/shared/vault/manager.py
uv run ruff check app/shared/vault/tests/test_manager.py
```

### Level 2: Type Checking

```bash
uv run mypy app/shared/vault/manager.py
uv run pyright app/shared/vault/manager.py
```

### Level 3: Unit Tests (Targeted)

```bash
# New tests
uv run pytest app/shared/vault/tests/test_manager.py -v -k "copilot"

# Related tests
uv run pytest app/shared/vault/tests/test_manager.py -v -k "find_by_name"
uv run pytest app/shared/vault/tests/test_manager.py -v -k "excluded"
```

### Level 4: Full Test Suite

```bash
uv run pytest -v
```

### Level 5: Manual Validation

Start the server and test via Obsidian Copilot:

```bash
uv run uvicorn app.main:app --reload --port 8123
```

1. Ask: "Find the note called [name that exists in copilot]"
   - Expected: No copilot conversations in results
2. Ask: "Search for [term that exists in copilot conversation]"
   - Expected: Copilot conversations MAY appear (search_text unchanged)

---

## ACCEPTANCE CRITERIA

- [ ] `find_by_name` excludes `copilot` folder from results
- [ ] `search_text` continues to include `copilot` folder
- [ ] Other operations unchanged (`find_by_tag`, `list_tasks`, `get_backlinks`, etc.)
- [ ] Explicit path parameter behavior unchanged for user-configured exclusions
- [ ] All existing tests pass (314 tests)
- [ ] New tests cover the behavior change (2 new tests)
- [ ] Type checking passes (mypy + pyright)
- [ ] Linting passes (ruff)

---

## COMPLETION CHECKLIST

- [ ] All 7 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (316 tests expected)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

**Design Decision**: Operation exclusions are checked BEFORE the `explicit_path` bypass. This means `copilot` is always excluded from `find_by_name`, even if a user explicitly searches within the copilot folder. This is intentional - copilot conversations should never appear in wikilink resolution results.

**Future Consideration**: If users want to customize which folders are excluded from name searches, this could be exposed via the preferences system (`_jasque/preferences.md`). For now, hardcoding `copilot` is sufficient.

**Folder Variations**: The exclusion checks `first_folder`, so both `copilot/` at root and `copilot/copilot-conversations/` (common Obsidian Copilot structure) are covered by excluding `copilot`.
