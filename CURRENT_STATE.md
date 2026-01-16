# Jasque - Current State

**Last Updated:** 2026-01-16

---

## Development Phase

```
[x] Planning & Research
[x] PRD & Tool Design
[x] Project Scaffolding
[x] Core Infrastructure (Base Agent)
[x] API Implementation (OpenAI-compatible)
[x] Tool Implementation
[x] Integration Testing
[ ] Documentation
[ ] Deployment
```

**Current Phase:** MVP Complete + Memory Phase 1 - Vault-based preferences implemented

---

## Implementation Status

### Core Infrastructure (from FastAPI template)

| Component | Status | Notes |
|-----------|--------|-------|
| `main.py` | ✅ Complete | FastAPI entry point with health routes + chat router |
| `core/config.py` | ✅ Complete | pydantic-settings + LLM_MODEL (multi-provider) |
| `core/database.py` | ✅ Complete | Async SQLAlchemy setup |
| `core/logging.py` | ✅ Complete | Structlog JSON logging |
| `core/middleware.py` | ✅ Complete | Request ID, CORS middleware |
| `core/health.py` | ✅ Complete | Health check endpoints |
| `core/exceptions.py` | ✅ Complete | Exception handlers |
| `core/agents/` | ✅ Complete | Pydantic AI agent package |
| `core/agents/base.py` | ✅ Complete | configure_llm_provider() + create_agent() + get_agent() singleton |
| `core/agents/types.py` | ✅ Complete | AgentDependencies, TokenUsage |
| `core/dependencies.py` | Not started | VaultDependencies |

### Shared Utilities

| Component | Status | Notes |
|-----------|--------|-------|
| `shared/models.py` | ✅ Complete | TimestampMixin base model |
| `shared/schemas.py` | ✅ Complete | Pagination, error response schemas |
| `shared/utils.py` | ✅ Complete | UTC datetime utilities |
| `shared/vault/` | ✅ Complete | VaultManager package |
| `shared/vault/manager.py` | ✅ Complete | VaultManager with 7 query + 6 CRUD + 5 structure + 1 preferences operation |
| `shared/vault/exceptions.py` | ✅ Complete | VaultError hierarchy (8 exceptions) |
| `shared/openai_adapter.py` | Not started | OpenAI format helpers |

### Features

| Feature | Tool | Status | Notes |
|---------|------|--------|-------|
| `features/chat/` | `/api/v1/chat/test` | ✅ Complete | Test endpoint for agent |
| `features/chat/schemas.py` | - | ✅ Complete | ChatRequest, ChatResponse |
| `features/chat/routes.py` | - | ✅ Complete | POST /api/v1/chat/test |
| Chat (OpenAI) | `/v1/chat/completions` | ✅ Complete | Streaming + non-streaming, Obsidian Copilot verified |
| `features/chat/openai_schemas.py` | - | ✅ Complete | OpenAI request/response models |
| `features/chat/streaming.py` | - | ✅ Complete | SSE generator using agent.iter() |
| `features/chat/openai_routes.py` | - | ✅ Complete | OpenAI-compatible endpoint + preferences injection |
| `features/chat/preferences.py` | - | ✅ Complete | User preferences schemas and formatting |
| Notes | `obsidian_manage_notes` | ✅ Complete | 6 operations, bulk support, 33 tests |
| Search | `obsidian_query_vault` | ✅ Complete | 7 operations, 51 tests |
| Structure | `obsidian_manage_structure` | ✅ Complete | 5 operations, bulk support, 52 tests |

### Docker

| Component | Status | Notes |
|-----------|--------|-------|
| `Dockerfile` | ✅ Complete | Container definition |
| `docker-compose.yml` | ✅ Complete | PostgreSQL on port 5433, vault mount, OBSIDIAN_VAULT_PATH override |
| Volume mounting | ✅ Complete | `/vault` mount point configured |

### Testing

| Category | Status | Notes |
|----------|--------|-------|
| Unit tests | ✅ 286 passing | Core, shared, agents, chat, vault, tools, preferences |
| Integration tests | ✅ 10 passing | Multi-tool workflow tests |
| Database tests | ✅ 6 passing | Require running PostgreSQL |
| E2E test | ✅ Verified | curl to /v1/chat/completions (streaming + non-streaming) |
| Obsidian Copilot | ✅ Verified | Chat with Jasque via Obsidian works |
| Manual tests | ✅ Verified | All 3 tools tested (query, notes, structure) |

---

## Service Status

