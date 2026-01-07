# Feature: OpenAI-Compatible API for Obsidian Copilot Integration

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement an OpenAI-compatible `/v1/chat/completions` endpoint that enables the Obsidian Copilot plugin to communicate with Jasque. This includes:

- Full streaming support using `agent.iter()` and SSE
- Non-streaming synchronous responses
- OpenAI message format conversion to Pydantic AI format
- CORS configuration for Obsidian (Electron app on `app://obsidian.md`)
- User documentation for plugin configuration

**Critical Design Decision:** The agent's system prompt lives in `app/core/agents/base.py` as `SYSTEM_PROMPT`. The OpenAI-compatible endpoint must NOT define its own system prompt—it uses the agent singleton which already has instructions configured.

## User Story

As an Obsidian user with the Copilot plugin installed,
I want to connect to Jasque as my AI backend,
So that I can interact with my vault through natural language in the Copilot interface.

## Problem Statement

Obsidian Copilot expects an OpenAI-compatible API at `/v1/chat/completions`. Currently, Jasque only has a test endpoint at `/api/v1/chat/test` with a non-standard format. Users cannot connect Obsidian Copilot to Jasque.

## Solution Statement

Implement the `/v1/chat/completions` endpoint following the OpenAI API specification:
1. Accept both streaming (`stream: true`) and non-streaming requests
2. Convert OpenAI message format to Pydantic AI message history
3. Use `agent.iter()` for streaming with `PartDeltaEvent` text extraction
4. Return properly formatted SSE chunks for streaming responses
5. Configure CORS to allow requests from Obsidian (`app://obsidian.md`)
6. Provide user documentation for Obsidian Copilot configuration

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `app/features/chat/`, `app/core/middleware.py`, `app/core/config.py`
**Dependencies**: Pydantic AI `agent.iter()`, FastAPI `StreamingResponse`

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `app/core/agents/base.py` (lines 14-25, 28-51) - Why: Contains `SYSTEM_PROMPT` and `create_agent()` - DO NOT duplicate system prompt
- `app/core/agents/types.py` (all) - Why: `AgentDependencies` and `TokenUsage` models to reuse
- `app/features/chat/routes.py` (all) - Why: Existing route pattern to follow, shows `get_agent()` usage
- `app/features/chat/schemas.py` (all) - Why: Existing schema pattern
- `app/core/middleware.py` (lines 91-114) - Why: CORS setup pattern in `setup_middleware()`
- `app/core/config.py` (line 49) - Why: `allowed_origins` setting for CORS
- `app/core/logging.py` - Why: Logging pattern with `get_logger(__name__)`
- `app/main.py` (lines 83-84) - Why: Router registration pattern

### New Files to Create

- `app/features/chat/openai_schemas.py` - OpenAI-compatible request/response Pydantic models
- `app/features/chat/openai_routes.py` - `/v1/chat/completions` endpoint implementation
- `app/features/chat/streaming.py` - SSE streaming generator and helpers
- `app/features/chat/tests/test_openai_routes.py` - Unit tests for OpenAI endpoint
- `app/features/chat/tests/test_streaming.py` - Unit tests for streaming logic
- `.agents/reference/obsidian-copilot-setup.md` - User documentation for plugin configuration

### Relevant Documentation YOU SHOULD READ BEFORE IMPLEMENTING!

- `.agents/report/research-report-obsidian-copilot-api-integration.md`
  - Sections: Part 1 (Message Content Format), Part 2 (Endpoint Path Construction), Implementation Requirements
  - Why: Exact OpenAI format expected by Obsidian Copilot, content normalization logic

- `.agents/report/research-report-pydantic-ai-streaming-sse.md`
  - Sections: Part 1 (`agent.iter()` usage), Part 2 (OpenAI Chunk Format), Part 3 (FastAPI SSE)
  - Why: How to stream from Pydantic AI agent, SSE chunk formatting, message history conversion

- `.agents/reference/vsa-patterns.md`
  - Sections: Rule 3 (Feature Slices), Testing in Vertical Slices
  - Why: Feature structure patterns, where files go

- `docs/logging-standard.md`
  - Sections: Agent Domain, Request Domain
  - Why: Event naming patterns like `agent.llm.call_started`, `agent.llm.streaming_started`

- `docs/pytest-standard.md`
  - Sections: Async Testing, FastAPI Testing
  - Why: Test patterns with `pytest.mark.asyncio` and `TestClient`

