# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Jasque** is an AI agent for Obsidian vault management. It provides natural language interaction with Obsidian vaults through an OpenAI-compatible API consumed by the Obsidian Copilot plugin.

FastAPI + PostgreSQL application using **vertical slice architecture**, optimized for AI-assisted development. Python 3.12+, strict type checking with MyPy and Pyright.

### Key Technologies

- **Pydantic AI** - Agent framework with typed tools
- **FastAPI** - API layer with streaming support
- **Docker** - Containerized deployment with vault volume mounting
- **Anthropic Claude** - LLM provider
- **UV** - Python package management
- **PostgreSQL** - Database with Alembic migrations

### Docker Context (Obsidian Vault)

- Host vault path: `$OBSIDIAN_VAULT_PATH` (from `.env`)
- Container vault path: `/vault` (fixed mount point)
- Mount mode: `:rw` (bidirectional sync)

---

## Core Documents

| Document | When to Read |
|----------|--------------|
| `PRD.md` | Full requirements, architecture decisions |
| `mvp-tool-designs.md` | Tool signatures, parameters, examples |
| `CURRENT_STATE.md` | Current progress, what's implemented |
| `_session_logs/` | Recent session history, context |

---

## The 3 Obsidian Tools

| Tool | Purpose | Operations |
|------|---------|------------|
| `obsidian_manage_notes` | Note CRUD + tasks | read, create, update, append, delete, complete_task |
| `obsidian_query_vault` | Search & discovery | search_text, find_by_tag, list_notes, list_folders, get_backlinks, get_tags, list_tasks |
| `obsidian_manage_structure` | Folder management | create_folder, rename, delete_folder, move, list_structure |

All tools use `obsidian_` prefix and support bulk operations.

---

## Core Principles

**KISS** (Keep It Simple, Stupid)
- Prefer simple, readable solutions over clever abstractions

**YAGNI** (You Aren't Gonna Need It)
- Don't build features until they're actually needed

**Vertical Slice Architecture**
- Each feature owns its database models, schemas, routes, and business logic
- Features live in separate directories under `app/` (e.g., `app/features/notes/`, `app/features/search/`)
- Shared utilities go in `app/shared/` only when used by 3+ features
- Core infrastructure (`app/core/`) is shared across all features

**Type Safety (CRITICAL)**
- Strict type checking enforced (MyPy + Pyright in strict mode)
- All functions, methods, and variables MUST have type annotations
- Zero type suppressions allowed
- No `Any` types without explicit justification
- Test files have relaxed typing rules (see pyproject.toml)

---

## Essential Commands

### Development

```bash
# Start development server (port 8123)
uv run uvicorn app.main:app --reload --port 8123
```

### Testing

```bash
# Run all tests
uv run pytest -v

# Run integration tests only
uv run pytest -v -m integration

# Run specific test
uv run pytest -v app/core/tests/test_database.py::test_function_name
```

### Type Checking (must be green)

```bash
# MyPy (strict mode)
uv run mypy app/

# Pyright (strict mode)
uv run pyright app/
```

### Linting & Formatting (must be green)

```bash
# Check linting
uv run ruff check .

# Auto-format code
uv run ruff format .
```

### Database Migrations

```bash
# Start PostgreSQL (Docker)
docker-compose up -d db

# Apply migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Rollback one migration
uv run alembic downgrade -1
```

### Docker

```bash
# Build and start all services
docker-compose up -d --build

# View app logs
docker-compose logs -f app

# Stop all services
docker-compose down
```

---

## Architecture

### Directory Structure

```
app/
├── core/           # Infrastructure (config, database, logging, middleware, health, exceptions)
├── shared/         # Cross-feature utilities (pagination, timestamps, error schemas)
├── features/       # Vertical slices (notes/, search/, structure/, chat/)
└── main.py         # FastAPI application entry point
```

### Database

- Async SQLAlchemy with connection pooling (pool_size=5, max_overflow=10)
- Base class: `app.core.database.Base`
- Session dependency: `get_db()` from `app.core.database`
- All models inherit `TimestampMixin` from `app.shared.models`

### Logging

**Philosophy:** Logs are optimized for AI agent consumption.

- JSON output via structlog
- Event naming: `domain.component.action_state` (e.g., `vault.notes.create_completed`)
- Logger: `from app.core.logging import get_logger; logger = get_logger(__name__)`
- Always include `exc_info=True` for exceptions

---

## Session Workflow

### Starting a Session

1. Run `/start-session` command
2. Or manually read `CURRENT_STATE.md` and recent session logs

### Ending a Session

1. Run `/end-session` command
2. This creates a session log and updates `CURRENT_STATE.md`
3. Commit changes with descriptive message

### Session Log Location

`_session_logs/YYYY-MM-DD-N-description.md`

---

## Tool Implementation Pattern

```python
@agent.tool
def obsidian_tool_name(
    ctx: RunContext[VaultDependencies],
    operation: Literal["op1", "op2"],
    # ... parameters
) -> ResultModel:
    """
    Tool description for LLM understanding.

    Operations:
    - op1: Description
    - op2: Description

    Examples:
    - operation="op1", param="value"
    """
```

### Error Messages

Make errors actionable:
```python
# Good
"Note not found: projects/foo.md. Use obsidian_query_vault with operation='list_notes' to see available notes."

# Bad
"File not found"
```

---

## Important Constraints

1. **Path Security** - Always validate paths stay within `/vault`
2. **Atomic Writes** - No partial file updates
3. **Error Guidance** - Errors must tell agent how to fix
4. **Token Efficiency** - Support `response_format` for concise responses
5. **Bulk Support** - All CRUD tools support bulk operations

---

## Don't Forget

- Update `CURRENT_STATE.md` when completing features
- Create session logs when ending work
- Keep `mvp-tool-designs.md` in sync with implementation
- Test with actual Obsidian vault before marking complete
- Run both MyPy and Pyright before committing
