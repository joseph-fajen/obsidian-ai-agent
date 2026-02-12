# find_by_name Operation - Test Evaluation

**Date:** 2026-02-12
**Feature:** `find_by_name` operation in `obsidian_query_vault` tool
**Commit:** `2a60316`

---

## Summary

The `find_by_name` operation was implemented to resolve wikilink-style queries (e.g., `[[Note Name]]`) by searching filenames and frontmatter titles. Initial testing revealed 3/5 test cases passing, with 2 failures due to normalization gaps.

---

## Test Results

### Test 1: Exact match with spaces
**Query:** "Find the note called GUIDE prompt method"

**Expected:** `GUIDE prompt method.md`
**Actual:** ✅ Found `GUIDE prompt method.md` as primary result
**Status:** **PASS**

**Notes:** Also returned a copilot conversation archive. Jasque correctly distinguished the main note from the conversation.

---

### Test 2: Case insensitivity + nested directory
**Query:** "Find career reset plan" (all lowercase)

**Expected:** `Career/Career Reset 2026/Career Reset Plan.md`
**Actual:** ✅ Found correct note as primary result
**Status:** **PASS**

**Notes:** Case insensitivity worked. Also mentioned copilot conversations from January.

---

### Test 3: Normalized matching (underscore handling)
**Query:** "find 040 Linux Education"

**Expected:** `_040 Linux Education.md`
**Actual:** ❌ Did NOT find the target note
**Status:** **FAIL**

**Results returned:**
- `copilot/copilot-conversations/find_040_Linux_Education@20260212_144738.md`
- `_000 Home.md` (mentions at line 75)
- `CLAUDE.md` (mentions at line 16)

**Root Cause:** Leading underscore normalization issue
- Query `040 Linux Education` normalized → `"040 linux education"`
- Filename `_040 Linux Education` normalized → `" 040 linux education"` (leading space)
- The leading space from the underscore conversion prevents matching

---

### Test 4: Partial match with special characters
**Query:** "Find Dr Mary Fu"

**Expected:** `Personal/Health/Primary Care Physician - Dr. Mary Fu.md`
**Actual:** ❌ Did NOT find the target note
**Status:** **FAIL**

**Results returned:**
- Only `copilot/copilot-conversations/Find_Dr_Mary_Fu@20260212_144853.md`

**Root Cause:** Punctuation not normalized
- Query `Dr Mary Fu` normalized → `"dr mary fu"`
- Filename portion `Dr. Mary Fu` normalized → `"dr. mary fu"`
- The period in "Dr." prevents substring match

---

### Test 5: Frontmatter title match (differs from filename)
**Query:** "Find Interesting IOG Links"

**Expected:** `_005 Interesting IOG Links to be aware of.md`
**Actual:** ✅ Found correct note via frontmatter title match
**Status:** **PASS**

**Notes:** Correctly displayed "(title: 'Interesting IOG Links')" indicating frontmatter match. Also found a copilot conversation reference.

---

## Issues Identified

### Issue 1: Leading Underscore Normalization

**Severity:** High
**Affected:** Notes with leading underscores (common Obsidian pattern for system/index notes)

The `_normalize_name` function converts underscores to spaces, but this creates a leading space for files like `_040 Linux Education.md`. The query without the leading underscore won't match.

**Current behavior:**
```python
def _normalize_name(self, name: str) -> str:
    return name.casefold().replace("-", " ").replace("_", " ")
```

**Fix:** Strip leading/trailing whitespace after normalization, or strip leading underscores before normalization.

---

### Issue 2: Punctuation Not Normalized

**Severity:** Medium
**Affected:** Notes with punctuation in names (Dr., Mr., Inc., etc.)

Periods and other punctuation are not removed during normalization, causing substring matches to fail.

**Example:**
- "Dr Mary Fu" should find "Dr. Mary Fu" but the period blocks the match

**Fix:** Remove common punctuation (periods, commas) during normalization.

---

