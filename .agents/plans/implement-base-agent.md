# Feature: Base Pydantic AI Agent with Test API

## Feature Description

Create a base Pydantic AI agent using Claude Opus 4, with a simple system prompt and a FastAPI test endpoint. Establishes the foundation for all future agent-based features in Jasque.

## User Story

As a developer building Jasque, I want a working Pydantic AI agent with a test API endpoint so that I can verify the agent infrastructure works before building vault tools.

## Feature Metadata

**Feature Type**: New Capability
**Complexity**: Medium
**Systems Affected**: `app/core/`, `app/features/chat/`
**Dependencies**: `pydantic-ai`, `anthropic` (already installed)

---

## CONTEXT REFERENCES

### Files to Read Before Implementing

| File | Why |
|------|-----|
| `app/core/config.py:15-48` | Settings pattern, `anthropic_api_key` |
| `app/core/logging.py:75-148` | `get_logger()` and logging patterns |
| `app/core/health.py` | FastAPI router pattern |
| `app/main.py:63-78` | Router inclusion pattern |
| `app/tests/conftest.py` | Fixture patterns |
| `app/core/tests/test_config.py` | Test patterns with env mocking |
| `docs/logging-standard.md` | Agent event taxonomy |
| `docs/pytest-standard.md` | Test patterns |
| `.agents/reference/vsa-patterns.md` | VSA architecture |

### New Files to Create

- `app/core/agents/__init__.py` - Package init
- `app/core/agents/types.py` - Type definitions
- `app/core/agents/base.py` - Agent factory
- `app/core/agents/tests/__init__.py` - Test package
- `app/core/agents/tests/test_base.py` - Unit tests
- `app/features/chat/schemas.py` - Request/response schemas
- `app/features/chat/routes.py` - Test endpoint
- `app/features/chat/tests/__init__.py` - Test package
- `app/features/chat/tests/test_routes.py` - Route tests
- `conftest.py` (root level) - Project-wide fixtures

### Key Patterns

**Logging**: Use `agent.lifecycle.*`, `agent.llm.*` events per `docs/logging-standard.md`

**Settings**: Follow `@lru_cache` singleton pattern from `get_settings()`

**Error Handling**:
```python
try:
    result = await agent.run(prompt, deps=deps)
    logger.info("agent.llm.call_completed", ...)
except Exception as e:
    logger.error("agent.llm.call_failed", error=str(e), exc_info=True)
    raise
```

---

## STEP-BY-STEP TASKS

### Task 1: UPDATE `app/core/config.py`

Add `anthropic_model` setting after `anthropic_api_key`:

```python
anthropic_model: str = "claude-opus-4"
```

**VALIDATE**: `uv run mypy app/core/config.py && uv run pyright app/core/config.py`

---

### Task 2: UPDATE `.env.example`

Add after `ANTHROPIC_API_KEY`:

```bash
# Anthropic model to use (claude-opus-4 is the latest and most capable)
ANTHROPIC_MODEL=claude-opus-4
```

---

### Task 3: CREATE `app/core/agents/__init__.py`

```python
"""Pydantic AI agent infrastructure for Jasque."""

from app.core.agents.base import create_agent, get_agent
from app.core.agents.types import AgentDependencies

__all__ = ["create_agent", "get_agent", "AgentDependencies"]
```

---

### Task 4: CREATE `app/core/agents/types.py`

```python
"""Type definitions for Pydantic AI agents."""

from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools via RunContext."""
    request_id: str = ""


class TokenUsage(BaseModel):
    """Token usage information from LLM call."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

**VALIDATE**: `uv run mypy app/core/agents/types.py && uv run pyright app/core/agents/types.py`

---

### Task 5: CREATE `app/core/agents/base.py`

```python
"""Base Pydantic AI agent for Jasque."""

from functools import lru_cache
from pydantic_ai import Agent
from app.core.agents.types import AgentDependencies
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Jasque, an AI assistant for Obsidian vault management.

