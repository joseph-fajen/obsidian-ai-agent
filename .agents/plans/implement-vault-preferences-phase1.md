# Feature: Vault-Based Preferences (Memory Phase 1)

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Implement vault-based user preferences for Jasque. The agent reads user preferences from a markdown file (`_jasque/preferences.md`) in the vault and incorporates those preferences into each request's context. This enables users to customize Jasque's behavior (date formats, default folders, response style) by editing a file in their vault.

This is **Phase 1** of a 4-phase memory implementation. Future phases will add conversation logging (Phase 2), audit trail (Phase 3), and extracted facts (Phase 4). This implementation is designed to integrate smoothly with those future phases.

## User Story

As a Jasque user
I want to customize how Jasque behaves by editing a preferences file in my vault
So that the agent responds according to my personal workflows and conventions

## Problem Statement

Currently, Jasque has no way to learn user preferences. Users must repeatedly specify things like date formats, preferred folder locations, and response verbosity in every conversation. There's no persistence of user-specific configuration.

## Solution Statement

Add a preferences system where:
1. Jasque reads `_jasque/preferences.md` from the vault on each request
2. Preferences are parsed (YAML frontmatter + markdown body) and validated
3. Valid preferences are injected as context into the agent's prompt
4. Missing file = works normally with defaults (logs warning)
5. Malformed YAML = returns HTTP 400 with actionable error message
6. If `_jasque/` folder exists but file doesn't = auto-create template

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low-Medium
**Primary Systems Affected**: VaultManager, Chat routes, Agent context
**Dependencies**: `python-frontmatter` (already installed), `aiofiles` (already installed)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - READ THESE BEFORE IMPLEMENTING!

- `app/shared/vault/manager.py` (lines 355-390) - `read_note()` shows frontmatter parsing pattern
- `app/shared/vault/manager.py` (lines 217-230) - `_read_note_content()` async file read pattern
- `app/shared/vault/manager.py` (lines 232-245) - `_atomic_write()` for template creation
- `app/shared/vault/exceptions.py` (lines 1-50) - Exception hierarchy pattern
- `app/features/chat/openai_routes.py` (lines 58-83) - Request handling, where preferences inject
- `app/features/chat/openai_schemas.py` - Pydantic schema patterns with nested models
- `app/features/chat/streaming.py` (lines 58-85) - Message conversion pattern
- `app/core/agents/types.py` - AgentDependencies dataclass
- `app/shared/vault/tests/test_manager.py` (lines 1-150) - Test fixture patterns

### New Files to Create

- `app/features/chat/preferences.py` - Preferences Pydantic schemas and formatting utilities
- `app/features/chat/tests/test_preferences.py` - Unit tests for preferences loading

### Files to Modify

- `app/shared/vault/manager.py` - Add `load_preferences()` method
- `app/shared/vault/exceptions.py` - Add `PreferencesParseError` exception
- `app/shared/vault/__init__.py` - Export new exception
- `app/features/chat/openai_routes.py` - Integrate preferences loading and injection

### Relevant Documentation - READ BEFORE IMPLEMENTING!

- `.agents/reference/memory-implementation-guide.md` (lines 36-173) - Phase 1 specification
- `.agents/report/research-report-conversation-memory.md` - Background research

### Patterns to Follow

**Frontmatter Parsing Pattern** (from `manager.py:382-388`):
```python
try:
    post = frontmatter.loads(content)
    metadata = dict(post.metadata)
    body = post.content
except Exception:
    metadata = {}
    body = content
```

**Exception Pattern** (from `exceptions.py`):
```python
class PreferencesParseError(VaultError):
    """Exception raised when preferences file has invalid YAML."""
    pass
```

**Async File Read Pattern** (from `manager.py:217-230`):
```python
async def _read_note_content(self, path: Path) -> str | None:
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            return await f.read()
    except (UnicodeDecodeError, OSError):
        return None
```

**Test Fixture Pattern** (from `test_manager.py:22-70`):
```python
@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault with test structure."""
    (tmp_path / "_jasque").mkdir()
    prefs = tmp_path / "_jasque" / "preferences.md"
    prefs.write_text("""---
date_format: "YYYY-MM-DD"
---
Additional context here.
""")
    return tmp_path
```

