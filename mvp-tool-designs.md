# MVP Tool Designs - Jasque

> **Purpose:** This document serves as the authoritative reference for agent tool implementation. It provides complete specifications for the 3 consolidated tools that power **Jasque**, the Obsidian AI Agent.

---

## Agent Overview

**Jasque** is an AI agent for Obsidian vault management. It runs in a Docker container with the user's vault mounted as a volume at `/vault`.

### Deployment Context

```bash
docker run -v ${OBSIDIAN_VAULT_PATH}:/vault:rw -e OBSIDIAN_VAULT_PATH=/vault jasque-agent
```

| Aspect | Value |
|--------|-------|
| **Container Vault Path** | `/vault` (fixed) |
| **Host Vault Path** | User-configured via `OBSIDIAN_VAULT_PATH` in `.env` |
| **Mount Mode** | `:rw` (read-write, bidirectional sync) |
| **Security** | Container sandboxed to only access `/vault` |

All tool paths are relative to `/vault` inside the container.

---

## Design Principles

These tools follow [Anthropic's best practices for writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents):

| Principle | How We Apply It |
|-----------|-----------------|
| **Tool Consolidation** | 3 tools instead of 12+ granular tools |
| **Less is More** | Few thoughtful tools targeting high-impact workflows |
| **Context Efficiency** | `response_format` parameter controls verbosity |
| **Namespacing** | `obsidian_` prefix groups all vault operations |
| **Actionable Errors** | Errors guide agent toward correct usage |
| **Unambiguous Parameters** | Clear, descriptive parameter names |

---

## Naming Conventions

- All tools prefixed with `obsidian_` to indicate vault operations
- Operations use `snake_case` (e.g., `search_text`, `create_folder`)
- Parameters use `snake_case` with clear nouns (e.g., `note_path`, `task_identifier`)

---

## Tool Summary

| Tool | Feature Location | Operations | Purpose |
|------|------------------|------------|---------|
| `obsidian_manage_notes` | `features/notes/tools.py` | 6 | Note lifecycle + task completion |
| `obsidian_query_vault` | `features/search/tools.py` | 7 | Search, discovery, retrieval |
| `obsidian_manage_structure` | `features/structure/tools.py` | 5 | Folder organization |

**Total: 3 tools, 17 operations**

---

## Tool 1: `obsidian_manage_notes`

### Purpose

Manages all note lifecycle operations including reading, creating, updating, and deleting notes. Also handles task completion (marking checkboxes as done). Supports both single-note and bulk operations.

### Location

`features/notes/tools.py`

### Signature

```python
@agent.tool
def obsidian_manage_notes(
    ctx: RunContext[VaultDependencies],
    operation: Literal["read", "create", "update", "append", "delete", "complete_task"],
    path: str,
    content: Optional[str] = None,
    folder: Optional[str] = None,
    task_identifier: Optional[str] = None,
    bulk: bool = False,
    items: Optional[List[Dict[str, Any]]] = None,
) -> NoteOperationResult:
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `operation` | `Literal["read", "create", "update", "append", "delete", "complete_task"]` | Yes | - | The operation to perform |
| `path` | `str` | Yes | - | Note path relative to vault root (e.g., `"projects/my-project.md"`) |
| `content` | `str` | Conditional | `None` | Note content. Required for `create`, `update`, `append` |
| `folder` | `str` | No | `None` | Target folder for `create` operation |
| `task_identifier` | `str` | Conditional | `None` | Task text or line number for `complete_task`. Required for that operation |
| `bulk` | `bool` | No | `False` | Enable bulk mode for multiple operations |
| `items` | `List[Dict]` | Conditional | `None` | List of operation items for bulk mode. Required when `bulk=True` |

### Operations

| Operation | Required Params | Optional Params | Description |
|-----------|-----------------|-----------------|-------------|
| `read` | `path` | - | Read and return the contents of a note |
| `create` | `path`, `content` | `folder` | Create a new note at the specified path |
| `update` | `path`, `content` | - | Replace the entire content of an existing note |
| `append` | `path`, `content` | - | Add content to the end of an existing note |
| `delete` | `path` | - | Delete a note from the vault |
| `complete_task` | `path`, `task_identifier` | - | Mark a task checkbox as complete (`- [ ]` → `- [x]`) |

### Return Type

```python
class NoteOperationResult(BaseModel):
    success: bool
    operation: str
    path: str
    message: str
    content: Optional[str] = None  # Populated for read operations
    affected_count: Optional[int] = None  # For bulk operations
```

### Usage Examples

**Read a note:**
```python
obsidian_manage_notes(
    operation="read",
    path="projects/website-redesign.md"
)
```

**Create a note:**
```python
obsidian_manage_notes(
    operation="create",
    path="meetings/2024-01-15-standup.md",
    content="# Standup Notes\n\n## Updates\n\n- Item 1\n- Item 2"
)
```

**Create a note in a specific folder:**
```python
obsidian_manage_notes(
    operation="create",
    path="new-idea.md",
    folder="inbox",
    content="# New Idea\n\nCapture this thought..."
)
```

**Append to a note:**
```python
obsidian_manage_notes(
    operation="append",
    path="journal/2024-01.md",
    content="\n\n## January 15\n\nToday I learned..."
)
```

**Complete a task:**
```python
obsidian_manage_notes(
    operation="complete_task",
    path="daily/2024-01-15.md",
    task_identifier="Buy groceries"  # Matches task text
)
```

**Bulk create notes:**
```python
obsidian_manage_notes(
    operation="create",
    path="",  # Ignored in bulk mode
    bulk=True,
    items=[
        {"path": "notes/note1.md", "content": "# Note 1"},
        {"path": "notes/note2.md", "content": "# Note 2"},
        {"path": "notes/note3.md", "content": "# Note 3"},
    ]
)
```

### Error Handling

| Error Condition | Response |
|-----------------|----------|
| Note not found (read/update/append/delete) | `{"success": false, "message": "Note not found: {path}. Verify the path exists using obsidian_query_vault with operation='list_notes'"}` |
| Note already exists (create) | `{"success": false, "message": "Note already exists: {path}. Use operation='update' to modify existing notes"}` |
| Missing content (create/update/append) | `{"success": false, "message": "Content is required for {operation} operation"}` |
| Task not found (complete_task) | `{"success": false, "message": "Task not found: '{task_identifier}'. List tasks first using obsidian_query_vault with operation='list_tasks'"}` |
| Path outside vault | `{"success": false, "message": "Access denied: Path must be within vault root"}` |

---

## Tool 2: `obsidian_query_vault`

### Purpose

Handles all search, discovery, and retrieval operations. Find notes by content, tags, or relationships. List vault structure. Discover tasks across the vault.

### Location

`features/search/tools.py`

### Signature

```python
@agent.tool
def obsidian_query_vault(
    ctx: RunContext[VaultDependencies],
    operation: Literal["search_text", "find_by_tag", "list_notes", "list_folders",
                       "get_backlinks", "get_tags", "list_tasks"],
    query: Optional[str] = None,
    path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    include_completed: bool = False,
    response_format: Literal["detailed", "concise"] = "concise",
    limit: int = 50,
) -> QueryResult:
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `operation` | `Literal["search_text", "find_by_tag", "list_notes", "list_folders", "get_backlinks", "get_tags", "list_tasks"]` | Yes | - | The query operation to perform |
| `query` | `str` | Conditional | `None` | Search query string. Required for `search_text` |
| `path` | `str` | No | `None` | Scope query to a specific folder or note |
| `tags` | `List[str]` | Conditional | `None` | List of tags to search for. Required for `find_by_tag` |
| `include_completed` | `bool` | No | `False` | Include completed tasks in `list_tasks` results |
| `response_format` | `Literal["detailed", "concise"]` | No | `"concise"` | Level of detail in response |
| `limit` | `int` | No | `50` | Maximum number of results to return |

### Operations

| Operation | Required Params | Optional Params | Description |
|-----------|-----------------|-----------------|-------------|
| `search_text` | `query` | `path`, `limit`, `response_format` | Full-text search across vault |
| `find_by_tag` | `tags` | `path`, `limit`, `response_format` | Find notes containing specified tags |
| `list_notes` | - | `path`, `limit`, `response_format` | List all notes in vault or folder |
| `list_folders` | - | `path` | List folder structure |
| `get_backlinks` | `path` | `limit`, `response_format` | Find notes that link to specified note |
| `get_tags` | - | - | Get all unique tags in vault |
| `list_tasks` | - | `path`, `include_completed`, `limit` | Find tasks (checkboxes) across vault |

### Return Type

```python
class QueryResult(BaseModel):
    success: bool
    operation: str
    total_count: int
    results: List[QueryResultItem]
    truncated: bool  # True if results exceeded limit

class QueryResultItem(BaseModel):
    path: str
    title: Optional[str] = None
    snippet: Optional[str] = None  # For detailed response_format
    tags: Optional[List[str]] = None
    modified: Optional[datetime] = None
    task_text: Optional[str] = None  # For list_tasks
    task_completed: Optional[bool] = None  # For list_tasks
    line_number: Optional[int] = None  # For tasks and search results
```

### Response Format Behavior

| Format | Behavior |
|--------|----------|
| `concise` | Returns paths, titles, and minimal metadata. Lower token usage. |
| `detailed` | Includes content snippets, full metadata, and context. Higher token usage. |

### Usage Examples

**Search for text:**
```python
obsidian_query_vault(
    operation="search_text",
    query="project planning",
    response_format="detailed",
    limit=10
)
```

**Search within a folder:**
```python
obsidian_query_vault(
    operation="search_text",
    query="budget",
    path="projects/",
    response_format="concise"
)
```

**Find notes by tag:**
```python
obsidian_query_vault(
    operation="find_by_tag",
    tags=["work", "urgent"]
)
```

**List all notes:**
```python
obsidian_query_vault(
    operation="list_notes",
    response_format="concise",
    limit=100
)
```

**List notes in a folder:**
```python
obsidian_query_vault(
    operation="list_notes",
    path="projects/",
    response_format="detailed"
)
```

**Get backlinks to a note:**
```python
obsidian_query_vault(
    operation="get_backlinks",
    path="concepts/zettelkasten.md"
)
```

**Get all tags:**
```python
obsidian_query_vault(
    operation="get_tags"
)
```

**List incomplete tasks:**
```python
obsidian_query_vault(
    operation="list_tasks",
    include_completed=False
)
```

**List tasks in a specific folder:**
```python
obsidian_query_vault(
    operation="list_tasks",
    path="projects/website/",
    include_completed=True
)
```

### Error Handling

| Error Condition | Response |
|-----------------|----------|
| Missing query (search_text) | `{"success": false, "message": "Query parameter is required for search_text operation"}` |
| Missing tags (find_by_tag) | `{"success": false, "message": "Tags parameter is required for find_by_tag operation"}` |
| Invalid path | `{"success": false, "message": "Path not found: {path}. Use operation='list_folders' to see available paths"}` |
| No results | `{"success": true, "total_count": 0, "results": [], "message": "No results found. Try broadening your search."}` |

---

## Tool 3: `obsidian_manage_structure`

### Purpose

Manages vault folder structure. Create, rename, move, and delete folders. Supports bulk operations for reorganizing multiple items at once.

### Location

`features/structure/tools.py`

### Signature

```python
@agent.tool
def obsidian_manage_structure(
    ctx: RunContext[VaultDependencies],
    operation: Literal["create_folder", "rename", "delete_folder", "move", "list_structure"],
    path: str,
    new_path: Optional[str] = None,
    bulk: bool = False,
    items: Optional[List[Dict[str, str]]] = None,
    force: bool = False,
) -> StructureOperationResult:
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `operation` | `Literal["create_folder", "rename", "delete_folder", "move", "list_structure"]` | Yes | - | The structure operation to perform |
| `path` | `str` | Yes | - | Target path (folder or note) |
| `new_path` | `str` | Conditional | `None` | Destination path. Required for `rename` and `move` |
| `bulk` | `bool` | No | `False` | Enable bulk mode for multiple operations |
| `items` | `List[Dict[str, str]]` | Conditional | `None` | List of `{path, new_path}` for bulk operations |
| `force` | `bool` | No | `False` | Force deletion of non-empty folders |

### Operations

| Operation | Required Params | Optional Params | Description |
|-----------|-----------------|-----------------|-------------|
| `create_folder` | `path` | - | Create a new folder (including nested) |
| `rename` | `path`, `new_path` | `bulk`, `items` | Rename a folder or note |
| `delete_folder` | `path` | `force` | Delete a folder (must be empty unless `force=True`) |
| `move` | `path`, `new_path` | `bulk`, `items` | Move a note or folder to new location |
| `list_structure` | - | `path` | Get folder tree structure |

### Return Type

```python
class StructureOperationResult(BaseModel):
    success: bool
    operation: str
    path: str
    new_path: Optional[str] = None
    message: str
    affected_count: Optional[int] = None  # For bulk operations
    structure: Optional[List[FolderNode]] = None  # For list_structure

class FolderNode(BaseModel):
    name: str
    path: str
    type: Literal["folder", "note"]
    children: Optional[List[FolderNode]] = None
```

### Usage Examples

**Create a folder:**
```python
obsidian_manage_structure(
    operation="create_folder",
    path="projects/new-project"
)
```

**Create nested folders:**
```python
obsidian_manage_structure(
    operation="create_folder",
    path="archive/2024/q1/reports"  # Creates all intermediate folders
)
```

**Rename a folder:**
```python
obsidian_manage_structure(
    operation="rename",
    path="projects/old-name",
    new_path="projects/new-name"
)
```

**Rename a note:**
```python
obsidian_manage_structure(
    operation="rename",
    path="inbox/untitled.md",
    new_path="inbox/meeting-notes-jan-15.md"
)
```

**Move a note:**
```python
obsidian_manage_structure(
    operation="move",
    path="inbox/processed-note.md",
    new_path="archive/processed-note.md"
)
```

**Move a folder:**
```python
obsidian_manage_structure(
    operation="move",
    path="projects/completed-project",
    new_path="archive/2024/completed-project"
)
```

**Delete an empty folder:**
```python
obsidian_manage_structure(
    operation="delete_folder",
    path="temp/scratch"
)
```

**Delete a non-empty folder (force):**
```python
obsidian_manage_structure(
    operation="delete_folder",
    path="old-archive",
    force=True
)
```

**List vault structure:**
```python
obsidian_manage_structure(
    operation="list_structure",
    path=""  # Root of vault
)
```

**List structure of a specific folder:**
```python
obsidian_manage_structure(
    operation="list_structure",
    path="projects/"
)
```

**Bulk move notes:**
```python
obsidian_manage_structure(
    operation="move",
    path="",  # Ignored in bulk mode
    bulk=True,
    items=[
        {"path": "inbox/note1.md", "new_path": "archive/note1.md"},
        {"path": "inbox/note2.md", "new_path": "archive/note2.md"},
        {"path": "inbox/note3.md", "new_path": "projects/note3.md"},
    ]
)
```

**Bulk rename:**
```python
obsidian_manage_structure(
    operation="rename",
    path="",
    bulk=True,
    items=[
        {"path": "meetings/meeting1.md", "new_path": "meetings/2024-01-15-standup.md"},
        {"path": "meetings/meeting2.md", "new_path": "meetings/2024-01-16-planning.md"},
    ]
)
```

### Error Handling

| Error Condition | Response |
|-----------------|----------|
| Folder already exists (create_folder) | `{"success": false, "message": "Folder already exists: {path}"}` |
| Path not found (rename/move/delete) | `{"success": false, "message": "Path not found: {path}. Use operation='list_structure' to see available paths"}` |
| Destination exists (rename/move) | `{"success": false, "message": "Destination already exists: {new_path}. Choose a different name or delete the existing item first"}` |
| Non-empty folder (delete_folder) | `{"success": false, "message": "Folder is not empty: {path}. Use force=True to delete non-empty folders, or empty the folder first"}` |
| Missing new_path (rename/move) | `{"success": false, "message": "new_path is required for {operation} operation"}` |
| Path outside vault | `{"success": false, "message": "Access denied: Path must be within vault root"}` |

---

## Bulk Operations Pattern

All tools that support bulk operations follow a consistent pattern:

### Enabling Bulk Mode

1. Set `bulk=True`
2. Provide `items` as a list of dictionaries
3. The primary `path` parameter is ignored in bulk mode

### Items Format

Each item in the `items` list should contain the parameters needed for a single operation:

**For `obsidian_manage_notes`:**
```python
items=[
    {"path": "note1.md", "content": "Content 1"},
    {"path": "note2.md", "content": "Content 2"},
]
```

**For `obsidian_manage_structure` (move/rename):**
```python
items=[
    {"path": "source1.md", "new_path": "dest1.md"},
    {"path": "source2.md", "new_path": "dest2.md"},
]
```

### Bulk Response

Bulk operations return `affected_count` indicating how many items were processed:

```python
{
    "success": true,
    "operation": "create",
    "message": "Bulk operation completed",
    "affected_count": 5
}
```

### Partial Failures

If some items in a bulk operation fail:

```python
{
    "success": false,
    "operation": "move",
    "message": "Bulk operation partially completed",
    "affected_count": 3,
    "errors": [
        {"path": "note4.md", "error": "File not found"},
        {"path": "note5.md", "error": "Destination exists"}
    ]
}
```

---

## Implementation Notes

### Docker Volume Context

Jasque runs inside a Docker container with the vault mounted at `/vault`:

```
Host Machine                    Docker Container
─────────────────────────────   ─────────────────────────────
$OBSIDIAN_VAULT_PATH/     <-->  /vault/
├── notes/                      ├── notes/
├── projects/                   ├── projects/
└── daily/                      └── daily/
```

**Key Points:**
- All tool paths are relative to `/vault` inside the container
- Changes sync bidirectionally in real-time (`:rw` mount)
- Container cannot access any paths outside `/vault`

### VaultManager Integration

All tools delegate filesystem operations to `shared/vault/manager.py`:

```python
from pathlib import Path

class VaultManager:
    def __init__(self, vault_path: Path = Path("/vault")):
        """Initialize with container vault path (default: /vault)."""
        self.vault_path = vault_path

    def read_note(self, path: str) -> str: ...
    def write_note(self, path: str, content: str) -> None: ...
    def delete_note(self, path: str) -> None: ...
    def search(self, query: str) -> List[SearchResult]: ...
    def list_notes(self, folder: Optional[str]) -> List[NoteInfo]: ...
    # ... etc
```

### Path Validation

All paths must be validated to prevent traversal attacks (even with Docker sandboxing):

```python
def validate_path(self, path: str) -> Path:
    """Ensure path is within vault root (/vault in container)."""
    full_path = (self.vault_path / path).resolve()
    if not full_path.is_relative_to(self.vault_path):
        raise PathTraversalError(f"Access denied: {path}")
    return full_path
```

**Defense in Depth:** Docker volume mounting provides OS-level sandboxing, but path validation adds application-level protection against `../` traversal attempts.

### Task Identification

Tasks are identified by either:
1. **Line number:** `task_identifier="15"` (line 15)
2. **Task text:** `task_identifier="Buy groceries"` (matches task content)

The tool should first try to parse as integer (line number), then fall back to text matching.

### Obsidian Markdown Conventions

- **Wikilinks:** `[[note-name]]` or `[[folder/note|Display Text]]`
- **Tags:** `#tag` inline or in frontmatter
- **Tasks:** `- [ ] incomplete` and `- [x] complete`
- **Frontmatter:** YAML between `---` delimiters at file start

---

## Tool Description Templates

These descriptions should be used in the `@agent.tool` decorator for optimal LLM understanding:

### obsidian_manage_notes

```
Manage notes in the Obsidian vault. Perform CRUD operations on notes and complete tasks.

Operations:
- read: Get the full contents of a note
- create: Create a new note with content (fails if exists)
- update: Replace entire note content (fails if not exists)
- append: Add content to the end of an existing note
- delete: Permanently remove a note from the vault
- complete_task: Mark a task checkbox as done (- [ ] becomes - [x])

For bulk operations on multiple notes, set bulk=True and provide items list.

Examples:
- Read: operation="read", path="projects/roadmap.md"
- Create: operation="create", path="notes/idea.md", content="# My Idea\n\nDetails..."
- Complete task: operation="complete_task", path="daily/today.md", task_identifier="Buy milk"
```

### obsidian_query_vault

```
Search and query the Obsidian vault. Find notes, discover connections, and list tasks.

Operations:
- search_text: Full-text search across all notes (requires query)
- find_by_tag: Find notes with specific tags (requires tags list)
- list_notes: List notes in vault or specific folder
- list_folders: Get folder structure
- get_backlinks: Find notes that link to a specific note
- get_tags: Get all unique tags used in vault
- list_tasks: Find task checkboxes across vault

Use response_format="concise" for brief results, "detailed" for full content.
Use limit to control result count.

Examples:
- Search: operation="search_text", query="meeting notes"
- Tags: operation="find_by_tag", tags=["project", "active"]
- Tasks: operation="list_tasks", path="projects/", include_completed=False
```

### obsidian_manage_structure

```
Manage vault folder structure. Create, rename, move, and delete folders.

Operations:
- create_folder: Create a new folder (creates parent folders as needed)
- rename: Rename a folder or note (requires new_path)
- delete_folder: Delete a folder (use force=True for non-empty)
- move: Move a note or folder to new location (requires new_path)
- list_structure: Get the folder tree of the vault

For bulk move/rename operations, set bulk=True and provide items list.

Examples:
- Create: operation="create_folder", path="projects/new-project"
- Move: operation="move", path="inbox/note.md", new_path="archive/note.md"
- Delete: operation="delete_folder", path="temp", force=True
```

---

*Document Version: 1.1*
*Consistent with: PRD.md v1.1*
*Agent Name: Jasque*
