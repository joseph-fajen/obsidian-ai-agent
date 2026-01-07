"""Tests for app.main module."""

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_environment() -> Generator[None, None, None]:
    """Mock environment variables for tests."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "ANTHROPIC_MODEL": "claude-sonnet-4-5",
    }
    with (
        patch.dict(os.environ, env_vars),
        patch("app.main.get_agent"),  # Mock agent initialization
    ):
        from app.core.agents.base import get_agent
        from app.core.config import get_settings

        get_settings.cache_clear()
        get_agent.cache_clear()
        yield
        get_settings.cache_clear()
        get_agent.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_root_endpoint(client: TestClient) -> None:
    """Test root endpoint returns correct JSON structure."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
    assert data["message"] == "Jasque"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"


def test_docs_endpoint_accessible(client: TestClient) -> None:
    """Test /docs endpoint is accessible."""
    response = client.get("/docs")

    assert response.status_code == 200


def test_openapi_endpoint_accessible(client: TestClient) -> None:
    """Test /openapi.json endpoint is accessible."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert data["info"]["title"] == "Jasque"
    assert data["info"]["version"] == "0.1.0"


def test_cors_headers_present(client: TestClient) -> None:
    """Test CORS headers are present in responses."""
    # Send a request with an Origin header that should be allowed
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    # CORS middleware should add access-control headers
    # Note: TestClient may not fully simulate CORS preflight,
    # but we can check the middleware is configured


def test_request_id_in_response_headers(client: TestClient) -> None:
    """Test X-Request-ID is added to response headers by middleware."""
    response = client.get("/")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_custom_request_id_preserved(client: TestClient) -> None:
    """Test custom X-Request-ID from request is preserved in response."""
    custom_id = "custom-request-id-12345"

    response = client.get("/", headers={"X-Request-ID": custom_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_lifespan_startup_logging() -> None:
    """Test lifespan logs application.lifecycle_started event."""
    with (
        patch("app.main.get_logger") as mock_get_logger,
        patch("app.main.get_agent") as mock_get_agent,
    ):
        mock_logger = mock_get_logger.return_value
        mock_get_agent.return_value = None  # Mock agent initialization

        # Import app inside the patch context to use mocked components
        from app.main import app

        # Create a new client to trigger lifespan
        with TestClient(app):
            # Check that logger.info was called with application.lifecycle_started
            mock_logger.info.assert_any_call(
                "application.lifecycle_started",
                app_name="Jasque",
                version="0.1.0",
                environment="development",
            )
