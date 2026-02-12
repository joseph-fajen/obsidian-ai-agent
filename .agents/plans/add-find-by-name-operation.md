# Feature: Add `find_by_name` Operation to `obsidian_query_vault`

## Problem Statement

When Jasque searches for notes referenced by wikilinks (e.g., `[[Proposed Tagging System]]`), the `search_text` operation returns content matches that bury the actual target note. Copilot conversation logs that *mention* the note appear before the note itself.

## Solution Statement

Add a `find_by_name` operation that searches by **filename and frontmatter title** instead of content. This enables direct resolution of wikilink references.

## Feature Metadata

- **Type**: Enhancement (new operation in existing tool)
- **Complexity**: Low-Medium
- **Systems Affected**: `obsidian_query_vault` tool, `VaultManager`
- **Dependencies**: None (uses existing libraries)

---

## CONTEXT REFERENCES

### Files to Read Before Implementing

| File | Lines | Why |
|------|-------|-----|
| `app/shared/vault/manager.py` | 683-711 | `find_by_tag()` - template pattern for new method |
| `app/shared/vault/manager.py` | 162-186 | `_get_note_title()` - title extraction logic |
| `app/shared/vault/manager.py` | 713-770 | `_find_by_tag_directory()` - recursive traversal pattern |
| `app/features/obsidian_query_vault/obsidian_query_vault_tool.py` | 29-46 | Tool signature and Literal operations |
| `app/features/obsidian_query_vault/obsidian_query_vault_tool.py` | 169-189 | `find_by_tag` branch - template for new branch |
| `app/features/obsidian_query_vault/tests/test_obsidian_query_vault_tool.py` | 164-199 | Test pattern for operations |
| `.agents/reference/adding_tools_guide.md` | All | Tool docstring requirements |

### New Files

None - all changes are additions to existing files.

### Patterns to Follow

**Naming**: `find_by_name` (matches `find_by_tag` pattern)

**Logging**: `vault.query.find_by_name_completed` with query, path, count

**Error message format**:
```python
"Query parameter is required for find_by_name operation. Example: query='Meeting Notes'"
```

---

## IMPLEMENTATION PLAN

### Phase 1: VaultManager Method

Add `find_by_name()` method to `app/shared/vault/manager.py`.

**Behavior**:
- Strip `.md` suffix from query if present
- Use `casefold()` for case-insensitive comparison
- Normalize: treat spaces, hyphens, underscores as equivalent
- Match against filename stem first, then frontmatter title
- Sort results: exact matches first, then contains matches, then by path length

**Signature**:
```python
async def find_by_name(
    self,
    query: str,
    path: str | None = None,
    limit: int = 50,
) -> list[NoteInfo]:
```

### Phase 2: Tool Operation Branch

Add `find_by_name` operation to `obsidian_query_vault_tool.py`.

**Changes**:
1. Add `"find_by_name"` to the `Literal` type
2. Add operation branch after `find_by_tag`
3. Update docstring with new operation
4. Update error message listing valid operations

### Phase 3: Tests

Add tests mirroring `find_by_tag` test patterns.

---

## STEP-BY-STEP TASKS

### Task 1: ADD `find_by_name` method to VaultManager

**File**: `app/shared/vault/manager.py`

**Location**: After `find_by_tag()` method (around line 770)

**Implementation**:
```python
async def find_by_name(
    self,
    query: str,
    path: str | None = None,
    limit: int = 50,
) -> list[NoteInfo]:
    """Find notes by filename or frontmatter title.

    Args:
        query: Note name to search for (case-insensitive, normalized).
               The .md extension is stripped if present.
        path: Optional folder to scope the search.
        limit: Maximum number of results.

    Returns:
        List of NoteInfo objects, sorted by match quality:
        1. Exact filename matches (shortest path first)
        2. Filename contains matches (shortest path first)
        3. Frontmatter title matches (shortest path first)
    """
```

