"""Pytest fixtures for AgentGuard tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers():
    """Get authentication headers for tests."""
    # TODO: Implement actual auth token generation
    return {"Authorization": "Bearer test-token"}