**Logging Pattern** (from throughout codebase):
```python
logger.info("vault.preferences.loaded", has_preferences=True)
logger.warning("vault.preferences.not_found", path="_jasque/preferences.md")
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Schemas & Exception)

Create the preferences data models and exception type that will be used throughout the feature.

**Tasks:**
- Create Pydantic schemas for preferences (structured YAML + free-form markdown)
- Add `PreferencesParseError` to exception hierarchy
- Export new exception from `__init__.py`

### Phase 2: VaultManager Integration

Add the `load_preferences()` method to VaultManager that handles file reading, parsing, template creation, and error handling.

**Tasks:**
- Implement `load_preferences()` method in VaultManager
- Handle missing file (log warning, return None)
- Handle malformed YAML (raise PreferencesParseError with details)
- Auto-create template if folder exists but file doesn't

### Phase 3: Route Integration

Connect preferences loading to the chat completions endpoint and inject preferences into agent context.

**Tasks:**
- Load preferences at start of request in openai_routes.py
- Format preferences as context string
- Prepend to user message for agent consumption
- Handle PreferencesParseError with HTTP 400 response

### Phase 4: Testing & Validation

Comprehensive testing of all scenarios.

**Tasks:**
- Unit tests for preferences schemas
- Unit tests for VaultManager.load_preferences()
- Integration tests for route-level preferences injection
- Test error scenarios (missing file, malformed YAML)

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

---

### Task 1: CREATE `app/features/chat/preferences.py`

Create the preferences schemas and formatting utilities.

**IMPLEMENT:**
```python
"""User preferences loaded from vault.

This module provides:
- Pydantic schemas for structured preferences (YAML frontmatter)
- VaultPreferences container combining structured + free-form context
- Formatting utility to convert preferences to agent context string
"""

from pydantic import BaseModel, Field


class DefaultFolders(BaseModel):
    """Default folder locations for different note types."""

    meeting_notes: str | None = None
    daily_notes: str | None = None
    projects: str | None = None


class ResponseStyle(BaseModel):
    """Preferences for how Jasque responds."""

    verbosity: str = Field(default="concise", description="concise or detailed")
    use_bullet_points: bool = True
    include_timestamps: bool = False


class UserPreferences(BaseModel):
    """Structured preferences parsed from YAML frontmatter."""

    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    default_folders: DefaultFolders = Field(default_factory=DefaultFolders)
    response_style: ResponseStyle = Field(default_factory=ResponseStyle)


class VaultPreferences(BaseModel):
    """Complete preferences including free-form context."""

    structured: UserPreferences = Field(default_factory=UserPreferences)
    additional_context: str = ""  # Markdown body after frontmatter


def format_preferences_for_agent(preferences: VaultPreferences) -> str:
    """Format preferences as context string for agent prompt.

    Args:
        preferences: The loaded vault preferences.

    Returns:
        Formatted string to prepend to agent context.
    """
    lines: list[str] = ["## User Preferences", ""]

    s = preferences.structured

    # Date/time
    lines.append(f"- Date format: {s.date_format}")
    lines.append(f"- Time format: {s.time_format}")

    # Default folders (only if set)
    if s.default_folders.meeting_notes:
        lines.append(f"- Meeting notes folder: {s.default_folders.meeting_notes}")
    if s.default_folders.daily_notes:
        lines.append(f"- Daily notes folder: {s.default_folders.daily_notes}")
    if s.default_folders.projects:
        lines.append(f"- Projects folder: {s.default_folders.projects}")

    # Response style
    lines.append(f"- Response verbosity: {s.response_style.verbosity}")
    if s.response_style.use_bullet_points:
        lines.append("- Prefer bullet points in responses")
    if s.response_style.include_timestamps:
        lines.append("- Include timestamps in responses")

    # Additional context
    if preferences.additional_context.strip():
        lines.append("")
        lines.append("## Additional User Context")
        lines.append("")
        lines.append(preferences.additional_context.strip())

    return "\n".join(lines)


# Template for auto-creation
PREFERENCES_TEMPLATE = '''---
# Jasque User Preferences
# Edit this file to customize how Jasque behaves

# Date/time formatting preferences
date_format: "YYYY-MM-DD"
time_format: "HH:mm"

# Default locations for different note types
default_folders:
  meeting_notes: "Meetings/"
  daily_notes: "Daily/"
  projects: "Projects/"

# Response style preferences
response_style:
  verbosity: "concise"  # concise | detailed
  use_bullet_points: true
  include_timestamps: false
---

## Additional Context

Any free-form notes you want Jasque to know about. For example:

- I use the PARA method for organizing my vault
- Meeting notes should always include attendees and action items
- I prefer tasks formatted as `- [ ] task @due(date)`
'''
```

**IMPORTS:** `from pydantic import BaseModel, Field`
**PATTERN:** Follow `openai_schemas.py` nested model pattern
**VALIDATE:** `uv run python -c "from app.features.chat.preferences import VaultPreferences, format_preferences_for_agent; print('OK')"`

---

### Task 2: ADD `PreferencesParseError` to `app/shared/vault/exceptions.py`

Add the new exception for malformed preferences YAML.

**IMPLEMENT:** Add after `FolderNotEmptyError` class (after line 49):

```python
class PreferencesParseError(VaultError):
    """Exception raised when preferences file has invalid YAML syntax."""

    pass