| Service | Status | Port | Notes |
|---------|--------|------|-------|
| Jasque API | Available | 8123 | `uv run uvicorn app.main:app --reload --port 8123` |
| PostgreSQL | Available | 5433 | `docker-compose up -d db` |
| Health endpoint | Working | - | `/health`, `/health/db`, `/health/ready` |
| Chat test endpoint | Working | - | POST `/api/v1/chat/test` |
| OpenAI endpoint | Working | - | POST `/v1/chat/completions` (streaming + non-streaming) |

---

## Configuration

### Environment Variables

```bash
# Configured in .env and .env.example
APP_NAME=Jasque
OBSIDIAN_VAULT_PATH=/path/to/vault  # Host path, mounted to /vault in container
LLM_MODEL=anthropic:claude-sonnet-4-5  # Format: provider:model-name
# Supported providers: anthropic, google-gla, google-vertex, openai
ANTHROPIC_API_KEY=sk-ant-...  # Set key for your chosen provider
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/obsidian_db
```

### Dependencies Added

- `pydantic-ai` - Agent framework
- `anthropic` - LLM provider
- `aiofiles` - Async file I/O for vault operations
- `python-frontmatter` - YAML frontmatter parsing

---

## Key Documents

| Document | Purpose | Status |
|----------|---------|--------|
| `.agents/reference/PRD.md` | Product requirements | Complete (v1.2) |
| `.agents/reference/mvp-tool-designs.md` | Tool specifications | Complete (v1.1) |
| `.agents/reference/obsidian-copilot-setup.md` | Obsidian Copilot config | Complete |
| `.agents/plans/implement-base-agent.md` | Base agent plan | ✅ Executed |
| `.agents/plans/implement-openai-compatible-api.md` | OpenAI API plan | ✅ Executed |
| `.agents/plans/implement-obsidian-query-vault-tool.md` | First tool plan | ✅ Executed |
| `.agents/plans/implement-obsidian-manage-notes-tool.md` | Second tool plan | ✅ Executed |
| `.agents/plans/implement-obsidian-manage-structure-tool.md` | Third tool plan | ✅ Executed |
| `.agents/report/research-report-obsidian-copilot-api-integration.md` | Obsidian Copilot research | Complete |
| `.agents/report/research-report-pydantic-ai-streaming-sse.md` | Streaming research | Complete |
| `.agents/report/research-report-conversation-memory.md` | Memory patterns research | Complete |
| `.agents/reference/memory-implementation-guide.md` | Phased memory implementation | Phase 1 complete, Phase 2-4 ready |
| `.agents/plans/implement-vault-preferences-phase1.md` | Phase 1 implementation plan | ✅ Executed |
| `CLAUDE.md` | Project guidelines | Complete |
| `README.md` | Project overview | Updated for Jasque |
| `docs/about-jasque.md` | Conceptual overview | Complete |
| `docs/architecture-layers.md` | Technical deep-dive | Complete |
| `docs/jasque-preferences-guide.md` | User guide for preferences | Complete |
| `_session_logs/` | Session history | Active |

---

## Recent Changes

- 2026-01-16 (Session 1): Preferences Guide and Customization
  - Deep exploration of `_jasque/preferences` feature capabilities
  - Created comprehensive user guide: `docs/jasque-preferences-guide.md`
  - Built personalized preferences file through guided interview
  - Key insight: tagging section as collaborative refinement (not fixed system)
  - Session log: `_session_logs/2026-01-16-1-preferences-guide-and-customization.md`

- 2026-01-15 (Session 3): Implement Vault-Based Preferences (Memory Phase 1)
  - Executed 7-task implementation plan from `.agents/plans/implement-vault-preferences-phase1.md`
  - Created `app/features/chat/preferences.py` with schemas and formatting utilities
  - Added `PreferencesParseError` exception and `load_preferences()` method to VaultManager
  - Integrated preferences loading into chat completions endpoint
  - Added 13 new tests for preferences system
  - Test count: 273 → 286 (+13 tests)
  - All validation green: pytest, mypy, pyright, ruff
  - Session log: `_session_logs/2026-01-15-3-implement-vault-preferences.md`

- 2026-01-15 (Session 2): Memory Feature Research and Planning
  - Reviewed PRD Phase 2 enhancements, clarified memory was in MVP scope but deferred
  - Researched Pydantic AI memory patterns, industry approaches (MemGPT, LangGraph)
  - Identified 12 senior-level architectural questions for memory implementation
  - Created comprehensive 4-phase implementation plan (vault prefs → conversation log → audit → extracted facts)
  - Made Phase 1 design decisions: `_jasque/preferences.md`, YAML+markdown format
  - Created `.agents/report/research-report-conversation-memory.md`
  - Created `.agents/reference/memory-implementation-guide.md`
  - Session log: `_session_logs/2026-01-15-2-memory-feature-research.md`