**PATTERN**: Mirror `find_by_tag()` structure at line 683
**IMPORTS**: None needed (reuses existing)
**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k find_by_name`

### Task 2: ADD helper method for name normalization

**File**: `app/shared/vault/manager.py`

**Location**: After `_is_hidden()` method (around line 160)

**Implementation**:
```python
def _normalize_name(self, name: str) -> str:
    """Normalize a name for comparison (lowercase, spaces/hyphens/underscores equivalent)."""
    return name.casefold().replace("-", " ").replace("_", " ")
```

**VALIDATE**: Method is tested via `find_by_name` tests

### Task 3: UPDATE tool Literal type

**File**: `app/features/obsidian_query_vault/obsidian_query_vault_tool.py`

**Location**: Line 31-39

**Change**: Add `"find_by_name"` to the Literal type

**VALIDATE**: `uv run mypy app/features/obsidian_query_vault/`

### Task 4: ADD operation branch for find_by_name

**File**: `app/features/obsidian_query_vault/obsidian_query_vault_tool.py`

**Location**: After `find_by_tag` branch (around line 189)

**Implementation**: Mirror `find_by_tag` branch pattern

**VALIDATE**: `uv run pytest app/features/obsidian_query_vault/tests/ -v -k find_by_name`

### Task 5: UPDATE tool docstring

**File**: `app/features/obsidian_query_vault/obsidian_query_vault_tool.py`

**Changes**:
1. Add `find_by_name` to "Use this when" section
2. Add to Args operation descriptions
3. Add example usage
4. Update valid operations in error message (line 271)

**VALIDATE**: Read docstring, verify completeness per adding_tools_guide.md

### Task 6: ADD VaultManager tests

**File**: `app/shared/vault/tests/test_manager.py`

**Tests to add**:
- `test_find_by_name_exact_match` - finds note by exact filename
- `test_find_by_name_case_insensitive` - "TEST NOTE" finds "Test Note"
- `test_find_by_name_normalized` - "my-note" finds "my_note" and "my note"
- `test_find_by_name_frontmatter_title` - matches frontmatter title field
- `test_find_by_name_strips_md_extension` - query "Note.md" finds "Note"
- `test_find_by_name_ordering` - exact matches before contains matches
- `test_find_by_name_in_folder` - respects path parameter

**VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v -k find_by_name`

### Task 7: ADD tool tests

**File**: `app/features/obsidian_query_vault/tests/test_obsidian_query_vault_tool.py`

**Tests to add**:
- `test_find_by_name_requires_query` - returns error without query
- `test_find_by_name_returns_results` - mocked VaultManager returns results

**PATTERN**: Mirror `test_find_by_tag_*` tests
**VALIDATE**: `uv run pytest app/features/obsidian_query_vault/tests/ -v`

---

## VALIDATION COMMANDS

```bash
# Level 1: Linting
uv run ruff check app/shared/vault/manager.py app/features/obsidian_query_vault/

# Level 2: Type checking
uv run mypy app/shared/vault/ app/features/obsidian_query_vault/
uv run pyright app/shared/vault/ app/features/obsidian_query_vault/

# Level 3: Unit tests
uv run pytest app/shared/vault/tests/test_manager.py -v -k find_by_name
uv run pytest app/features/obsidian_query_vault/tests/ -v -k find_by_name

# Level 4: Full test suite
uv run pytest -v

# Level 5: Manual validation (with server running)
# In Obsidian Copilot, ask: "Find the note called Proposed Tagging System"
```

---

## ACCEPTANCE CRITERIA

- [ ] `find_by_name` operation added to `obsidian_query_vault` tool
- [ ] Case-insensitive matching works ("TEST" finds "test")
- [ ] Normalized matching works ("my-note" finds "my_note")
- [ ] Frontmatter title matching works
- [ ] Results sorted by match quality (exact > contains > title)
- [ ] `.md` extension stripped from query
- [ ] All validation commands pass
- [ ] Tool docstring follows adding_tools_guide.md patterns

---

## NOTES

**Deferred**: Alias support (frontmatter `aliases` field) - can be added later if needed.

**Performance**: For very large vaults (10k+ notes), consider adding caching in a future iteration.
