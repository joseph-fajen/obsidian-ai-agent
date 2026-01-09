# Feature: obsidian_query_vault Tool Implementation

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Implement `obsidian_query_vault` - the first agent tool for Jasque. This tool enables users to search and query their Obsidian vault through 7 operations: `search_text`, `find_by_tag`, `list_notes`, `list_folders`, `get_backlinks`, `get_tags`, and `list_tasks`.

This is the foundational tool implementation that establishes patterns for future tools (`obsidian_manage_notes`, `obsidian_manage_structure`).

## User Story

As an Obsidian vault user
I want to search my vault using natural language queries
So that I can quickly find notes, tasks, and information without manual browsing

## Problem Statement

Users need to discover and retrieve information from their Obsidian vaults via natural language. The agent currently has no tools to interact with the filesystem, making it unable to answer questions about vault contents.

## Solution Statement

Implement an async tool using Pydantic AI's `FunctionToolset` pattern that:
1. Accepts 7 query operations via a `Literal` type parameter
2. Delegates filesystem work to an async `VaultManager` class
3. Returns structured `QueryResult` Pydantic models
4. Uses `python-frontmatter` for metadata and regex for tasks/links

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High (foundational patterns)
**Primary Systems Affected**: `app/core/agents/`, `app/shared/vault/`, `app/features/obsidian_query_vault/`
**Dependencies**: `python-frontmatter>=1.0.0` (new), `aiofiles` (existing)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: READ THESE FILES BEFORE IMPLEMENTING!

- `app/core/agents/base.py` (lines 1-60) - Agent factory pattern, SYSTEM_PROMPT location, how to add toolsets
- `app/core/agents/types.py` (lines 1-21) - AgentDependencies dataclass to extend
- `app/core/agents/__init__.py` (lines 1-7) - Exports to update
- `app/features/chat/openai_schemas.py` (lines 1-50) - Schema organization pattern with section comments
- `app/features/chat/openai_routes.py` (lines 56-60) - How AgentDependencies is instantiated
- `app/features/chat/tests/test_openai_routes.py` (lines 12-38) - Test fixture patterns
- `app/core/exceptions.py` (lines 14-30) - Exception hierarchy pattern
- `app/core/logging.py` - Logger pattern: `logger = get_logger(__name__)`
- `.agents/reference/mvp-tool-designs.md` (lines 197-364) - Full `obsidian_query_vault` specification
- `.agents/reference/adding_tools_guide.md` (lines 165-239) - Agent-optimized docstring template

### New Files to Create

| File | Purpose |
|------|---------|
| `app/shared/vault/exceptions.py` | Vault-specific exceptions (PathTraversalError, NoteNotFoundError) |
| `app/shared/vault/manager.py` | Async VaultManager class for filesystem operations |
| `app/core/agents/tool_registry.py` | FunctionToolset factory function |
| `app/features/obsidian_query_vault/__init__.py` | Feature exports |
| `app/features/obsidian_query_vault/obsidian_query_vault_schemas.py` | QueryResult, QueryResultItem models |
| `app/features/obsidian_query_vault/obsidian_query_vault_tool.py` | Tool implementation with register function |
| `app/features/obsidian_query_vault/tests/__init__.py` | Test package |
| `app/features/obsidian_query_vault/tests/test_obsidian_query_vault_tool.py` | Tool unit tests |
| `app/shared/vault/tests/__init__.py` | Test package |
| `app/shared/vault/tests/test_manager.py` | VaultManager unit tests |

### Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `python-frontmatter>=1.0.0` dependency |
| `app/core/agents/types.py` | Add `vault_path: Path` to AgentDependencies |
| `app/core/agents/base.py` | Import toolset, add `toolsets=` param, update SYSTEM_PROMPT |
| `app/core/agents/__init__.py` | Export `create_obsidian_toolset` |
| `app/features/chat/openai_routes.py` | Pass `vault_path` in AgentDependencies |
| `app/shared/vault/__init__.py` | Export VaultManager |

### Relevant Documentation - READ THESE BEFORE IMPLEMENTING!