- 2026-01-15 (Session 1): Validation and Integration Tests
  - Fixed 2 failing API key tests (mocking issue with pydantic-settings)
  - Added 10 integration workflow tests covering multi-tool scenarios
  - Test count: 263 → 273 (+10 tests)
  - All validation green: pytest, mypy, pyright, ruff
  - Commit: `c26e6fc`
  - Session log: `_session_logs/2026-01-15-1-validation-and-integration-tests.md`

- 2026-01-14 (Session 1): Documentation Deep-Dive
  - Conducted tutored walkthrough of all infrastructure layers
  - Clarified Jasque value proposition (retrieval vs. agency)
  - Explained Docker's role in packaging and sandboxing
  - Created `docs/about-jasque.md` - conceptual overview and value proposition
  - Created `docs/architecture-layers.md` - technical deep-dive with Docker section
  - Added `/create-prompt` command from upstream course materials
  - Session log: `_session_logs/2026-01-14-1-documentation-deep-dive.md`

- 2026-01-13 (Session 3): Module 7 System Review Exercise
  - Completed tutored walkthrough of system review concepts
  - Created `/validation/execution-report` and `/validation/system-review` commands
  - Ran system review on obsidian_manage_structure implementation (9/10 alignment)
  - Updated CLAUDE.md with Docker environment override pattern
  - Reorganized commands into subdirectories: session/, piv_loop/, validation/
  - Removed plan-template.md (superseded by plan-feature.md)
  - Commit: `e7fab36`
  - Session log: `_session_logs/2026-01-13-3-system-review-exercise.md`

- 2026-01-13 (Session 2): Gemini 2.5 Pro LLM Testing
  - Pushed 6 commits to origin/main (ca652ee..e7ede85)
  - Updated `.env` with LLM_MODEL variable and multi-provider API key structure
  - Configured and tested Gemini 2.5 Pro as LLM provider
  - Resolved Google Cloud setup: enabled Generative Language API, enabled billing
  - Successfully tested Jasque with Gemini via Obsidian Copilot
  - Session log: `_session_logs/2026-01-13-2-gemini-llm-testing.md`

- 2026-01-13 (Session 1): Code Review Command and LLM Provider Refactor
  - Ran `/code-review --last-commit` on multi-LLM provider commit
  - Refactored: Moved env var setup to dedicated `configure_llm_provider()` function
  - Committed `/code-review` slash command (3 modes: uncommitted, last-commit, unpushed)
  - Compared command against agentic-coding-course module 7 reference
  - Added `.agents/code-reviews` to `.gitignore`
  - All validation green: 263 tests passing
  - Session log: `_session_logs/2026-01-13-1-code-review-and-refactor.md`

- 2026-01-12 (Session 1): obsidian_manage_structure Tool Implementation - MVP Complete
  - Implemented third and final MVP tool with 5 operations
  - Added FolderAlreadyExistsError, FolderNotEmptyError, FolderNode dataclass
  - Implemented 5 VaultManager methods (create_folder, rename, delete_folder, move, list_structure)
  - Created obsidian_manage_structure tool with bulk support for move/rename
  - Added 52 new tests (27 VaultManager + 25 tool)
  - Fixed Docker config: OBSIDIAN_VAULT_PATH override for container environment
  - Manual tested all 5 operations with Obsidian Copilot
  - All validation green: 251 tests passing
  - Session log: `_session_logs/2026-01-12-1-implement-obsidian-manage-structure.md`

- 2026-01-09 (Session 5): obsidian_manage_notes Tool Implementation
  - Executed all 18 tasks from implementation plan
  - Added 2 new exceptions (NoteAlreadyExistsError, TaskNotFoundError)
  - Implemented 6 VaultManager methods (create, update, append, delete, complete_task, _atomic_write)
  - Created obsidian_manage_notes tool with bulk support
  - Added 33 new tests (18 VaultManager + 15 tool)
  - Manual tested all 6 operations with Obsidian Copilot
  - Added "File Sync" guidance to SYSTEM_PROMPT for UI refresh issues
  - All validation green: 201 tests passing
  - Session log: `_session_logs/2026-01-09-5-obsidian-manage-notes-implementation.md`

- 2026-01-09 (Session 4): obsidian_manage_notes Tool Planning
  - Deep planning session using `/plan-feature` command
  - Researched Pydantic AI FunctionToolset and tool patterns
  - Researched atomic writes (aiofiles), frontmatter preservation
  - Designed bulk operations schema (single BulkNoteItem model)
  - Designed task completion with cascading match (line number → exact → substring)
  - Created 18-task implementation plan (condensed from 2,014 to 1,071 lines)
  - Plan ready to execute: `.agents/plans/implement-obsidian-manage-notes-tool.md`
  - Session log: `_session_logs/2026-01-09-4-obsidian-manage-notes-planning.md`

