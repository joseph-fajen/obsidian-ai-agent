# Jasque - Claude Project Guidelines

This document provides context and guidelines for Claude when working on the Jasque project.

---

## Project Overview

**Jasque** is an AI agent for Obsidian vault management. It provides natural language interaction with Obsidian vaults through an OpenAI-compatible API consumed by the Obsidian Copilot plugin.

### Key Technologies

- **Pydantic AI** - Agent framework with typed tools
- **FastAPI** - API layer with streaming support
- **Docker** - Containerized deployment with vault volume mounting
- **Anthropic Claude** - LLM provider
- **UV** - Python package management

---

## Architecture Quick Reference

```
app/                          # Project root
├── main.py                   # FastAPI entry point
├── core/                     # Agent, config, dependencies
├── shared/                   # Vault utilities, OpenAI adapter
└── features/                 # Vertical slices (chat, notes, search, structure)
```

### Docker Context

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

## The 3 Tools

| Tool | Purpose | Operations |
|------|---------|------------|
| `obsidian_manage_notes` | Note CRUD + tasks | read, create, update, append, delete, complete_task |
| `obsidian_query_vault` | Search & discovery | search_text, find_by_tag, list_notes, list_folders, get_backlinks, get_tags, list_tasks |
| `obsidian_manage_structure` | Folder management | create_folder, rename, delete_folder, move, list_structure |

All tools use `obsidian_` prefix and support bulk operations.

---

## Code Style Guidelines

### Python

- Use type hints everywhere
- Pydantic models for all data structures
- Async functions for I/O operations
- Follow existing patterns in codebase

### Tool Implementation

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

## Testing Approach

### Local Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=app
```

### Docker Testing

```bash
# Build and run
docker compose up --build

# Test endpoint
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "List my notes"}]}'
```

---

## Common Tasks

### Adding a New Operation to Existing Tool

1. Add operation to `Literal` type in signature
2. Add operation handler in tool function
3. Update tool docstring with new operation
4. Add tests for new operation
5. Update `mvp-tool-designs.md` if significant

### Adding a New Feature Slice

1. Create `features/new_feature/` directory
2. Add `__init__.py`, `tools.py`, `models.py`
3. Register tools in `core/agent.py`
4. Update documentation

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
