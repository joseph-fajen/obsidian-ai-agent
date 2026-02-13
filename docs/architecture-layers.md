# Jasque Architecture Layers

This document provides a technical deep-dive into Jasque's infrastructure. It explains each layer of the application, what it does, and how the pieces fit together.

**MVP Status:** February 2026 - Infrastructure complete, all tools implemented, 333 tests passing.

---

## Origin: FastAPI Starter Template

Jasque's infrastructure came from the [fastapi-starter-for-ai-coding](https://github.com/dynamous-community/fastapi-starter-for-ai-coding) template, integrated in commit `8c9e6fe` (January 2026).

The template provided:
- Application structure (vertical slice architecture)
- Database setup (PostgreSQL + SQLAlchemy + Alembic)
- Logging, middleware, health checks, exception handling
- Development tooling (ruff, mypy, pyright, pytest)
- Docker configuration
- ~75 unit tests for infrastructure

Jasque added on top:
- Pydantic AI agent with tools
- VaultManager for file operations
- OpenAI-compatible API endpoints
- The 3 Obsidian tools

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        app/main.py                          │
│                    (Entry Point)                            │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────-┐
│   app/core/     │ │  app/shared/    │ │  app/features/   │
│ (Infrastructure)│ │  (Utilities)    │ │ (Vertical Slices)│
└─────────────────┘ └─────────────────┘ └─────────────────-┘
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ config.py   │      │ models.py   │      │ chat/       │
│ database.py │      │ schemas.py  │      │ obsidian_*/ │
│ logging.py  │      │ vault/      │      │             │
│ middleware  │      └─────────────┘      └─────────────┘
│ health.py   │
│ exceptions  │
│ agents/     │
└─────────────┘
```

---

## Layer 1: Configuration (`app/core/config.py`)

**Purpose:** Centralized settings management via environment variables.

**Problem it solves:** Your app needs configuration values (database URL, API keys, vault path) that differ between development, testing, and production. Hardcoding these would be inflexible and insecure.

**How it works:**
1. Defines a `Settings` class with all configurable values
2. Each setting has a type and optional default
3. At startup, reads from `.env` file and environment variables
4. `get_settings()` returns a cached singleton instance

**Key Jasque settings:**
```python
obsidian_vault_path: str = "/vault"           # Where vault is mounted
llm_model: str = "anthropic:claude-sonnet-4-5" # LLM provider:model
anthropic_api_key: str | None = None          # API keys for providers
allowed_origins: list[str] = [...]            # CORS (includes app://obsidian.md)
```

**Location:** `app/core/config.py`

---

## Layer 2: Database (`app/core/database.py`)

**Purpose:** PostgreSQL connection management with async SQLAlchemy.

**Problem it solves:** Opening a new database connection for every request is slow. You need connection pooling and proper session lifecycle management.

**How it works:**
1. **Engine:** Creates a connection pool (5 connections, 10 overflow)
2. **Session factory:** Template for creating database sessions
3. **Base class:** All models inherit from this for SQLAlchemy to track them
4. **`get_db()`:** Dependency that provides a session per request and cleans up afterward

**Current status in Jasque:** The database infrastructure exists but is **not actively used**. All vault operations are file-based. The database is scaffolded for future features like:
- Chat history persistence
- User preferences
- Analytics

**Location:** `app/core/database.py`

---

## Layer 3: Logging (`app/core/logging.py`)

**Purpose:** Structured JSON logging optimized for machine parsing.

**Problem it solves:** Traditional text logs are hard for programs to parse. Since Jasque is an AI agent, its logs might be analyzed by other AI systems.

**How it works:**
1. **JSON output:** Logs are structured data, not text strings
2. **Request ID correlation:** Every request gets a unique ID for tracing
3. **Event naming:** `domain.component.action_state` pattern

**Example output:**
```json
{
  "event": "vault.notes.create_completed",
  "path": "meetings/2026-01-14.md",
  "request_id": "abc-123",
  "timestamp": "2026-01-14T10:30:00Z"
}
```

**Location:** `app/core/logging.py`

---

## Layer 4: Middleware (`app/core/middleware.py`)

**Purpose:** Code that runs before/after every HTTP request.

**Problem it solves:** Every request needs common handling: assign a request ID, log arrival, measure timing, log completion, handle CORS.

**Think of it like:** A receptionist at an office. Every visitor (request) checks in, gets a visitor badge (request ID), and the receptionist notes arrival/departure times.

**What it does:**
1. Extracts or generates `X-Request-ID` header
2. Logs `request.http_received` with method, path, client info
3. Calls the actual route handler
4. Logs `request.http_completed` with status code and duration
5. Handles CORS headers (critical for Obsidian Copilot at `app://obsidian.md`)

**Location:** `app/core/middleware.py`

---

## Layer 5: Health Checks (`app/core/health.py`)