- 2026-01-09 (Session 3): Fix Streaming First Token Issue
  - Diagnosed missing first token in streaming responses ("!" instead of "Hello!")
  - Root cause: `PartStartEvent` contains initial text, not just `PartDeltaEvent`
  - Added `PartStartEvent` handling in `streaming.py`
  - Updated research report with correct streaming pattern
  - Added test case for `PartStartEvent` handling
  - Verified fix with Obsidian Copilot - first token now streams correctly
  - Session log: `_session_logs/2026-01-09-3-fix-streaming-first-token.md`

- 2026-01-09 (Session 2): obsidian_query_vault Tool Implementation
  - Executed all 19 tasks from implementation plan
  - Created VaultManager with 7 query operations (list_notes, list_folders, read_note, search_text, find_by_tag, get_backlinks, get_tags, list_tasks)
  - Implemented obsidian_query_vault tool with Pydantic AI FunctionToolset
  - Created tool_registry.py for centralized tool registration
  - Added 51 new tests (36 VaultManager + 15 tool tests)
  - Fixed circular import with lazy imports in `__init__.py`
  - All validation green: ruff, mypy, pyright, pytest (167 tests)
  - Session log: `_session_logs/2026-01-09-2-obsidian-query-vault-implementation.md`

- 2026-01-09 (Session 1): obsidian_query_vault Tool Planning
  - Deep session with full codebase and reference document analysis
  - Researched Pydantic AI FunctionToolset patterns (RunContext, tool registration)
  - Evaluated naming conventions (verbose for features, generic for shared/core)
  - Created comprehensive 19-task implementation plan
  - Decisions: python-frontmatter for YAML, aiofiles for async I/O, tmp_path for tests
  - Session log: `_session_logs/2026-01-09-1-obsidian-query-vault-planning.md`

- 2026-01-08 (Session 2): PIV Loop Commands Migration
  - Copied core PIV loop commands from agentic-coding-course
  - Replaced `/execute` with comprehensive 5-step version
  - Merged `/plan-feature` (user checkpoints + source detailed template)
  - Kept `/prime` and `/prime-tools` unchanged (already optimal)
  - Session log: `_session_logs/2026-01-08-2-piv-loop-commands.md`

- 2026-01-08 (Session 1): Plan Feature Command (Course Exercise)
  - Verified .zshrc compatibility after system troubleshooting
  - Created global `~/.claude/CLAUDE.md` with GitHub CLI preference
  - Completed Module 5.7 exercise: Template planning workflow
  - Created `/plan-feature` command combining research + planning (7 phases, 3 checkpoints)
  - Fixed import sorting in `app/main.py`
  - Session log: `_session_logs/2026-01-08-1-plan-feature-command.md`

- 2026-01-07 (Session 4): Command Optimization
  - Analyzed redundancy between `/prime` and `/start-session`
  - Added `deep` mode to `/start-session` for full codebase analysis
  - Analyzed redundancy between `/commit` and `/end-session`
  - Added `commit` mode to `/end-session` for thorough conventional commits
  - Established composition pattern: default (light) + flag (thorough)
  - Session log: `_session_logs/2026-01-07-4-command-optimization.md`

- 2026-01-07 (Session 3): OpenAI-Compatible API Implementation
  - Implemented `/v1/chat/completions` endpoint with streaming and non-streaming support
  - Created `openai_schemas.py` with Pydantic models matching OpenAI format
  - Created `streaming.py` with SSE generator using `agent.iter()` and `node.stream()`
  - Created `openai_routes.py` with endpoint handling both response types
  - Configured CORS for Obsidian Copilot (`app://obsidian.md`)
  - Added 30 new unit tests (107 total passing)
  - Created user documentation: `.agents/reference/obsidian-copilot-setup.md`
  - E2E verified with curl and Obsidian Copilot plugin
  - Session log: `_session_logs/2026-01-07-3-openai-api-implementation.md`

---

## Blockers

None currently.

---

## Next Actions

1. **Memory Phase 2** - Conversation logging with PostgreSQL (optional)
2. **Memory Phase 3** - Audit trail for tool calls (optional)
3. **Memory Phase 4** - Extracted facts with LLM (optional)
4. **Documentation** - User guide, API docs
5. **Consider `/v1/embeddings`** - For Obsidian Copilot QA mode support (lower priority)