You help users interact with their Obsidian vault through natural language.
You can search notes, create and modify content, manage tasks, and organize folders.

Be concise and helpful. When you don't have access to a tool needed for a task,
explain what you would need to accomplish it.

Current capabilities:
- Conversational responses
- (Tools will be added in future updates)
"""


def create_agent() -> Agent[AgentDependencies, str]:
    """Create a new Pydantic AI agent instance."""
    settings = get_settings()
    model_name = f"anthropic:{settings.anthropic_model}"

    logger.info("agent.lifecycle.creating", model=settings.anthropic_model)

    agent: Agent[AgentDependencies, str] = Agent(
        model_name,
        deps_type=AgentDependencies,
        output_type=str,
        instructions=SYSTEM_PROMPT,
    )

    logger.info("agent.lifecycle.created", model=settings.anthropic_model)
    return agent


@lru_cache(maxsize=1)
def get_agent() -> Agent[AgentDependencies, str]:
    """Get the cached singleton agent instance."""
    return create_agent()
```

**VALIDATE**: `uv run mypy app/core/agents/base.py && uv run pyright app/core/agents/base.py`

---

### Task 6: CREATE `app/core/agents/tests/__init__.py`

```python
"""Tests for agent infrastructure."""
```

---

### Task 7: CREATE `app/features/chat/schemas.py`

```python
"""Schemas for chat feature endpoints."""

from pydantic import BaseModel, Field
from app.core.agents.types import TokenUsage


class ChatRequest(BaseModel):
    """Request schema for the test chat endpoint."""
    message: str = Field(..., min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    """Response schema for the test chat endpoint."""
    response: str
    model: str
    usage: TokenUsage | None = None
```

**VALIDATE**: `uv run mypy app/features/chat/schemas.py && uv run pyright app/features/chat/schemas.py`

---

### Task 8: CREATE `app/features/chat/routes.py`

```python
"""Chat feature routes for testing the Pydantic AI agent."""

from fastapi import APIRouter, HTTPException, status
from app.core.agents import AgentDependencies, get_agent
from app.core.agents.types import TokenUsage
from app.core.logging import get_logger, get_request_id
from app.features.chat.schemas import ChatRequest, ChatResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/test", response_model=ChatResponse)
async def test_chat(request: ChatRequest) -> ChatResponse:
    """Test endpoint for the Pydantic AI agent."""
    agent = get_agent()
    request_id = get_request_id()
    deps = AgentDependencies(request_id=request_id)

    logger.info("agent.llm.call_started", prompt_length=len(request.message), request_id=request_id)

    try:
        result = await agent.run(request.message, deps=deps)

        usage = None
        if result.usage():
            usage_data = result.usage()
            usage = TokenUsage(
                prompt_tokens=usage_data.request_tokens or 0,
                completion_tokens=usage_data.response_tokens or 0,
                total_tokens=usage_data.total_tokens or 0,
            )

        logger.info(
            "agent.llm.call_completed",
            response_length=len(result.output),
            tokens_prompt=usage.prompt_tokens if usage else None,
            tokens_completion=usage.completion_tokens if usage else None,
            request_id=request_id,
        )

        return ChatResponse(
            response=result.output,
            model=result.model_name or "unknown",
            usage=usage,
        )

    except Exception as e:
        logger.error("agent.llm.call_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e!s}",
        ) from e
```

**VALIDATE**: `uv run mypy app/features/chat/routes.py && uv run pyright app/features/chat/routes.py`

---

### Task 9: UPDATE `app/features/chat/__init__.py`

```python
"""Chat feature - OpenAI-compatible API endpoint."""

from app.features.chat.routes import router

__all__ = ["router"]
```

---

### Task 10: UPDATE `app/main.py`

Add import at top:
```python
from app.features.chat import router as chat_router
```

Add router inclusion after `app.include_router(health_router)`:
```python
app.include_router(chat_router, prefix="/api/v1")
```

Add agent init in lifespan after database log:
```python
from app.core.agents import get_agent
get_agent()
logger.info("agent.lifecycle.initialized")
```

**VALIDATE**: `uv run mypy app/main.py && uv run pyright app/main.py`

---

### Task 11: CREATE `conftest.py` (root level)

```python
"""Project-wide pytest fixtures."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """Provide standard mock environment variables for testing."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ANTHROPIC_API_KEY": "sk-ant-test-key-for-testing",
        "ANTHROPIC_MODEL": "claude-opus-4",
        "APP_NAME": "Jasque",
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def test_client(mock_env_vars: dict[str, str]) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with mocked environment."""
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


@pytest.fixture
def mock_anthropic_response() -> dict[str, Any]:
    """Provide a mock Anthropic API response for testing."""
    return {
        "content": [{"type": "text", "text": "Hello! I'm Jasque."}],
        "model": "claude-opus-4",
        "usage": {"input_tokens": 10, "output_tokens": 15},
    }
```

**VALIDATE**: `uv run pytest --collect-only`

---

### Task 12: CREATE `app/core/agents/tests/test_base.py`

```python
"""Tests for base agent module."""

import os
from unittest.mock import MagicMock, patch
import pytest
from app.core.agents.base import SYSTEM_PROMPT, create_agent, get_agent
from app.core.agents.types import AgentDependencies


@pytest.fixture(autouse=True)
def mock_environment():
    """Set up test environment."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "ANTHROPIC_MODEL": "claude-opus-4",
    }
    with patch.dict(os.environ, env_vars):
        from app.core.config import get_settings
        get_settings.cache_clear()
        get_agent.cache_clear()
        yield
        get_settings.cache_clear()
        get_agent.cache_clear()