```

**PATTERN:** Follow existing exception classes (lines 10-48)
**VALIDATE:** `uv run python -c "from app.shared.vault.exceptions import PreferencesParseError; print('OK')"`

---

### Task 3: UPDATE `app/shared/vault/__init__.py` exports

Export the new exception.

**IMPLEMENT:** Add `PreferencesParseError` to the imports and `__all__` list.

**PATTERN:** Check existing exports in the file
**VALIDATE:** `uv run python -c "from app.shared.vault import PreferencesParseError; print('OK')"`

---

### Task 4: ADD `load_preferences()` method to `app/shared/vault/manager.py`

Add the method to load and parse preferences from the vault.

**IMPLEMENT:** Add after the Structure Management Methods section (after line 1195):

```python
    # =========================================================================
    # Preferences Methods
    # =========================================================================

    async def load_preferences(self) -> "VaultPreferences | None":
        """Load user preferences from _jasque/preferences.md.

        Behavior:
        - If file exists: parse and return preferences
        - If folder exists but file doesn't: create template, return None
        - If folder doesn't exist: return None (log warning)
        - If YAML is malformed: raise PreferencesParseError

        Returns:
            VaultPreferences if file exists and is valid, None otherwise.

        Raises:
            PreferencesParseError: If file exists but has invalid YAML syntax.
        """
        from yaml import YAMLError

        from app.features.chat.preferences import (
            PREFERENCES_TEMPLATE,
            UserPreferences,
            VaultPreferences,
        )

        prefs_path = self.vault_path / "_jasque" / "preferences.md"
        folder_path = self.vault_path / "_jasque"

        # Check if preferences file exists
        if not await aiofiles.os.path.exists(prefs_path):
            # Check if folder exists - if so, create template
            if await aiofiles.os.path.exists(folder_path):
                await self._atomic_write(prefs_path, PREFERENCES_TEMPLATE)
                logger.info(
                    "vault.preferences.template_created",
                    path="_jasque/preferences.md",
                )
            else:
                logger.warning(
                    "vault.preferences.not_found",
                    path="_jasque/preferences.md",
                )
            return None

        # Read the file
        content = await self._read_note_content(prefs_path)
        if content is None:
            logger.warning(
                "vault.preferences.read_failed",
                path="_jasque/preferences.md",
            )
            return None

        # Parse frontmatter
        try:
            post = frontmatter.loads(content)
            metadata = dict(post.metadata)
            body = post.content
        except YAMLError as e:
            raise PreferencesParseError(
                f"Invalid YAML in _jasque/preferences.md: {e}. "
                "Check the file for syntax errors (missing colons, incorrect indentation)."
            ) from e

        # Validate against schema
        try:
            structured = UserPreferences.model_validate(metadata)
        except Exception as e:
            # Log validation error but use defaults for invalid fields
            logger.warning(
                "vault.preferences.validation_warning",
                error=str(e),
            )
            structured = UserPreferences()

        logger.info("vault.preferences.loaded", has_structured=bool(metadata))

        return VaultPreferences(
            structured=structured,
            additional_context=body,
        )