- `docs/mypy-standard.md`
  - Sections: Async Functions, Type Aliases
  - Why: Proper type annotations for async generators

### Patterns to Follow

**Naming Conventions:**
```python
# Logging events (from docs/logging-standard.md)
logger.info("agent.llm.streaming_started", ...)
logger.info("agent.llm.chunk_received", ...)
logger.info("agent.llm.streaming_completed", ...)
logger.error("agent.llm.call_failed", ..., exc_info=True)
```

**Error Handling:**
```python
# From app/features/chat/routes.py:71-81
try:
    # Agent call
except Exception as e:
    logger.error("agent.llm.call_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Agent execution failed: {e!s}") from e
```

**Logging Pattern:**
```python
# From app/features/chat/routes.py:10
from app.core.logging import get_logger, get_request_id
logger = get_logger(__name__)
```

**Agent Usage Pattern:**
```python
# From app/features/chat/routes.py:30-32
agent = get_agent()
request_id = get_request_id()
deps = AgentDependencies(request_id=request_id)
```

**Router Registration:**
```python
# From app/main.py:84
app.include_router(chat_router, prefix="/api/v1")
# NOTE: OpenAI endpoint needs different prefix! See Task 8.
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Schemas & Types)

Create OpenAI-compatible Pydantic models for request/response handling.

**Tasks:**
- Define message content types (string and structured array formats)
- Create `ChatCompletionRequest` with all OpenAI fields
- Create `ChatCompletionResponse` for non-streaming
- Create `ChatCompletionChunk` for streaming
- Add content normalization helper function

### Phase 2: Core Implementation (Streaming & Endpoint)

Implement the streaming generator and main endpoint.

**Tasks:**
- Create streaming generator using `agent.iter()` and `PartDeltaEvent`
- Implement message history conversion (OpenAI → Pydantic AI)
- Create non-streaming response handler
- Implement `/v1/chat/completions` endpoint with stream flag handling
- Add proper error handling for streams

### Phase 3: Integration (CORS & Router Registration)

Wire up the endpoint and configure CORS for Obsidian.

**Tasks:**
- Add `app://obsidian.md` to CORS allowed origins
- Register OpenAI router at `/v1` (not `/api/v1`)
- Update `.env.example` with new CORS setting

### Phase 4: Documentation & Testing

Create user documentation and comprehensive tests.

**Tasks:**
- Write Obsidian Copilot setup guide
- Create unit tests for schemas and content normalization
- Create unit tests for streaming generator (mocked agent)
- Create integration tests for endpoint

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: CREATE `app/features/chat/openai_schemas.py`

- **IMPLEMENT**: OpenAI-compatible Pydantic models following research report specifications
- **PATTERN**: Schema structure from `app/features/chat/schemas.py`
- **IMPORTS**: `from typing import Literal, Union, Annotated` and `from pydantic import BaseModel, Field`
- **GOTCHA**: Content can be `str` OR `list[ContentPart]` - use Union type
- **GOTCHA**: Use `Literal` for discriminated unions (`type: "text"` vs `type: "image_url"`)
- **VALIDATE**: `uv run mypy app/features/chat/openai_schemas.py && uv run pyright app/features/chat/openai_schemas.py`

**Models to create:**

```python
# Content parts (for multi-modal support)
class TextContentPart(BaseModel):
    type: Literal["text"]
    text: str

class ImageUrlContent(BaseModel):
    url: str
    detail: str | None = None

class ImageContentPart(BaseModel):
    type: Literal["image_url"]
    image_url: str | ImageUrlContent

ContentPart = Annotated[TextContentPart | ImageContentPart, Field(discriminator="type")]

# Message with flexible content
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[ContentPart]

# Request
class ChatCompletionRequest(BaseModel):
    model: str = "jasque"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    stream_options: dict[str, bool] | None = None

# Non-streaming response
class ChatCompletionMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length", "tool_calls"] = "stop"

class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage | None = None

# Streaming chunk
class DeltaContent(BaseModel):
    role: str | None = None
    content: str | None = None

class ChunkChoice(BaseModel):
    index: int = 0
    delta: DeltaContent
    finish_reason: str | None = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]
    usage: ChatCompletionUsage | None = None
```

### Task 2: CREATE `app/features/chat/streaming.py`

