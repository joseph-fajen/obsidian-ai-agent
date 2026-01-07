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
        "ANTHROPIC_MODEL": "claude-sonnet-4-5",
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
