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
        "ANTHROPIC_MODEL": "claude-sonnet-4-5",
        "APP_NAME": "Jasque",
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def test_client(mock_env_vars: dict[str, str]) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with mocked environment."""
    # mock_env_vars is used via pytest fixture dependency to ensure env is mocked
    _ = mock_env_vars  # Mark as used
    from app.core.agents.base import get_agent
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_agent.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()
    get_agent.cache_clear()


@pytest.fixture
def mock_anthropic_response() -> dict[str, Any]:
    """Provide a mock Anthropic API response for testing."""
    return {
        "content": [{"type": "text", "text": "Hello! I'm Jasque."}],
        "model": "claude-sonnet-4-5",
        "usage": {"input_tokens": 10, "output_tokens": 15},
    }