- **IMPLEMENT**: Content normalization function and message history conversion
- **PATTERN**: Helper function pattern from research report
- **IMPORTS**: `from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart, ModelMessage`
- **GOTCHA**: System messages from OpenAI should be ignored (agent has its own SYSTEM_PROMPT in base.py)
- **GOTCHA**: Import types correctly - `TextPart` is for responses, `UserPromptPart` is for requests
- **VALIDATE**: `uv run mypy app/features/chat/streaming.py && uv run pyright app/features/chat/streaming.py`

**Functions to create:**

```python
def normalize_content(content: str | list[dict[str, Any]]) -> str:
    """Extract plain text from OpenAI message content.

    Handles both string content and structured array format.
    Mirrors obsidian-copilot's extractTextFromChunk() logic.
    """

def extract_last_user_message(messages: list[ChatMessage]) -> str:
    """Get the last user message for the agent prompt."""

def convert_to_pydantic_history(messages: list[ChatMessage]) -> list[ModelMessage]:
    """Convert OpenAI messages to Pydantic AI message history.

    Note: System messages are ignored - the agent has its own instructions.
    """
```

### Task 3: ADD SSE streaming generator to `app/features/chat/streaming.py`

- **IMPLEMENT**: Async generator that yields SSE-formatted chunks from agent.iter()
- **PATTERN**: Research report Part 3 (FastAPI SSE), Part 1 (agent.iter() usage)
- **IMPORTS**: `from pydantic_ai import Agent`, `from pydantic_ai.messages import PartDeltaEvent, TextPartDelta`
- **GOTCHA**: First chunk must include `role: "assistant"` in delta
- **GOTCHA**: Last chunk must include `finish_reason: "stop"` and empty delta
- **GOTCHA**: Each chunk must be prefixed with `data: ` and end with `\n\n`
- **GOTCHA**: Stream must end with `data: [DONE]\n\n`
- **VALIDATE**: `uv run mypy app/features/chat/streaming.py && uv run pyright app/features/chat/streaming.py`

**Generator signature:**

```python
async def generate_sse_stream(
    agent: Agent[AgentDependencies, str],
    user_message: str,
    message_history: list[ModelMessage],
    deps: AgentDependencies,
    model_name: str,
    include_usage: bool = False,
) -> AsyncIterator[str]:
    """Generate OpenAI-compatible SSE chunks from Pydantic AI agent.

    Uses agent.iter() with node.stream() to extract TextPartDelta events.
    Yields SSE-formatted strings: 'data: {json}\n\n'
    """
```

### Task 4: CREATE `app/features/chat/openai_routes.py`

- **IMPLEMENT**: `/chat/completions` endpoint with stream/non-stream handling
- **PATTERN**: Route structure from `app/features/chat/routes.py`
- **IMPORTS**: `from fastapi import APIRouter, HTTPException, status`, `from fastapi.responses import StreamingResponse`
- **GOTCHA**: This router will be mounted at `/v1` so endpoint is just `/chat/completions`
- **GOTCHA**: Use existing `get_agent()` singleton - DO NOT create new agent
- **GOTCHA**: Agent already has system prompt configured - do NOT add another
- **VALIDATE**: `uv run mypy app/features/chat/openai_routes.py && uv run pyright app/features/chat/openai_routes.py`

**Route signature:**

```python
router = APIRouter(tags=["openai"])

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    """OpenAI-compatible chat completions endpoint.

    Supports both streaming (stream=true) and non-streaming requests.
    Compatible with Obsidian Copilot plugin.
    """
```

### Task 5: UPDATE `app/core/config.py` - Add Obsidian CORS origin

- **IMPLEMENT**: Add `app://obsidian.md` to default `allowed_origins` list
- **PATTERN**: Existing list format at line 49
- **IMPORTS**: None needed
- **GOTCHA**: Obsidian uses `app://obsidian.md` as its origin (Electron app)
- **VALIDATE**: `uv run pytest app/core/tests/test_config.py -v`

**Change:**

```python
# Line 49 - update default list
allowed_origins: list[str] = [
    "http://localhost:3000",
    "http://localhost:8123",
    "app://obsidian.md",  # Obsidian Copilot plugin
]
```

### Task 6: UPDATE `app/features/chat/__init__.py` - Export OpenAI router

- **IMPLEMENT**: Add import and export for `openai_router`
- **PATTERN**: Existing export pattern
- **IMPORTS**: `from app.features.chat.openai_routes import router as openai_router`
- **GOTCHA**: Keep existing `router` export, add new `openai_router`
- **VALIDATE**: `uv run python -c "from app.features.chat import openai_router; print('OK')"`