def test_system_prompt_contains_jasque():
    """Test that system prompt mentions Jasque."""
    assert "Jasque" in SYSTEM_PROMPT
    assert "Obsidian" in SYSTEM_PROMPT


def test_create_agent_returns_agent():
    """Test that create_agent returns a Pydantic AI Agent."""
    with patch("app.core.agents.base.Agent") as mock_agent_class:
        mock_agent_class.return_value = MagicMock()
        result = create_agent()
        assert result is mock_agent_class.return_value
        mock_agent_class.assert_called_once()


def test_create_agent_uses_correct_model():
    """Test that create_agent uses the configured model."""
    with patch("app.core.agents.base.Agent") as mock_agent_class:
        create_agent()
        assert mock_agent_class.call_args[0][0] == "anthropic:claude-opus-4"


def test_create_agent_sets_deps_type():
    """Test that create_agent configures dependencies type."""
    with patch("app.core.agents.base.Agent") as mock_agent_class:
        create_agent()
        assert mock_agent_class.call_args[1]["deps_type"] == AgentDependencies


def test_get_agent_returns_cached_instance():
    """Test that get_agent returns the same instance on repeated calls."""
    with patch("app.core.agents.base.Agent") as mock_agent_class:
        mock_agent_class.return_value = MagicMock()
        agent1 = get_agent()
        agent2 = get_agent()
        assert agent1 is agent2
        mock_agent_class.assert_called_once()


def test_agent_dependencies_dataclass():
    """Test AgentDependencies dataclass creation."""
    deps = AgentDependencies()
    assert deps.request_id == ""
    deps_with_id = AgentDependencies(request_id="test-123")
    assert deps_with_id.request_id == "test-123"
```

**VALIDATE**: `uv run pytest app/core/agents/tests/test_base.py -v`

---

### Task 13: CREATE `app/features/chat/tests/__init__.py`

```python
"""Tests for chat feature."""
```

---

### Task 14: CREATE `app/features/chat/tests/test_routes.py`

```python
"""Tests for chat routes."""

