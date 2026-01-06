# Jasque - Product Requirements Document

## Executive Summary

**Jasque** is a custom AI agent that operates on Obsidian vaults via natural language. The agent exposes an OpenAI-compatible API endpoint consumed by the Obsidian Copilot plugin, enabling users to manage notes, query their knowledge base, and organize vault structure through conversation.

The MVP delivers 3 consolidated tools (17 operations) following Anthropic's tool design best practices, built with Pydantic AI and FastAPI using a Vertical Slice Architecture. Jasque runs in Docker with the vault mounted as a volume for secure, sandboxed access.

---

## Mission

Enable Obsidian users to interact with their vault using natural language, reducing friction in note management and knowledge retrieval.

---

## Target Users

- **Primary:** Obsidian power users who want AI-assisted vault management
- **Use Case:** Personal knowledge management, note-taking, task tracking
- **Environment:** Local-first, privacy-conscious users running the agent alongside Obsidian

---

## User Story

> As an Obsidian vault user, I want to interact with my vault using natural language, so that I can more easily manage my notes and tasks.

### Example Interactions

| User Says | Agent Does |
|-----------|------------|
| "What do I have written about project planning?" | Searches vault, returns relevant notes |
| "Create a new note about the meeting with Sarah" | Creates note in appropriate folder |
| "What tasks do I have outstanding?" | Lists incomplete tasks across vault |
| "Move all notes tagged #archive to the archive folder" | Bulk moves matching notes |
| "Mark the 'Buy groceries' task as done" | Completes the checkbox in the note |

---

## Technical Architecture

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Agent Framework** | Pydantic AI | Type-safe tools, multi-provider support, native streaming |
| **API Layer** | FastAPI | OpenAI-compatible endpoints, async, streaming via SSE |
| **Frontend** | Obsidian Copilot | Existing plugin with custom API endpoint support |
| **LLM Provider** | Anthropic Claude | Primary provider for MVP |
| **Package Manager** | UV (Astral) | Fast, modern Python dependency management |
| **Containerization** | Docker | Sandboxed execution, volume-mounted vault access |
| **Vault Access** | Docker volume mount | Bidirectional sync with host filesystem |

### Docker Deployment

Jasque runs in a Docker container with the Obsidian vault mounted as a volume:

```bash
# Run Jasque with vault mounted
docker run -v ${OBSIDIAN_VAULT_PATH}:/vault:rw -e OBSIDIAN_VAULT_PATH=/vault jasque-agent
```

**Volume Mounting Strategy:**

| Aspect | Configuration |
|--------|---------------|
| **Host Path** | `OBSIDIAN_VAULT_PATH` environment variable (e.g., `/Users/me/Documents/MyVault`) |
| **Container Path** | `/vault` (fixed mount point inside container) |
| **Permissions** | `:rw` (read-write) for bidirectional sync |
| **Security** | Container sandboxed to only access the mounted vault directory |

**Environment Configuration (`.env`):**

```bash
# Host machine vault path - mounted into container
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...

# Server Configuration
HOST=0.0.0.0
PORT=8123
```

**How It Works:**

1. User sets `OBSIDIAN_VAULT_PATH` in `.env` to their local vault location
2. Docker mounts this path to `/vault` inside the container
3. Jasque reads/writes to `/vault`, which syncs to host filesystem in real-time
4. Changes are immediately visible in Obsidian (may require refresh)
5. Container cannot access any files outside the mounted vault directory

### Project Structure (Vertical Slice Architecture)

```
app/                              # PROJECT ROOT
├── pyproject.toml                # UV package config
├── uv.lock
├── .python-version
├── .env / .env.example
├── .gitignore
├── README.md
├── PRD.md                        # This document
├── Dockerfile                    # Container definition
├── docker-compose.yml            # Compose config with volume mounts
│
├── main.py                       # FastAPI entry point
│
├── core/                         # Core infrastructure
│   ├── __init__.py
│   ├── agent.py                  # Pydantic AI agent instance
│   ├── config.py                 # Settings (pydantic-settings)
│   ├── dependencies.py           # VaultDependencies dataclass
│   └── lifespan.py               # FastAPI startup/shutdown
│
├── shared/                       # Shared utilities
│   ├── __init__.py
│   ├── vault/
│   │   ├── __init__.py
│   │   ├── manager.py            # VaultManager class
│   │   └── models.py             # Vault domain models
│   └── openai_adapter.py         # OpenAI format helpers
│
└── features/                     # Vertical slices
    ├── __init__.py
    ├── chat/                     # API endpoint feature
    │   ├── __init__.py
    │   ├── routes.py             # POST /v1/chat/completions
    │   ├── models.py             # Request/Response models
    │   └── history.py            # Conversation history (PostgreSQL)
    ├── notes/                    # Note management
    │   ├── __init__.py
    │   ├── tools.py              # obsidian_manage_notes
    │   └── models.py
    ├── search/                   # Query and discovery
    │   ├── __init__.py
    │   ├── tools.py              # obsidian_query_vault
    │   └── models.py
    └── structure/                # Folder management
        ├── __init__.py
        ├── tools.py              # obsidian_manage_structure
        └── models.py
```