### Task 7: UPDATE `app/main.py` - Register OpenAI router at /v1

- **IMPLEMENT**: Add OpenAI router at `/v1` prefix (separate from `/api/v1`)
- **PATTERN**: Line 84 router registration
- **IMPORTS**: `from app.features.chat import openai_router`
- **GOTCHA**: OpenAI SDK expects `/v1/chat/completions` - mount at `/v1`, not `/api/v1`
- **VALIDATE**: `uv run pytest app/tests/test_main.py -v`

**Add after line 84:**

```python
app.include_router(openai_router, prefix="/v1")  # OpenAI-compatible endpoint
```

### Task 8: UPDATE `.env.example` - Document CORS setting

- **IMPLEMENT**: Add comment explaining Obsidian CORS requirement
- **PATTERN**: Existing comment style
- **IMPORTS**: None
- **GOTCHA**: Just documentation, no functional change
- **VALIDATE**: Manual review

### Task 9: CREATE `app/features/chat/tests/test_openai_schemas.py`

- **IMPLEMENT**: Unit tests for schema validation and content normalization
- **PATTERN**: Test structure from `app/features/chat/tests/test_routes.py`
- **IMPORTS**: `import pytest`, schema imports
- **GOTCHA**: Test both string and array content formats
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_openai_schemas.py -v`

**Test cases:**

```python
def test_chat_message_string_content() -> None:
    """Test ChatMessage with simple string content."""

def test_chat_message_array_content() -> None:
    """Test ChatMessage with structured array content."""

def test_normalize_content_string() -> None:
    """Test normalize_content with string input."""

def test_normalize_content_array() -> None:
    """Test normalize_content with array input."""

def test_normalize_content_mixed_array() -> None:
    """Test normalize_content with mixed text/image array (only extracts text)."""

def test_chat_completion_request_defaults() -> None:
    """Test ChatCompletionRequest default values."""
```

### Task 10: CREATE `app/features/chat/tests/test_streaming.py`

- **IMPLEMENT**: Unit tests for message conversion and streaming helpers
- **PATTERN**: Async test patterns from `docs/pytest-standard.md`
- **IMPORTS**: `import pytest`, `from unittest.mock import AsyncMock, MagicMock, patch`
- **GOTCHA**: Mock `agent.iter()` to test streaming without real LLM calls
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_streaming.py -v`

**Test cases:**

```python
def test_extract_last_user_message() -> None:
    """Test extracting last user message from conversation."""

def test_extract_last_user_message_empty() -> None:
    """Test extracting from empty messages returns empty string."""

def test_convert_to_pydantic_history_basic() -> None:
    """Test converting OpenAI messages to Pydantic AI format."""

def test_convert_to_pydantic_history_ignores_system() -> None:
    """Test that system messages are ignored (agent has own prompt)."""

async def test_generate_sse_stream_format() -> None:
    """Test SSE stream format: data: prefix, double newline, [DONE]."""
```

### Task 11: CREATE `app/features/chat/tests/test_openai_routes.py`

- **IMPLEMENT**: Integration tests for `/v1/chat/completions` endpoint
- **PATTERN**: FastAPI TestClient pattern from `docs/pytest-standard.md`
- **IMPORTS**: `from fastapi.testclient import TestClient`, `from unittest.mock import patch, AsyncMock`
- **GOTCHA**: Mock `get_agent()` to avoid real LLM calls in tests
- **GOTCHA**: Test both streaming and non-streaming paths
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_openai_routes.py -v`

**Test cases:**

```python
def test_chat_completions_non_streaming() -> None:
    """Test non-streaming chat completion response format."""

def test_chat_completions_streaming() -> None:
    """Test streaming response returns SSE format."""

def test_chat_completions_with_history() -> None:
    """Test that message history is passed to agent."""

def test_chat_completions_error_handling() -> None:
    """Test error response format on agent failure."""
```

### Task 12: CREATE `.agents/reference/obsidian-copilot-setup.md`

- **IMPLEMENT**: User documentation for configuring Obsidian Copilot with Jasque
- **PATTERN**: Markdown documentation style
- **IMPORTS**: None
- **GOTCHA**: Base URL should be `http://localhost:8123/v1` (SDK appends `/chat/completions`)
- **VALIDATE**: Manual review

