"""Tests for base agent module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.agents.base import (
    SYSTEM_PROMPT,
    _get_api_key_for_provider,
    _get_provider_from_model,
    create_agent,
    get_agent,
)
from app.core.agents.types import AgentDependencies
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def mock_environment():
    """Set up test environment."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "LLM_MODEL": "anthropic:claude-sonnet-4-5",
    }
    with patch.dict(os.environ, env_vars):
        from app.core.agents.base import get_agent
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
        # Verify model string is passed as first argument
        assert mock_agent_class.call_args[0][0] == "anthropic:claude-sonnet-4-5"


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


# Tests for _get_provider_from_model helper


def test_get_provider_from_model_anthropic():
    """Test extracting anthropic provider."""
    assert _get_provider_from_model("anthropic:claude-sonnet-4-5") == "anthropic"


def test_get_provider_from_model_google():
    """Test extracting google-gla provider."""
    assert _get_provider_from_model("google-gla:gemini-2.5-pro") == "google-gla"


def test_get_provider_from_model_openai():
    """Test extracting openai provider."""
    assert _get_provider_from_model("openai:gpt-4o") == "openai"


def test_get_provider_from_model_invalid_format():
    """Test that invalid model format raises clear error."""
    with pytest.raises(ValueError, match="Invalid model format"):
        _get_provider_from_model("invalid-no-colon")


def test_get_provider_from_model_empty_string():
    """Test that empty string raises clear error."""
    with pytest.raises(ValueError, match="Invalid model format"):
        _get_provider_from_model("")


# Tests for _get_api_key_for_provider helper


def test_get_api_key_for_provider_anthropic():
    """Test getting API key for anthropic provider."""
    settings = get_settings()
    env_var, api_key = _get_api_key_for_provider("anthropic", settings)
    assert env_var == "ANTHROPIC_API_KEY"
    assert api_key == "sk-ant-test-key"


def test_get_api_key_for_provider_unsupported():
    """Test that unsupported provider raises clear error."""
    settings = get_settings()
    with pytest.raises(ValueError, match="Unsupported provider: 'unsupported'"):
        _get_api_key_for_provider("unsupported", settings)


def test_get_api_key_for_provider_missing_key():
    """Test that missing API key raises clear error."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "LLM_MODEL": "google-gla:gemini-2.5-pro",
        # Note: GOOGLE_API_KEY not set
    }
    with patch.dict(os.environ, env_vars, clear=True):
        get_settings.cache_clear()
        settings = get_settings()
        with pytest.raises(ValueError, match="API key not configured for provider 'google-gla'"):
            _get_api_key_for_provider("google-gla", settings)


# Tests for create_agent with multiple providers


def test_create_agent_invalid_model_format():
    """Test that invalid model format raises clear error."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "LLM_MODEL": "invalid-no-colon",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="Invalid model format"):
            create_agent()


def test_create_agent_missing_api_key():
    """Test that missing API key raises clear error."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "LLM_MODEL": "google-gla:gemini-2.5-pro",
        # Note: GOOGLE_API_KEY not set
    }
    with patch.dict(os.environ, env_vars, clear=True):
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="API key not configured"):
            create_agent()


def test_create_agent_unsupported_provider():
    """Test that unsupported provider raises clear error."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "LLM_MODEL": "unsupported:some-model",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="Unsupported provider"):
            create_agent()
