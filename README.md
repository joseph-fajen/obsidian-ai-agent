# Jasque

**AI agent for Obsidian vault management via natural language.**

Jasque provides an OpenAI-compatible API that enables natural language interaction with your Obsidian vault through the Obsidian Copilot plugin.

## Features

- **Natural Language Vault Management** - Create, read, update, and delete notes using conversation
- **Smart Search & Discovery** - Full-text search, tag filtering, backlinks, and task discovery
- **Task Management** - List incomplete tasks across your vault and mark them complete
- **Folder Organization** - Create, move, rename, and delete folders
- **Bulk Operations** - Process multiple notes or folders in a single request
- **OpenAI-Compatible API** - Works with Obsidian Copilot and other OpenAI-compatible clients

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo>
cd jasque

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env to set:
#   - OBSIDIAN_VAULT_PATH (path to your Obsidian vault)
#   - ANTHROPIC_API_KEY (your Anthropic API key)

# 4. Start PostgreSQL
docker-compose up -d db

# 5. Run migrations
uv run alembic upgrade head

# 6. Start the server
uv run uvicorn app.main:app --reload --port 8123
```

Visit `http://localhost:8123/docs` for the API documentation.

## The 3 Tools

Jasque provides 3 consolidated tools following [Anthropic's best practices](https://www.anthropic.com/engineering/writing-tools-for-agents):

| Tool | Operations | Purpose |
|------|------------|---------|
| `obsidian_manage_notes` | read, create, update, append, delete, complete_task | Note lifecycle + tasks |
| `obsidian_query_vault` | search_text, find_by_tag, list_notes, list_folders, get_backlinks, get_tags, list_tasks | Search & discovery |
| `obsidian_manage_structure` | create_folder, rename, delete_folder, move, list_structure | Folder organization |

## Architecture

Built with vertical slice architecture, optimized for AI-assisted development:

```
app/
├── core/           # Infrastructure (config, database, logging, middleware)
├── shared/         # Cross-feature utilities (vault manager, pagination)
├── features/       # Vertical slices (chat/, notes/, search/, structure/)
└── main.py         # FastAPI application entry point
```

## Tech Stack

- **Agent Framework**: Pydantic AI with Anthropic Claude
- **API**: FastAPI with OpenAI-compatible endpoints
- **Database**: PostgreSQL with SQLAlchemy + Alembic
- **Vault Access**: Docker volume mount (sandboxed)
- **Type Safety**: Strict MyPy + Pyright

## Docker Deployment

```bash
# Build and start all services (API + PostgreSQL)
docker-compose up -d --build

# View logs
docker-compose logs -f app
```

The Obsidian vault is mounted at `/vault` inside the container, configured via `OBSIDIAN_VAULT_PATH` in your `.env` file.

## Observability (Datadog)

Enable Datadog LLM Observability to monitor agent behavior, LLM calls, and performance.

### Prerequisites

1. [Create a Datadog account](https://www.datadoghq.com/) (free tier available)
2. Get your API key from [Organization Settings](https://app.datadoghq.com/organization-settings/api-keys)
3. Add to your `.env` file:

```bash
DD_API_KEY=your-api-key
DD_SITE=datadoghq.com
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=jasque
DD_LLMOBS_AGENTLESS_ENABLED=1
```

### Local Development

Run with the `ddtrace-run` wrapper:

```bash
# Install dependencies (includes ddtrace)
uv sync

# Run with Datadog tracing enabled
ddtrace-run uv run uvicorn app.main:app --port 8123
```

### Docker

Use the observability override file:

```bash
# Start with Datadog tracing enabled
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d --build

# View logs
docker-compose logs -f app
```

### What You'll See in Datadog

- **LLM Observability**: Agent runs, tool calls, LLM request/response traces
- **APM**: HTTP request traces, database queries, error tracking
- **Metrics**: Latency, token usage, error rates

View traces at: [LLM Observability](https://app.datadoghq.com/llm) | [APM Traces](https://app.datadoghq.com/apm/traces)

## Development Commands

```bash
# Run tests
uv run pytest -v

# Type checking
uv run mypy app/
uv run pyright app/

# Linting
uv run ruff check .
uv run ruff format .

# Database migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Path to your Obsidian vault on the host |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DATABASE_URL` | PostgreSQL connection string |

## Documentation

- `.agents/reference/PRD.md` - Product requirements and architecture
- `.agents/reference/mvp-tool-designs.md` - Detailed tool specifications
- `CLAUDE.md` - Development guidelines

## Status

**Current Phase:** Scaffolding Complete, Core Infrastructure Next

See `CURRENT_STATE.md` for detailed progress tracking.

## License

MIT