```

**IMPORTS:** Add at top of file (after existing imports):
- The `YAMLError` import is done locally to avoid circular imports
- `VaultPreferences`, `UserPreferences`, `PREFERENCES_TEMPLATE` imported locally

**PATTERN:** Follow `read_note()` pattern (lines 355-390)
**GOTCHA:** Import preferences schemas locally to avoid circular import
**VALIDATE:** `uv run python -c "from app.shared.vault.manager import VaultManager; print('OK')"`

---

### Task 5: ADD `PreferencesParseError` import to `app/shared/vault/manager.py`

Update the imports at the top of manager.py to include the new exception.

**IMPLEMENT:** Add `PreferencesParseError` to the import from exceptions (around line 17-25):

```python
from app.shared.vault.exceptions import (
    FolderAlreadyExistsError,
    FolderNotEmptyError,
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
    PathTraversalError,
    PreferencesParseError,  # ADD THIS
    TaskNotFoundError,
)
```

**VALIDATE:** `uv run python -c "from app.shared.vault.manager import VaultManager; print('OK')"`

---

### Task 6: UPDATE `app/features/chat/openai_routes.py` to load preferences

Integrate preferences loading and injection into the chat endpoint.

**IMPLEMENT:**

1. Add imports at top of file (after line 27):
```python
from app.features.chat.preferences import VaultPreferences, format_preferences_for_agent
from app.shared.vault import PreferencesParseError, VaultManager
```

2. Add preferences loading after deps creation (after line 64, before user_message extraction):
```python
    # Load user preferences from vault
    vault_manager = VaultManager(deps.vault_path)
    preferences: VaultPreferences | None = None
    try:
        preferences = await vault_manager.load_preferences()
    except PreferencesParseError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
```

3. Modify user_message to include preferences context (after line 72, where user_message is set):
```python
    # Prepend preferences context if available
    if preferences:
        prefs_context = format_preferences_for_agent(preferences)
        user_message = f"{prefs_context}\n\n---\n\n{user_message}"
```

**PATTERN:** Follow existing HTTPException pattern (lines 69-72)
**GOTCHA:** Preferences context goes BEFORE the user message, separated by `---`
**VALIDATE:** `uv run python -c "from app.features.chat.openai_routes import router; print('OK')"`

---

### Task 7: CREATE `app/features/chat/tests/test_preferences.py`

Create comprehensive tests for the preferences system.

**IMPLEMENT:**
```python
"""Tests for user preferences loading and formatting."""

from pathlib import Path

import pytest

from app.features.chat.preferences import (
    PREFERENCES_TEMPLATE,
    DefaultFolders,
    ResponseStyle,
    UserPreferences,
    VaultPreferences,
    format_preferences_for_agent,
)
from app.shared.vault import PreferencesParseError, VaultManager


# =============================================================================
# Schema Tests
# =============================================================================


def test_user_preferences_defaults():
    """UserPreferences should have sensible defaults."""
    prefs = UserPreferences()
    assert prefs.date_format == "YYYY-MM-DD"
    assert prefs.time_format == "HH:mm"
    assert prefs.response_style.verbosity == "concise"


def test_user_preferences_custom_values():
    """UserPreferences should accept custom values."""
    prefs = UserPreferences(
        date_format="DD/MM/YYYY",
        default_folders=DefaultFolders(meeting_notes="Meetings/"),
    )
    assert prefs.date_format == "DD/MM/YYYY"
    assert prefs.default_folders.meeting_notes == "Meetings/"


def test_vault_preferences_with_context():
    """VaultPreferences should store additional context."""
    prefs = VaultPreferences(
        structured=UserPreferences(),
        additional_context="I use PARA method.",
    )
    assert prefs.additional_context == "I use PARA method."


# =============================================================================
# Formatting Tests
# =============================================================================


def test_format_preferences_basic():
    """format_preferences_for_agent should produce readable output."""
    prefs = VaultPreferences()
    result = format_preferences_for_agent(prefs)

    assert "## User Preferences" in result
    assert "Date format: YYYY-MM-DD" in result
    assert "Response verbosity: concise" in result


def test_format_preferences_with_folders():
    """format_preferences_for_agent should include folder preferences."""
    prefs = VaultPreferences(
        structured=UserPreferences(
            default_folders=DefaultFolders(
                meeting_notes="Meetings/",
                daily_notes="Daily/",
            )
        )
    )
    result = format_preferences_for_agent(prefs)

    assert "Meeting notes folder: Meetings/" in result
    assert "Daily notes folder: Daily/" in result


def test_format_preferences_with_additional_context():
    """format_preferences_for_agent should include additional context."""
    prefs = VaultPreferences(
        additional_context="I prefer bullet points.\nUse PARA method.",
    )
    result = format_preferences_for_agent(prefs)

    assert "## Additional User Context" in result
    assert "I prefer bullet points." in result


# =============================================================================
# VaultManager.load_preferences Tests
# =============================================================================