### Issue 3: Copilot Conversations Polluting Results

**Severity:** Medium (UX issue)
**Affected:** All queries

The `copilot/copilot-conversations/` folder stores conversation logs named after query topics. These appear in search results, adding noise when users are looking for their "real" notes.

**Examples from tests:**
- `copilot/copilot-conversations/find_040_Linux_Education@20260212_144738.md`
- `copilot/copilot-conversations/Find_Dr_Mary_Fu@20260212_144853.md`

**User impact:** Clutters results with meta-content rather than actual vault notes.

---

## Recommended Improvements

### Option A: Enhance `_normalize_name` (Quick Fix)

Update the normalization function to:
1. Strip leading underscores before conversion
2. Remove punctuation (periods, commas)
3. Strip leading/trailing whitespace

```python
def _normalize_name(self, name: str) -> str:
    """Normalize a name for comparison."""
    # Strip leading underscores (common Obsidian pattern)
    name = name.lstrip("_")
    # Remove punctuation
    name = name.replace(".", "").replace(",", "")
    # Normalize case and separators
    return name.casefold().replace("-", " ").replace("_", " ").strip()
```

**Pros:** Simple, fixes Test 3 and Test 4
**Cons:** Doesn't address copilot conversations issue

---

### Option B: Add Folder Exclusion

Add ability to exclude folders from searches:
1. Add `exclude_folders` parameter to `find_by_name`
2. Or configure via `_jasque/preferences.md`
3. Default exclude `copilot/` folder

**Implementation options:**
- Parameter: `exclude_folders: list[str] = ["copilot"]`
- Preferences: `search_exclude_folders: ["copilot", ".obsidian"]`

**Pros:** Reduces noise in all search operations
**Cons:** More complex, affects multiple tools

---

### Option C: Both (Recommended)

Implement both improvements:
1. Fix normalization for immediate correctness
2. Add folder exclusion for better UX

**Phased approach:**
- Phase 1: Fix `_normalize_name` (addresses Test 3, Test 4)
- Phase 2: Add configurable folder exclusion (addresses copilot noise)

---

## Files to Modify

### Phase 1 (Normalization fix)
- `app/shared/vault/manager.py` - Update `_normalize_name` method
- `app/shared/vault/tests/test_manager.py` - Add tests for edge cases

### Phase 2 (Folder exclusion)
- `app/shared/vault/manager.py` - Add exclusion logic to `find_by_name` and other query methods
- `app/features/chat/preferences.py` - Add `search_exclude_folders` schema
- `app/shared/vault/tests/test_manager.py` - Add exclusion tests

---

## Test Cases to Add

```python
# Test 3 fix - leading underscore
async def test_find_by_name_leading_underscore(tmp_path):
    (tmp_path / "_040 Linux Education.md").write_text("# Linux\n")
    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("040 Linux Education")
    assert len(results) >= 1
    assert results[0].path == "_040 Linux Education.md"

# Test 4 fix - punctuation
async def test_find_by_name_punctuation(tmp_path):
    (tmp_path / "Dr. Mary Fu.md").write_text("# Doctor\n")
    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("Dr Mary Fu")
    assert len(results) >= 1
    assert results[0].path == "Dr. Mary Fu.md"

# Folder exclusion
async def test_find_by_name_excludes_folders(tmp_path):
    (tmp_path / "copilot").mkdir()
    (tmp_path / "copilot" / "test.md").write_text("# Copilot\n")
    (tmp_path / "test.md").write_text("# Real Note\n")
    manager = VaultManager(tmp_path)
    results = await manager.find_by_name("test", exclude_folders=["copilot"])
    assert len(results) == 1
    assert results[0].path == "test.md"
```

---

## Next Steps

1. Review this evaluation document
2. Decide on implementation approach (Option A, B, or C)
3. Create implementation plan if needed
4. Execute fixes and re-run tests

---

*Document created: 2026-02-12*
*Related plan: `.agents/plans/add-find-by-name-operation.md`*