---

## MVP Scope

### In Scope

| Category | Deliverable |
|----------|-------------|
| **Tools** | 3 consolidated tools with 17 operations |
| **API** | OpenAI-compatible `/v1/chat/completions` with streaming |
| **History** | PostgreSQL-based conversation persistence |
| **Notes** | Full CRUD operations + bulk support |
| **Search** | Text search, tag filtering, backlinks, task discovery |
| **Structure** | Folder CRUD, move/rename operations |
| **Tasks** | List incomplete tasks, mark tasks complete |

### Out of Scope (Deferred)

| Feature | Reason |
|---------|--------|
| Semantic search / embeddings | Requires vector DB infrastructure |
| Similar note discovery | Depends on embeddings |
| Auto-tagging | A-tier feature, not core MVP |
| Template support | Workflow enhancement, not core |
| Advanced task features | Due dates, priorities, recurring |
| Multi-vault support | Single vault per instance for MVP |

---

## Core Patterns & Principles

### Tool Design Principles

Based on [Anthropic's "Writing Tools for Agents"](https://www.anthropic.com/engineering/writing-tools-for-agents):

| Principle | Implementation |
|-----------|----------------|
| **Tool Consolidation** | 3 tools instead of 12+ granular tools |
| **Less is More** | Few thoughtful tools targeting high-impact workflows |
| **Context Efficiency** | `response_format` parameter for detailed vs concise |
| **Namespacing** | `obsidian_` prefix groups all vault operations |
| **Actionable Errors** | Errors guide agent toward correct usage |
| **Unambiguous Parameters** | Clear parameter names (`note_path` not `path`) |

### Architecture Patterns

| Pattern | Application |
|---------|-------------|
| **Vertical Slice Architecture** | Features are self-contained slices |
| **Single Agent** | One Pydantic AI agent assembles all tools |
| **Dependency Injection** | `VaultDependencies` passed via `RunContext` |
| **OpenAI Compatibility** | Standard format for plugin interoperability |

### Reference Implementation

Tool design informed by [mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) - validates core operations while we consolidate per Anthropic guidance.

---

## Agent Tools

### Tool Overview

| Tool | Operations | Purpose |
|------|------------|---------|
| `obsidian_manage_notes` | 6 | Note lifecycle + task completion |
| `obsidian_query_vault` | 7 | Search, discovery, retrieval |
| `obsidian_manage_structure` | 5 | Folder organization |

**Total: 3 tools, 17 operations**

---

### Tool 1: `obsidian_manage_notes`

**Purpose:** All note lifecycle operations (single or bulk)

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `operation` | enum | Yes | read, create, update, append, delete, complete_task |
| `path` | string | Yes | Note path relative to vault root |
| `content` | string | Conditional | Required for create/update/append |
| `folder` | string | No | Target folder for create |
| `task_identifier` | string | Conditional | Task text or line number for complete_task |
| `bulk` | boolean | No | Enable bulk mode |
| `items` | list | Conditional | List of operations for bulk mode |

**Operations:**

| Operation | Description |
|-----------|-------------|
| `read` | Get contents of a note |
| `create` | Create a new note |
| `update` | Replace entire note content |
| `append` | Add content to end of note |
| `delete` | Remove note from vault |
| `complete_task` | Mark checkbox as done (`- [ ]` → `- [x]`) |

---

### Tool 2: `obsidian_query_vault`

**Purpose:** All search, discovery, and retrieval operations

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `operation` | enum | Yes | search_text, find_by_tag, list_notes, list_folders, get_backlinks, get_tags, list_tasks |
| `query` | string | Conditional | Search query for search_text |
| `path` | string | No | Scope to folder/note |
| `tags` | list | Conditional | Tag list for find_by_tag |
| `include_completed` | boolean | No | Include completed tasks (default: false) |
| `response_format` | enum | No | detailed or concise (default: concise) |
| `limit` | integer | No | Max results (default: 50) |

**Operations:**

| Operation | Description |
|-----------|-------------|
| `search_text` | Full-text search across vault |
| `find_by_tag` | Find notes with specific tags |
| `list_notes` | List notes in vault or folder |
| `list_folders` | List folder structure |
| `get_backlinks` | Find notes linking to a note |
| `get_tags` | Get all tags in vault |
| `list_tasks` | Find tasks (checkboxes) |

---

### Tool 3: `obsidian_manage_structure`

**Purpose:** Folder and vault organization (single or bulk)

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `operation` | enum | Yes | create_folder, rename, delete_folder, move, list_structure |
| `path` | string | Yes | Target path |
| `new_path` | string | Conditional | Destination for rename/move |
| `bulk` | boolean | No | Enable bulk mode |
| `items` | list | Conditional | List of operations for bulk mode |
| `force` | boolean | No | Required for non-empty folder deletion |

**Operations:**

| Operation | Description |
|-----------|-------------|
| `create_folder` | Create a new folder |
| `rename` | Rename a folder or note |
| `delete_folder` | Delete a folder |
| `move` | Move note or folder |
| `list_structure` | Get vault folder tree |

---

## API Design

### Endpoint

```
POST /v1/chat/completions
```

### Request Format (OpenAI-compatible)

```json
{
  "model": "jasque",
  "messages": [
    {"role": "user", "content": "What tasks do I have?"}
  ],
  "stream": true
}
```

### Response Format

**Non-streaming:**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "jasque",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }]
}
```

**Streaming:** Server-Sent Events (SSE) with OpenAI delta format.

---

## Success Criteria

### MVP Complete When:

- [ ] Agent responds to natural language queries about vault
- [ ] All 3 tools functional with documented operations
- [ ] Streaming responses work in Obsidian Copilot
- [ ] Conversation history persists across sessions
- [ ] Bulk operations work for notes and folders
- [ ] Task listing and completion functional

### Quality Gates:

- [ ] Path traversal protection (no access outside vault)
- [ ] Graceful error handling with actionable messages
- [ ] Response times < 2s for simple operations
- [ ] Works with vault of 1000+ notes

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| File corruption | Atomic writes, no partial updates |
| Path traversal | Validate all paths within vault root (`/vault` in container) |
| Token limits | Pagination, concise response format |
| Obsidian conflicts | Document that Obsidian may need refresh |
| Container escape | Docker volume mount sandboxes access to only the vault directory |
| Host filesystem access | Container only sees `/vault`, cannot access other host paths |

---

## Implementation Roadmap

### Phase 1: Foundation
1. Scaffold project structure
2. Implement `shared/vault/manager.py`
3. Set up Pydantic AI agent in `core/agent.py`

### Phase 2: Tools
4. Implement `obsidian_manage_notes`
5. Implement `obsidian_query_vault`
6. Implement `obsidian_manage_structure`

### Phase 3: API
7. Implement `/v1/chat/completions` endpoint
8. Add SSE streaming support
9. Add conversation history

### Phase 4: Integration
10. Test with Obsidian Copilot
11. Refine tool descriptions based on agent behavior
12. Documentation and deployment

---

## Appendix: Tool Design Rationale

### Why Consolidation?

**Before (granular approach):**
```
read_note, create_note, update_note, delete_note, append_to_note,
search_notes, find_by_tag, get_backlinks, list_tasks, complete_task,
create_folder, delete_folder, move_note, rename_folder...
```
12+ tools with overlapping concepts.

**After (consolidated approach):**
```
obsidian_manage_notes
obsidian_query_vault
obsidian_manage_structure
```
3 tools with clear domains.

### Benefits

1. **Reduced agent confusion** - Fewer tools to choose from
2. **Clear mental model** - Notes, queries, structure
3. **Bulk operations native** - Parameter, not separate tool
4. **Extensible** - Add operations without new tools
5. **Aligned with Anthropic research** - Proven approach

---

*Document Version: 1.2*
*Last Updated: 2026-01-06*
*Agent Name: Jasque*