@pytest.fixture
def vault_with_preferences(tmp_path: Path) -> Path:
    """Create a vault with valid preferences file."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()

    prefs_file = jasque_dir / "preferences.md"
    prefs_file.write_text('''---
date_format: "DD-MM-YYYY"
time_format: "HH:mm:ss"
default_folders:
  meeting_notes: "Meetings/"
  daily_notes: "Journal/"
response_style:
  verbosity: "detailed"
  use_bullet_points: false
---

## My Notes

I organize using the PARA method.
Meeting notes always include action items.
''')
    return tmp_path


@pytest.fixture
def vault_with_empty_jasque_folder(tmp_path: Path) -> Path:
    """Create a vault with _jasque folder but no preferences file."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()
    return tmp_path


@pytest.fixture
def vault_without_jasque_folder(tmp_path: Path) -> Path:
    """Create a vault without _jasque folder."""
    return tmp_path


@pytest.fixture
def vault_with_malformed_yaml(tmp_path: Path) -> Path:
    """Create a vault with invalid YAML in preferences."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()

    prefs_file = jasque_dir / "preferences.md"
    prefs_file.write_text('''---
date_format: "YYYY-MM-DD"
  bad_indent: this is wrong
response_style
  missing_colon: true
---

Content here.
''')
    return tmp_path


async def test_load_preferences_valid_file(vault_with_preferences: Path):
    """load_preferences should parse valid preferences file."""
    manager = VaultManager(vault_with_preferences)
    prefs = await manager.load_preferences()

    assert prefs is not None
    assert prefs.structured.date_format == "DD-MM-YYYY"
    assert prefs.structured.time_format == "HH:mm:ss"
    assert prefs.structured.default_folders.meeting_notes == "Meetings/"
    assert prefs.structured.default_folders.daily_notes == "Journal/"
    assert prefs.structured.response_style.verbosity == "detailed"
    assert prefs.structured.response_style.use_bullet_points is False
    assert "PARA method" in prefs.additional_context


async def test_load_preferences_creates_template(vault_with_empty_jasque_folder: Path):
    """load_preferences should create template if folder exists but file doesn't."""
    manager = VaultManager(vault_with_empty_jasque_folder)
    prefs = await manager.load_preferences()

    # Should return None (template just created)
    assert prefs is None

    # Template should exist
    template_path = vault_with_empty_jasque_folder / "_jasque" / "preferences.md"
    assert template_path.exists()

    content = template_path.read_text()
    assert "Jasque User Preferences" in content
    assert "date_format:" in content


async def test_load_preferences_no_folder(vault_without_jasque_folder: Path):
    """load_preferences should return None if _jasque folder doesn't exist."""
    manager = VaultManager(vault_without_jasque_folder)
    prefs = await manager.load_preferences()

    assert prefs is None

    # Should NOT create the folder
    jasque_dir = vault_without_jasque_folder / "_jasque"
    assert not jasque_dir.exists()


async def test_load_preferences_malformed_yaml(vault_with_malformed_yaml: Path):
    """load_preferences should raise PreferencesParseError for invalid YAML."""
    manager = VaultManager(vault_with_malformed_yaml)

    with pytest.raises(PreferencesParseError) as exc_info:
        await manager.load_preferences()

    error_msg = str(exc_info.value)
    assert "Invalid YAML" in error_msg
    assert "_jasque/preferences.md" in error_msg


