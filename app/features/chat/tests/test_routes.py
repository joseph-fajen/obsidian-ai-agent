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
    # Mock the response object with model_name
    mock_response = MagicMock()
    mock_response.model_name = "claude-sonnet-4-5"
    mock_result.response = mock_response
    # Mock usage with updated field names
    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 15
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