**Purpose:** Endpoints for monitoring systems to verify the app is running.

**Problem it solves:** Docker, Kubernetes, and monitoring tools need a simple way to ask "are you OK?"

**Endpoints:**
| Endpoint | What It Checks |
|----------|----------------|
| `/health` | Is the API process running? |
| `/health/db` | Can we connect to PostgreSQL? |
| `/health/ready` | Combined readiness check |

**Location:** `app/core/health.py`

---

## Layer 6: Exception Handling (`app/core/exceptions.py`)

**Purpose:** Convert errors into proper HTTP responses with helpful messages.

**Problem it solves:** When something goes wrong, you want consistent error responses, not crashes or stack traces shown to users.

**How it works:**
1. **Custom exceptions:** Define specific error types (`NotFoundError`, `ValidationError`)
2. **Global handlers:** Catch these anywhere and convert to JSON responses with appropriate HTTP status codes

**Example flow:**
1. Code throws `NotFoundError("Note not found: projects/foo.md")`
2. Global handler catches it
3. Returns `{"error": "Note not found: projects/foo.md"}` with HTTP 404

**Location:** `app/core/exceptions.py`

---

## Layer 7: Agent Infrastructure (`app/core/agents/`)

**Purpose:** Pydantic AI agent setup and configuration.

**What it provides:**
- `base.py`: Agent creation, LLM provider configuration, system prompt
- `types.py`: Type definitions (`AgentDependencies`, `TokenUsage`)

**Key functions:**
- `configure_llm_provider()`: Sets up the LLM based on `LLM_MODEL` setting
- `create_agent()`: Creates the Pydantic AI agent with tools
- `get_agent()`: Singleton accessor

**Location:** `app/core/agents/`

---

## Layer 8: Shared Utilities (`app/shared/`)

**Purpose:** Reusable code used by multiple features.

**Components:**

### `models.py` - Database Mixins
- `TimestampMixin`: Adds `created_at` and `updated_at` to any model

### `schemas.py` - Common Data Structures
- Pagination schemas (for paged results)
- Error response schemas (consistent error format)

### `vault/` - VaultManager (Jasque-specific)
This is where the actual vault operations live:

| Category | Methods |
|----------|---------|
| **Query** | `list_notes`, `list_folders`, `read_note`, `search_text`, `find_by_tag`, `get_backlinks`, `get_tags`, `list_tasks` |
| **CRUD** | `create_note`, `update_note`, `append_to_note`, `delete_note`, `complete_task` |
| **Structure** | `create_folder`, `rename`, `delete_folder`, `move`, `list_structure` |

**Location:** `app/shared/`

---

## Layer 9: Entry Point (`app/main.py`)

**Purpose:** Assemble all components into a running FastAPI application.

**What it does:**
```python
# Create the app
app = FastAPI(title="Jasque", lifespan=lifespan)

# Wire up middleware
setup_middleware(app)

# Wire up exception handlers
setup_exception_handlers(app)

# Wire up routes
app.include_router(health_router)           # /health, /health/db
app.include_router(chat_router, prefix="/api/v1")  # /api/v1/chat/test
app.include_router(openai_router, prefix="/v1")    # /v1/chat/completions
```

**Lifespan events:**
- **Startup:** Configure logging, initialize database, configure LLM provider, create agent
- **Shutdown:** Close database connections

**Location:** `app/main.py`

---

## Layer 10: Features (`app/features/`)

**Purpose:** Vertical slices of functionality - each feature owns its own code.

**Structure:**
```
app/features/
├── chat/                      # API endpoints
│   ├── routes.py              # Test endpoint
│   ├── openai_routes.py       # /v1/chat/completions
│   ├── openai_schemas.py      # OpenAI request/response models
│   ├── streaming.py           # SSE stream generation
│   └── tests/
│
├── obsidian_query_vault/      # Search & discovery tool
│   ├── obsidian_query_vault_tool.py
│   ├── obsidian_query_vault_schemas.py
│   └── tests/
│
├── obsidian_manage_notes/     # Note CRUD tool
│   ├── obsidian_manage_notes_tool.py
│   ├── obsidian_manage_notes_schemas.py
│   └── tests/
│
└── obsidian_manage_structure/ # Folder management tool
    ├── obsidian_manage_structure_tool.py
    ├── obsidian_manage_structure_schemas.py
    └── tests/
```

**Vertical Slice Architecture means:**
- Each feature is self-contained
- Features don't import from each other
- Shared code goes in `app/shared/` only when used by 3+ features

---

## Docker: The Runtime Environment

Docker packages Jasque and its dependencies into **containers** - self-contained units that run identically on any machine.

### The Problem Docker Solves

Without Docker, running Jasque requires:
- Python 3.12 installed correctly
- PostgreSQL installed and configured
- All Python packages installed
- Correct environment variables