**Content structure:**

```markdown
# Connecting Obsidian Copilot to Jasque

## Prerequisites
- Jasque running at localhost:8123
- Obsidian Copilot plugin installed

## Configuration Steps
1. Open Obsidian Settings
2. Navigate to Copilot settings
3. Configure:
   - Provider: "3rd party (openai format)"
   - Base URL: http://localhost:8123/v1
   - Model: jasque
   - API Key: (any non-empty value)

## Troubleshooting
- CORS errors: Ensure Jasque is running with proper CORS config
- Connection refused: Verify Jasque is running on port 8123
- 404 errors: Check base URL doesn't include /chat/completions

## Testing the Connection
Send a test message in Copilot to verify connectivity.
```

---

## TESTING STRATEGY

### Unit Tests

| File | Coverage Target |
|------|-----------------|
| `test_openai_schemas.py` | Schema validation, content normalization |
| `test_streaming.py` | Message conversion, SSE format |
| `test_openai_routes.py` | Endpoint logic, error handling |

Design unit tests with fixtures and assertions following existing testing approaches in `app/features/chat/tests/`.

### Integration Tests

- Test full request flow with mocked agent
- Verify CORS headers in response
- Test streaming vs non-streaming branches
- Test error propagation

### Edge Cases

| Case | Test File |
|------|-----------|
| Empty messages array | `test_openai_routes.py` |
| Messages with only system role | `test_streaming.py` |
| Content as empty array | `test_openai_schemas.py` |
| Invalid message role | `test_openai_schemas.py` |
| Agent timeout/error during stream | `test_streaming.py` |

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check app/features/chat/
uv run ruff format app/features/chat/ --check
```

### Level 2: Type Checking

```bash
uv run mypy app/features/chat/
uv run pyright app/features/chat/
```

### Level 3: Unit Tests

```bash
uv run pytest app/features/chat/tests/ -v
```

### Level 4: Full Test Suite

```bash
uv run pytest -v -m "not integration"
```

### Level 5: Manual Validation

```bash
# Start server
uv run uvicorn app.main:app --reload --port 8123

# Test non-streaming
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}]}'

# Test streaming
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'

# Test CORS preflight
curl -X OPTIONS http://localhost:8123/v1/chat/completions \
  -H "Origin: app://obsidian.md" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

---

## ACCEPTANCE CRITERIA

- [ ] `POST /v1/chat/completions` returns valid OpenAI-format response (non-streaming)
- [ ] `POST /v1/chat/completions` with `stream: true` returns SSE-formatted chunks
- [ ] SSE stream starts with role chunk, ends with finish_reason and `[DONE]`
- [ ] Message history is converted and passed to agent
- [ ] Agent's existing system prompt is used (not duplicated)
- [ ] CORS allows `app://obsidian.md` origin
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage for schemas, streaming, and routes
- [ ] User documentation in `.agents/reference/obsidian-copilot-setup.md`
- [ ] No regressions in existing `/api/v1/chat/test` endpoint

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms streaming and non-streaming work
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

1. **Separate router for OpenAI endpoint**: Mounted at `/v1` instead of `/api/v1` to match OpenAI SDK expectations. The SDK auto-appends `/chat/completions` to the base URL.

2. **Reuse agent singleton**: The `get_agent()` function returns a cached agent with system prompt already configured. The OpenAI endpoint must NOT create a new agent or add a system prompt.

3. **System messages ignored**: OpenAI format includes system messages in the messages array, but Jasque's agent already has instructions via `SYSTEM_PROMPT` in `base.py`. System messages from requests are silently ignored.

4. **Content normalization**: OpenAI messages can have `content` as string or array (for multi-modal). We extract only text parts, ignoring images for now (Jasque doesn't support images yet).

5. **Streaming with agent.iter()**: Uses Pydantic AI's `agent.iter()` with `node.stream()` to get `TextPartDelta` events. This is the recommended approach per Pydantic AI documentation.

### Future Considerations

- Image support (multi-modal) - requires tool/prompt changes
- Tool calling in OpenAI format - requires response format changes
- Multiple choices (n > 1) - currently only returns single choice
- Token streaming options - `stream_options.include_usage` support

### Research References

- `.agents/report/research-report-obsidian-copilot-api-integration.md` - OpenAI format details
- `.agents/report/research-report-pydantic-ai-streaming-sse.md` - Streaming implementation

<!-- EOF -->