import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_environment():
    """Set up test environment."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "ANTHROPIC_MODEL": "claude-opus-4",
    }
    with patch.dict(os.environ, env_vars):
        from app.core.config import get_settings
        from app.core.agents.base import get_agent
        get_settings.cache_clear()
        get_agent.cache_clear()
        yield
        get_settings.cache_clear()
        get_agent.cache_clear()


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_agent_run():
    """Mock the agent.run() method."""
    mock_result = MagicMock()
    mock_result.output = "Hello! I'm Jasque, your AI assistant."
    mock_result.model_name = "claude-opus-4"
    mock_usage = MagicMock()
    mock_usage.request_tokens = 10
    mock_usage.response_tokens = 15
    mock_usage.total_tokens = 25
    mock_result.usage.return_value = mock_usage
    return mock_result


def test_chat_test_endpoint_success(client, mock_agent_run):
    """Test successful chat request."""
    with patch("app.features.chat.routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent
        response = client.post("/api/v1/chat/test", json={"message": "Hello!"})
        assert response.status_code == 200
        assert response.json()["response"] == "Hello! I'm Jasque, your AI assistant."


def test_chat_test_endpoint_empty_message(client):
    """Test that empty message is rejected."""
    response = client.post("/api/v1/chat/test", json={"message": ""})
    assert response.status_code == 422


def test_chat_test_endpoint_missing_message(client):
    """Test that missing message field is rejected."""
    response = client.post("/api/v1/chat/test", json={})
    assert response.status_code == 422


def test_chat_test_endpoint_agent_error(client):
    """Test error handling when agent fails."""
    with patch("app.features.chat.routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = Exception("API Error")
        mock_get_agent.return_value = mock_agent
        response = client.post("/api/v1/chat/test", json={"message": "Hello!"})
        assert response.status_code == 500
        assert "Agent execution failed" in response.json()["detail"]


def test_chat_test_endpoint_returns_usage(client, mock_agent_run):
    """Test that usage information is returned."""
    with patch("app.features.chat.routes.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = mock_agent_run
        mock_get_agent.return_value = mock_agent
        response = client.post("/api/v1/chat/test", json={"message": "Hello!"})
        assert response.status_code == 200
        assert response.json()["usage"]["prompt_tokens"] == 10
```

**VALIDATE**: `uv run pytest app/features/chat/tests/test_routes.py -v`

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
uv run ruff format .
uv run ruff check .
```

### Level 2: Type Checking

```bash
uv run mypy app/
uv run pyright app/
```

### Level 3: Tests

```bash
uv run pytest -v
uv run pytest app/core/agents/tests/ -v
uv run pytest app/features/chat/tests/ -v
```

### Level 4: Manual Validation

```bash
uv run uvicorn app.main:app --reload --port 8123

curl -X POST http://localhost:8123/api/v1/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, who are you?"}'
```

---

## ACCEPTANCE CRITERIA

- [ ] Agent uses `claude-opus-4` as default model
- [ ] `ANTHROPIC_MODEL` configurable via environment variable
- [ ] Test endpoint at `POST /api/v1/chat/test` works
- [ ] Structured logging follows `agent.` domain pattern
- [ ] All type checking passes (MyPy + Pyright)
- [ ] All tests pass (no regressions in 66 existing tests)
- [ ] Root-level conftest.py provides shared fixtures

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] All validation commands pass
- [ ] Manual testing confirms feature works
- [ ] Code follows project patterns

---

## NOTES

### Design Decisions

1. **Agent in `core/agents/` folder**: Allows expansion for types, base, future registry
2. **Singleton via `@lru_cache`**: Follows existing `get_settings()` pattern
3. **Simple test endpoint**: Validates agent before full OpenAI-compatible API
4. **Mock-based tests**: No real API calls, fast and reliable

### Future Considerations

- Add `tools` parameter for vault tools
- Add streaming support
- Add conversation history
- Implement `/v1/chat/completions` endpoint

<!-- EOF -->