- [Pydantic AI Tools Documentation](https://ai.pydantic.dev/tools/)
  - Section: Function Tools and Schema
  - Why: Core patterns for tool function signatures
- [Pydantic AI Toolsets Documentation](https://ai.pydantic.dev/toolsets/)
  - Section: FunctionToolset
  - Why: How to create and register toolsets
- [python-frontmatter Documentation](https://python-frontmatter.readthedocs.io/)
  - Section: Usage
  - Why: Parsing YAML frontmatter from markdown
- [aiofiles Documentation](https://pypi.org/project/aiofiles/)
  - Section: Basic usage
  - Why: Async file operations pattern

### Patterns to Follow

**Tool Registration Pattern** (from Pydantic AI):
```python
from pydantic_ai import FunctionToolset, RunContext

toolset = FunctionToolset[AgentDependencies]()

@toolset.tool
async def obsidian_query_vault(
    ctx: RunContext[AgentDependencies],
    operation: Literal["search_text", ...],
    # ... parameters
) -> QueryResult:
    """Agent-optimized docstring."""
    vault = VaultManager(ctx.deps.vault_path)
    # ... implementation
```

**Schema Pattern** (from `app/features/chat/openai_schemas.py`):
```python
# =============================================================================
# Section Name
# =============================================================================

class ModelName(BaseModel):
    """Clear docstring."""
    field: type
```

**Exception Pattern** (from `app/core/exceptions.py`):
```python
class VaultError(Exception):
    """Base exception for vault-related errors."""
    pass

class PathTraversalError(VaultError):
    """Exception raised when path escapes vault root."""
    pass
```

**Logging Pattern**:
```python
from app.core.logging import get_logger
logger = get_logger(__name__)

logger.info("vault.query.search_started", query=query, path=path)
logger.error("vault.query.search_failed", error=str(e), exc_info=True)
```

**Path Security Pattern**:
```python
def validate_path(self, path: str) -> Path:
    """Ensure path stays within vault root."""
    full_path = (self.vault_path / path).resolve()
    if not full_path.is_relative_to(self.vault_path.resolve()):
        raise PathTraversalError(f"Access denied: {path}")
    return full_path
```

**Async File Pattern**:
```python
import aiofiles
import aiofiles.os

async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
    content = await f.read()

entries = await aiofiles.os.listdir(directory_path)
stat_result = await aiofiles.os.stat(file_path)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Dependencies & Exceptions)

Set up the foundational infrastructure before implementing business logic.

**Tasks:**
- Add `python-frontmatter` dependency to pyproject.toml
- Create vault exceptions module
- Update AgentDependencies with vault_path

### Phase 2: VaultManager Implementation

Build the async VaultManager class that handles all filesystem operations.

**Tasks:**
- Create VaultManager class with path validation
- Implement core methods: list_notes, list_folders, read_note
- Implement search methods: search_text, find_by_tag
- Implement relationship methods: get_backlinks, get_tags
- Implement task methods: list_tasks
- Add comprehensive tests

### Phase 3: Tool Schemas

Define Pydantic models for tool inputs and outputs.

**Tasks:**
- Create QueryResult and QueryResultItem schemas
- Follow existing schema patterns from chat feature

### Phase 4: Tool Implementation

Implement the actual tool function and registration.

**Tasks:**
- Create tool_registry.py with FunctionToolset factory
- Implement obsidian_query_vault tool with agent-optimized docstring
- Register tool with toolset

### Phase 5: Agent Integration

Connect the tool to the agent.

**Tasks:**
- Update agent base.py to use toolset
- Update SYSTEM_PROMPT to describe available tools
- Update AgentDependencies instantiation in routes
- Export from __init__.py files

### Phase 6: Testing & Validation

Comprehensive testing of all components.

**Tasks:**
- VaultManager unit tests with tmp_path
- Tool unit tests with mocked VaultManager
- Integration test with agent

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

---

### Task 1: UPDATE pyproject.toml

- **IMPLEMENT**: Add `python-frontmatter>=1.0.0` to dependencies list
- **PATTERN**: Follow existing dependency format (lines 5-15)
- **LOCATION**: Under `[project]` dependencies array
- **VALIDATE**: `uv sync && uv pip list | grep frontmatter`

---

### Task 2: CREATE app/shared/vault/exceptions.py

- **IMPLEMENT**: Vault exception hierarchy
- **PATTERN**: Mirror `app/core/exceptions.py` (lines 14-30)
- **CONTENT**:
```python
"""Vault-specific exception classes."""


class VaultError(Exception):
    """Base exception for vault-related errors."""

    pass


class PathTraversalError(VaultError):
    """Exception raised when path attempts to escape vault root."""

    pass


class NoteNotFoundError(VaultError):
    """Exception raised when a note is not found."""

    pass


class FolderNotFoundError(VaultError):
    """Exception raised when a folder is not found."""

    pass
```
- **VALIDATE**: `uv run python -c "from app.shared.vault.exceptions import VaultError, PathTraversalError"`

---

### Task 3: UPDATE app/core/agents/types.py

- **IMPLEMENT**: Add `vault_path` field to AgentDependencies
- **PATTERN**: Existing dataclass pattern (lines 8-12)
- **IMPORTS**: Add `from pathlib import Path`
- **CHANGES**:
```python
@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools via RunContext."""

    request_id: str = ""
    vault_path: Path = field(default_factory=lambda: Path("/vault"))
```
- **GOTCHA**: Use `field(default_factory=...)` for mutable default, not direct `Path("/vault")`
- **VALIDATE**: `uv run mypy app/core/agents/types.py`

---

### Task 4: CREATE app/shared/vault/manager.py

- **IMPLEMENT**: Async VaultManager class with all filesystem operations
- **PATTERN**: Use aiofiles for async I/O, frontmatter for parsing
- **IMPORTS**:
```python
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import aiofiles.os
import frontmatter

from app.core.logging import get_logger
from app.shared.vault.exceptions import (
    FolderNotFoundError,
    NoteNotFoundError,
    PathTraversalError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)
```
- **KEY METHODS**:
  - `__init__(self, vault_path: Path)` - Store vault path
  - `validate_path(self, path: str) -> Path` - Security check
  - `async list_notes(self, folder: str | None = None) -> list[NoteInfo]`
  - `async list_folders(self, path: str | None = None) -> list[FolderInfo]`
  - `async read_note(self, path: str) -> NoteContent`
  - `async search_text(self, query: str, path: str | None = None, limit: int = 50) -> list[SearchResult]`
  - `async find_by_tag(self, tags: list[str], path: str | None = None, limit: int = 50) -> list[NoteInfo]`
  - `async get_backlinks(self, note_path: str, limit: int = 50) -> list[BacklinkResult]`
  - `async get_tags(self) -> list[str]`
  - `async list_tasks(self, path: str | None = None, include_completed: bool = False, limit: int = 50) -> list[TaskInfo]`
- **HELPER DATACLASSES** (define at top of file):
```python
@dataclass
class NoteInfo:
    path: str
    title: str
    tags: list[str]
    modified: datetime | None = None

@dataclass
class FolderInfo:
    path: str
    name: str

@dataclass
class SearchResult:
    path: str
    title: str
    snippet: str
    line_number: int

@dataclass
class BacklinkResult:
    path: str
    title: str
    context: str

@dataclass
class TaskInfo:
    path: str
    task_text: str
    completed: bool
    line_number: int

@dataclass
class NoteContent:
    path: str
    title: str
    content: str
    tags: list[str]
    metadata: dict[str, Any]
```
- **REGEX PATTERNS**:
```python
WIKILINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
TASK_PATTERN = re.compile(r'^(\s*)-\s*\[([ xX])\]\s*(.+)$', re.MULTILINE)
TAG_PATTERN = re.compile(r'#([a-zA-Z][a-zA-Z0-9_/-]*)')
```
- **GOTCHA**: Skip hidden files/folders (starting with `.`)
- **GOTCHA**: Handle files without frontmatter gracefully
- **GOTCHA**: Use `encoding='utf-8'` and catch `UnicodeDecodeError`
- **VALIDATE**: `uv run mypy app/shared/vault/manager.py && uv run pyright app/shared/vault/manager.py`

---

### Task 5: UPDATE app/shared/vault/__init__.py

- **IMPLEMENT**: Export VaultManager and exceptions
- **CONTENT**:
```python
"""Vault utilities - shared vault management functionality."""

from app.shared.vault.exceptions import (
    FolderNotFoundError,
    NoteNotFoundError,
    PathTraversalError,
    VaultError,
)
from app.shared.vault.manager import VaultManager

__all__ = [
    "FolderNotFoundError",
    "NoteNotFoundError",
    "PathTraversalError",
    "VaultError",
    "VaultManager",
]
```
- **VALIDATE**: `uv run python -c "from app.shared.vault import VaultManager, VaultError"`

---

### Task 6: CREATE app/shared/vault/tests/__init__.py

- **IMPLEMENT**: Empty test package init
- **CONTENT**: `"""Tests for vault utilities."""`
- **VALIDATE**: File exists

---

### Task 7: CREATE app/shared/vault/tests/test_manager.py

- **IMPLEMENT**: Comprehensive VaultManager tests using tmp_path
- **PATTERN**: Mirror `app/features/chat/tests/test_openai_routes.py` fixtures
- **KEY TESTS**:
  - `test_validate_path_within_vault` - Valid path passes
  - `test_validate_path_traversal_blocked` - `../` blocked
  - `test_list_notes_empty_vault` - Returns empty list
  - `test_list_notes_with_files` - Returns note info
  - `test_list_notes_skips_hidden` - `.obsidian/` skipped
  - `test_search_text_finds_match` - Query in content found
  - `test_search_text_case_insensitive` - Case doesn't matter
  - `test_find_by_tag_frontmatter` - Tags from YAML
  - `test_find_by_tag_inline` - Tags from content `#tag`
  - `test_get_backlinks` - Finds `[[note]]` references
  - `test_get_tags_all_unique` - Deduplicates tags
  - `test_list_tasks_incomplete` - `- [ ]` found
  - `test_list_tasks_complete` - `- [x]` found when include_completed=True
- **FIXTURE**:
```python
@pytest.fixture
def vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault with test notes."""
    # Create test structure
    (tmp_path / "notes").mkdir()
    (tmp_path / ".obsidian").mkdir()  # Should be skipped

    # Create test notes
    note1 = tmp_path / "notes" / "test-note.md"
    note1.write_text("""---
title: Test Note
tags: [project, important]
---

# Test Note

This is test content with a [[link-to-other]] and #inline-tag.

- [ ] Incomplete task
- [x] Completed task
""")
    return tmp_path
```
- **VALIDATE**: `uv run pytest app/shared/vault/tests/test_manager.py -v`

---

### Task 8: CREATE app/features/obsidian_query_vault/__init__.py

- **IMPLEMENT**: Feature exports
- **CONTENT**:
```python
"""obsidian_query_vault feature - vault search and discovery tool."""

from app.features.obsidian_query_vault.obsidian_query_vault_schemas import (
    QueryResult,
    QueryResultItem,
)
from app.features.obsidian_query_vault.obsidian_query_vault_tool import (
    register_obsidian_query_vault_tool,
)

__all__ = [
    "QueryResult",
    "QueryResultItem",
    "register_obsidian_query_vault_tool",
]
```
- **VALIDATE**: Syntax check after creating referenced files

---

### Task 9: CREATE app/features/obsidian_query_vault/obsidian_query_vault_schemas.py

- **IMPLEMENT**: Pydantic models for tool results
- **PATTERN**: Mirror `app/features/chat/openai_schemas.py` structure
- **CONTENT**:
```python
"""Pydantic schemas for obsidian_query_vault tool."""

from datetime import datetime

from pydantic import BaseModel


# =============================================================================
# Result Item Models
# =============================================================================


class QueryResultItem(BaseModel):
    """A single item in query results."""

    path: str
    title: str | None = None
    snippet: str | None = None
    tags: list[str] | None = None
    modified: datetime | None = None
    task_text: str | None = None
    task_completed: bool | None = None
    line_number: int | None = None


# =============================================================================
# Query Result Model
# =============================================================================


class QueryResult(BaseModel):
    """Result from obsidian_query_vault operations."""

    success: bool
    operation: str
    total_count: int
    results: list[QueryResultItem]
    truncated: bool = False
    message: str | None = None
```
- **VALIDATE**: `uv run mypy app/features/obsidian_query_vault/obsidian_query_vault_schemas.py`

---

### Task 10: CREATE app/features/obsidian_query_vault/obsidian_query_vault_tool.py

- **IMPLEMENT**: Tool function with FunctionToolset registration
- **PATTERN**: Follow `.agents/reference/adding_tools_guide.md` docstring template
- **IMPORTS**:
```python
"""obsidian_query_vault tool implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic_ai import FunctionToolset, RunContext

from app.core.agents.types import AgentDependencies
from app.core.logging import get_logger
from app.features.obsidian_query_vault.obsidian_query_vault_schemas import (
    QueryResult,
    QueryResultItem,
)
from app.shared.vault import VaultError, VaultManager

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)
```
- **FUNCTION SIGNATURE**:
```python
def register_obsidian_query_vault_tool(
    toolset: FunctionToolset[AgentDependencies],
) -> None:
    """Register the obsidian_query_vault tool with the given toolset."""

    @toolset.tool
    async def obsidian_query_vault(
        ctx: RunContext[AgentDependencies],
        operation: Literal[
            "search_text",
            "find_by_tag",
            "list_notes",
            "list_folders",
            "get_backlinks",
            "get_tags",
            "list_tasks",
        ],
        query: str | None = None,
        path: str | None = None,
        tags: list[str] | None = None,
        include_completed: bool = False,
        response_format: Literal["detailed", "concise"] = "concise",
        limit: int = 50,
    ) -> QueryResult:
        """Search and query the Obsidian vault...

        [FULL AGENT-OPTIMIZED DOCSTRING - see adding_tools_guide.md]
        """
```
- **DOCSTRING**: Must include all 7 sections from adding_tools_guide.md:
  1. One-line summary
  2. "Use this when" (5 scenarios)
  3. "Do NOT use" (redirect to other tools)
  4. Args with guidance
  5. Returns with format details
  6. Performance Notes
  7. Examples (4 realistic examples)
- **IMPLEMENTATION**: Dispatch to VaultManager based on operation, convert results to QueryResult
- **ERROR HANDLING**: Catch VaultError, return QueryResult with success=False and actionable message
- **VALIDATE**: `uv run mypy app/features/obsidian_query_vault/obsidian_query_vault_tool.py`

---

### Task 11: CREATE app/core/agents/tool_registry.py

- **IMPLEMENT**: FunctionToolset factory function
- **CONTENT**:
```python
"""Tool registry - creates toolsets for the Jasque agent."""

from pydantic_ai import FunctionToolset

from app.core.agents.types import AgentDependencies
from app.features.obsidian_query_vault.obsidian_query_vault_tool import (
    register_obsidian_query_vault_tool,
)


def create_obsidian_toolset() -> FunctionToolset[AgentDependencies]:
    """Create a FunctionToolset with all Obsidian vault tools.

    Returns:
        FunctionToolset configured with obsidian_query_vault tool.
        Future tools (obsidian_manage_notes, obsidian_manage_structure)
        will be registered here.
    """
    toolset: FunctionToolset[AgentDependencies] = FunctionToolset()

    # Register query/search tool
    register_obsidian_query_vault_tool(toolset)

    # Future: register_obsidian_manage_notes_tool(toolset)
    # Future: register_obsidian_manage_structure_tool(toolset)

    return toolset
```
- **VALIDATE**: `uv run mypy app/core/agents/tool_registry.py`

---

### Task 12: UPDATE app/core/agents/base.py

- **IMPLEMENT**: Add toolset to agent, update SYSTEM_PROMPT
- **CHANGES**:
  1. Import: `from app.core.agents.tool_registry import create_obsidian_toolset`
  2. Update SYSTEM_PROMPT to describe available tool
  3. Add `toolsets=[create_obsidian_toolset()]` to Agent constructor
- **SYSTEM_PROMPT UPDATE** (append to existing):
```python
SYSTEM_PROMPT = """You are Jasque, an AI assistant for Obsidian vault management.

You help users interact with their Obsidian vault using natural language.

## Available Tools

You have access to the following tool:

### obsidian_query_vault
Search and query the Obsidian vault. Operations:
- search_text: Full-text search across notes
- find_by_tag: Find notes with specific tags
- list_notes: List notes in vault or folder
- list_folders: Get folder structure
- get_backlinks: Find notes linking to a specific note
- get_tags: Get all unique tags in vault
- list_tasks: Find task checkboxes

Use response_format="concise" (default) for brief results, "detailed" for full content.

## Guidelines

- Always use the appropriate tool to answer questions about the vault
- When searching, start with concise format and only use detailed if needed
- If a search returns no results, suggest alternative queries
- Be helpful and conversational while being efficient with tool calls
"""
```
- **AGENT CONSTRUCTION**:
```python
def create_agent() -> Agent[AgentDependencies, str]:
    """Create and configure the Jasque agent with tools."""
    settings = get_settings()
    model_name = f"anthropic:{settings.anthropic_model}"

    toolset = create_obsidian_toolset()

    agent: Agent[AgentDependencies, str] = Agent(
        model_name,
        deps_type=AgentDependencies,
        output_type=str,
        instructions=SYSTEM_PROMPT,
        toolsets=[toolset],
    )

    logger.info("agent.created", model=model_name, tools=["obsidian_query_vault"])
    return agent
```
- **VALIDATE**: `uv run mypy app/core/agents/base.py`

---

### Task 13: UPDATE app/core/agents/__init__.py

- **IMPLEMENT**: Export create_obsidian_toolset
- **CHANGES**: Add to imports and __all__
```python
from app.core.agents.base import create_agent, get_agent
from app.core.agents.tool_registry import create_obsidian_toolset
from app.core.agents.types import AgentDependencies

__all__ = ["AgentDependencies", "create_agent", "create_obsidian_toolset", "get_agent"]
```
- **VALIDATE**: `uv run python -c "from app.core.agents import create_obsidian_toolset"`

---

### Task 14: UPDATE app/features/chat/openai_routes.py

- **IMPLEMENT**: Pass vault_path in AgentDependencies
- **CHANGES**: Update deps instantiation (around line 58)
- **IMPORTS**: Add `from app.core.config import get_settings`
- **CODE**:
```python
settings = get_settings()
deps = AgentDependencies(
    request_id=request_id,
    vault_path=settings.vault_path,
)
```
- **GOTCHA**: Need to add vault_path to Settings in config.py first
- **VALIDATE**: `uv run mypy app/features/chat/openai_routes.py`

---

### Task 15: UPDATE app/core/config.py

- **IMPLEMENT**: Add vault_path setting
- **CHANGES**: Add to Settings class
```python
vault_path: Path = Path("/vault")
```
- **IMPORTS**: Ensure `from pathlib import Path` is present
- **VALIDATE**: `uv run mypy app/core/config.py`

---

### Task 16: CREATE app/features/obsidian_query_vault/tests/__init__.py

- **IMPLEMENT**: Test package init
- **CONTENT**: `"""Tests for obsidian_query_vault feature."""`
- **VALIDATE**: File exists

---

### Task 17: CREATE app/features/obsidian_query_vault/tests/test_obsidian_query_vault_tool.py

- **IMPLEMENT**: Tool unit tests
- **PATTERN**: Mirror `app/features/chat/tests/test_openai_routes.py`
- **KEY TESTS**:
  - `test_search_text_returns_results` - Mocked VaultManager
  - `test_find_by_tag_requires_tags` - Error without tags param
  - `test_list_notes_empty_vault` - Returns empty results
  - `test_get_backlinks_requires_path` - Error without path
  - `test_list_tasks_filters_completed` - Respects include_completed
  - `test_invalid_operation_handled` - Graceful error for unknown op
  - `test_vault_error_returns_failure` - VaultError → success=False
- **FIXTURE**: Mock VaultManager methods
- **VALIDATE**: `uv run pytest app/features/obsidian_query_vault/tests/ -v`

---

### Task 18: DELETE app/features/search/ (cleanup)

- **IMPLEMENT**: Remove old empty search feature directory
- **REASON**: Replaced by obsidian_query_vault with verbose naming
- **VALIDATE**: Directory no longer exists

---

### Task 19: RUN full validation suite

- **VALIDATE ALL**:
```bash
uv run ruff check .
uv run ruff format .
uv run mypy app/
uv run pyright app/
uv run pytest -v
```

---

## TESTING STRATEGY

### Unit Tests

**VaultManager** (`app/shared/vault/tests/test_manager.py`):
- Path validation security
- Each filesystem operation
- Edge cases: empty vault, no frontmatter, encoding errors
- Use `tmp_path` fixture for real temporary directories

**Tool Function** (`app/features/obsidian_query_vault/tests/test_obsidian_query_vault_tool.py`):
- Each operation dispatch
- Parameter validation
- Error handling
- Mock VaultManager to isolate tool logic

### Integration Tests

**Agent Integration**:
- Create test with real agent + tool
- Verify tool is registered and callable
- Test with mocked LLM response triggering tool

### Edge Cases

- Empty vault (no notes)
- Note without frontmatter
- Binary files in vault (should be skipped)
- Very large notes (>1MB)
- Notes with invalid UTF-8
- Deeply nested folder structures
- Path traversal attempts (`../../../etc/passwd`)
- Notes with no title (use filename)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check .
uv run ruff format --check .
```

### Level 2: Type Checking

```bash
uv run mypy app/
uv run pyright app/
```

### Level 3: Unit Tests

```bash
uv run pytest app/shared/vault/tests/ -v
uv run pytest app/features/obsidian_query_vault/tests/ -v
uv run pytest app/core/agents/tests/ -v
```

### Level 4: Full Test Suite

```bash
uv run pytest -v
```

### Level 5: Manual Validation

```bash
# Start the server
uv run uvicorn app.main:app --reload --port 8123

# Test health
curl http://localhost:8123/health

# Test tool via chat endpoint (requires OBSIDIAN_VAULT_PATH set)
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "List all notes in my vault"}]}'

# Test streaming
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "What tags exist in my vault?"}], "stream": true}'
```

---

## ACCEPTANCE CRITERIA

- [x] `python-frontmatter` dependency added and installed
- [ ] VaultManager handles all 7 query operations
- [ ] Path traversal attacks are blocked
- [ ] Tool registered with FunctionToolset pattern
- [ ] Agent SYSTEM_PROMPT describes available tool
- [ ] Tool docstring follows agent-optimized format
- [ ] All operations return structured QueryResult
- [ ] Errors return success=False with actionable messages
- [ ] Hidden files/folders (`.obsidian/`) are skipped
- [ ] All validation commands pass with zero errors
- [ ] Unit tests cover happy path and edge cases
- [ ] Manual testing confirms tool works via Obsidian Copilot

---

## COMPLETION CHECKLIST

- [ ] All 19 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

### Design Decisions

1. **Verbose Naming**: Files use `obsidian_query_vault_` prefix for greppability, breaking from generic naming pattern in chat feature. This is intentional for tool-related features.

2. **Async Throughout**: VaultManager is fully async using aiofiles, even though tools could technically use sync I/O in an executor. Async is more consistent with the codebase.

3. **tmp_path over pyfakefs**: Using pytest's `tmp_path` fixture creates real temporary directories. This is simpler and tests actual filesystem behavior without mocking complexity.

4. **FunctionToolset Pattern**: Using `FunctionToolset` with registration function allows future tools to be added without modifying agent construction.

5. **response_format Parameter**: Supports "concise" (default) and "detailed" to control token usage, per Anthropic best practices.

### Future Considerations

- `obsidian_manage_notes` tool will follow same patterns
- `obsidian_manage_structure` tool will follow same patterns
- May need to add caching for large vaults
- Could add semantic search later with embeddings

### Dependencies on External Systems

- Requires `OBSIDIAN_VAULT_PATH` environment variable for production
- Requires actual vault for manual testing
- LLM API key required for agent execution