If any of these differ between machines, you get the "works on my machine" problem.

Docker solves this by packaging everything together:

```
┌─────────────────────────────────────────┐
│            Docker Container             │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Jasque Application             │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  Python 3.12                    │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  All Python packages            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  Linux operating system         │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Container vs. Virtual Machine

| Aspect | Virtual Machine | Docker Container |
|--------|-----------------|------------------|
| Size | Gigabytes (full OS) | Megabytes (just what's needed) |
| Startup | Minutes | Seconds |
| Resources | Heavy (runs full OS) | Light (shares host kernel) |
| Isolation | Complete | Process-level |

### Jasque's Docker Setup

The `docker-compose.yml` defines two containers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Computer                           │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │   db container   │      │  app container   │            │
│  │                  │      │                  │            │
│  │   PostgreSQL     │◄────►│     Jasque       │            │
│  │   Database       │      │     (Python)     │            │
│  │                  │      │                  │            │
│  │   Port 5432      │      │   Port 8123      │            │
│  └──────────────────┘      └──────────────────┘            │
│         │                          │                        │
│    Port 5433                  Port 8123                     │
│    (exposed)                  (exposed)                     │
│                                    │                        │
│                          ┌────────────────────┐            │
│                          │  Your Obsidian     │            │
│                          │  Vault (mounted)   │            │
│                          │  as /vault         │            │
│                          └────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Key Configuration Concepts

**Port Mapping:**
```yaml
ports:
  - "8123:8123"  # host:container
```
Connects port 8123 on your machine to port 8123 inside the container. This is why `http://localhost:8123` reaches Jasque.

**Volume Mounting (critical for vault access):**
```yaml
volumes:
  - ${OBSIDIAN_VAULT_PATH}:/vault:rw
```
- Takes your vault folder on the host (e.g., `/Users/you/Documents/MyVault`)
- Makes it appear inside the container at `/vault`
- `:rw` means read-write (bidirectional sync)

This is how Jasque accesses your Obsidian vault without files being copied into the container.

**Environment Override:**
```yaml
env_file:
  - .env
environment:
  - OBSIDIAN_VAULT_PATH=/vault  # Override for container context
```
The `.env` file contains your host path (for volume mounting). The override tells the app to look at `/vault` inside the container.

**Service Dependencies:**
```yaml
depends_on:
  db:
    condition: service_healthy
```
Ensures PostgreSQL is healthy before Jasque starts.

### Security: Sandboxed Access

The Jasque container can only access:
1. Its own code (`/app`)
2. Your vault (`/vault`)
3. Network (database, internet for LLM API)

It cannot read your Documents folder, Desktop, or anything else. This sandboxing limits potential damage from bugs.

### Common Docker Commands

```bash
# Start both containers in background
docker compose up -d

# View running containers
docker compose ps

# View Jasque logs
docker compose logs -f app

# Stop everything
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

### Running Without Docker

You can run Jasque directly if preferred:

```bash
# Start PostgreSQL separately, then:
uv run uvicorn app.main:app --reload --port 8123
```

But Docker simplifies setup and ensures consistent environments.

**Location:** `Dockerfile`, `docker-compose.yml`

---

## What's Used vs. Scaffolded

| Component | Status | Notes |
|-----------|--------|-------|
| Configuration | **Active** | All settings in use |
| Database | **Scaffolded** | Infrastructure ready, no tables defined |
| Logging | **Active** | All requests logged |
| Middleware | **Active** | Request tracking, CORS |
| Health checks | **Active** | Used by Docker |
| Exception handling | **Active** | Global error handling |
| Agent | **Active** | Powers all interactions |
| VaultManager | **Active** | All 18 operations implemented |
| Features | **Active** | All 3 tools + chat endpoints |

The database layer is the main "scaffolded for future" component. When features like chat history are added, the infrastructure is ready.

---

## Request Flow Example

When you ask "What notes do I have about Python?" in Obsidian Copilot:

1. **Copilot** sends POST to `http://localhost:8123/v1/chat/completions`
2. **Middleware** logs `request.http_received`, assigns request ID
3. **Route handler** (`openai_routes.py`) receives the request
4. **Agent** (Pydantic AI) processes the message
5. **LLM** (Claude/Gemini) decides to call `obsidian_query_vault` with `operation="search_text"`
6. **Tool** calls `VaultManager.search_text("Python")`
7. **VaultManager** searches `.md` files in the vault directory
8. **Results** flow back through the agent to the response
9. **Streaming** sends SSE chunks back to Copilot
10. **Middleware** logs `request.http_completed` with timing

---

## Learn More

- [About Jasque](./about-jasque.md) - Conceptual overview and value proposition
- [CLAUDE.md](../CLAUDE.md) - Development conventions
- [PRD](../.agents/reference/PRD.md) - Full product requirements