async def test_load_preferences_partial_yaml(tmp_path: Path):
    """load_preferences should use defaults for missing/invalid fields."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()

    prefs_file = jasque_dir / "preferences.md"
    prefs_file.write_text('''---
date_format: "custom-format"
unknown_field: "ignored"
---

Just some context.
''')

    manager = VaultManager(tmp_path)
    prefs = await manager.load_preferences()

    assert prefs is not None
    assert prefs.structured.date_format == "custom-format"
    # Missing fields should have defaults
    assert prefs.structured.time_format == "HH:mm"
    assert prefs.structured.response_style.verbosity == "concise"


# =============================================================================
# Template Tests
# =============================================================================


def test_preferences_template_is_valid_yaml():
    """PREFERENCES_TEMPLATE should be parseable."""
    import frontmatter

    post = frontmatter.loads(PREFERENCES_TEMPLATE)
    assert "date_format" in post.metadata
    assert "default_folders" in post.metadata
    assert "response_style" in post.metadata


def test_preferences_template_validates_as_schema():
    """PREFERENCES_TEMPLATE should validate against UserPreferences schema."""
    import frontmatter

    post = frontmatter.loads(PREFERENCES_TEMPLATE)
    prefs = UserPreferences.model_validate(post.metadata)

    assert prefs.date_format == "YYYY-MM-DD"
    assert prefs.default_folders.meeting_notes == "Meetings/"
```

**PATTERN:** Follow `test_manager.py` fixture and test patterns
**VALIDATE:** `uv run pytest app/features/chat/tests/test_preferences.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Scope:** Test preferences schemas, formatting, and VaultManager.load_preferences() in isolation.

**Files:**
- `app/features/chat/tests/test_preferences.py` - All unit tests

**Coverage Requirements:**
- Schema defaults and custom values
- Formatting output for various preference combinations
- File exists/missing/malformed scenarios
- Template auto-creation

### Integration Tests

**Scope:** Test preferences injection into chat endpoint.

**Approach:** Add to `app/tests/test_integration_workflows.py` or create new integration test:
- Request with valid preferences
- Request with missing preferences (should work)
- Request with malformed YAML (should return 400)

### Edge Cases

- Empty preferences file (just frontmatter delimiters)
- Preferences with only additional context (no YAML)
- Very large additional context section
- Non-UTF8 characters in preferences
- Concurrent preference reads

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check app/features/chat/preferences.py
uv run ruff check app/shared/vault/manager.py
uv run ruff check app/features/chat/openai_routes.py
uv run ruff format --check .
```

### Level 2: Type Checking

```bash
uv run mypy app/
uv run pyright app/
```

### Level 3: Unit Tests

```bash
# Run new preferences tests
uv run pytest app/features/chat/tests/test_preferences.py -v

# Run all tests to check for regressions
uv run pytest -v
```

### Level 4: Integration Tests

```bash
uv run pytest -v -m integration
```

### Level 5: Manual Validation

1. **Start server:**
   ```bash
   uv run uvicorn app.main:app --reload --port 8123
   ```

2. **Test without preferences folder:**
   ```bash
   curl -X POST http://localhost:8123/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}]}'
   ```
   Expected: Works normally, logs warning about missing preferences

3. **Create _jasque folder and test template creation:**
   ```bash
   mkdir -p $OBSIDIAN_VAULT_PATH/_jasque
   # Make another request - template should be created
   curl -X POST http://localhost:8123/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}]}'
   # Check template was created
   cat $OBSIDIAN_VAULT_PATH/_jasque/preferences.md
   ```

4. **Test with valid preferences:**
   - Edit `_jasque/preferences.md` with custom values
   - Make a request and verify agent acknowledges preferences

5. **Test malformed YAML:**
   - Break the YAML syntax in preferences.md
   - Make a request, verify HTTP 400 response with helpful error

---

## ACCEPTANCE CRITERIA

- [ ] Preferences file is read from `_jasque/preferences.md` on each request
- [ ] Missing file logs warning but doesn't break agent (returns None)
- [ ] Template auto-created when `_jasque/` folder exists but file doesn't
- [ ] Malformed YAML returns HTTP 400 with actionable error message
- [ ] Structured preferences are validated with Pydantic (invalid fields use defaults)
- [ ] Additional context (markdown body) is captured and injected
- [ ] Agent receives preferences in its context (prepended to user message)
- [ ] All validation commands pass with zero errors
- [ ] No regressions in existing 273 tests

---

## COMPLETION CHECKLIST

- [ ] Task 1: Created `preferences.py` with schemas and formatting
- [ ] Task 2: Added `PreferencesParseError` to exceptions
- [ ] Task 3: Updated `__init__.py` exports
- [ ] Task 4: Added `load_preferences()` to VaultManager
- [ ] Task 5: Added exception import to manager.py
- [ ] Task 6: Integrated preferences into openai_routes.py
- [ ] Task 7: Created comprehensive test file
- [ ] All validation commands pass
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

### Design Decisions

1. **Per-request loading (not cached):** User can edit preferences.md and changes take effect immediately. The file is small (~1KB) so performance impact is negligible.

2. **Prepend to user message:** This is the simplest injection point that preserves message history integrity. The agent sees preferences as context before the user's actual question.

3. **Template auto-creation:** Reduces friction for users - they just need to create the folder, and Jasque provides a documented template.

4. **Graceful degradation for validation:** If YAML is valid but some fields don't match the schema, we use defaults rather than failing. This allows users to experiment with the format.

### Forward Compatibility (Phase 2+)

- Preferences schemas are in a separate file, won't conflict with conversation storage
- VaultManager method is self-contained, easy to extend
- The `_jasque/` folder convention can hold other files (conversation logs, extracted facts) in future phases

### Known Limitations

- Preferences are user-editable text, so we can't guarantee type safety
- No versioning/migration for preference format changes
- No UI for editing preferences (user must edit markdown directly)
