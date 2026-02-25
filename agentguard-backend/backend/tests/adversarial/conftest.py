"""Shared fixtures for adversarial detector tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def default_config() -> dict[str, object]:
    """Default detector config with LLM verification disabled.

    We disable LLM verify so tests exercise the real pattern-matching logic
    without needing to mock external LLM calls.
    """
    return {"llm_verify": False}


@pytest.fixture
def config_with_llm() -> dict[str, object]:
    """Config with LLM verification enabled (requires mocking call_llm)."""
    return {"llm_verify": True}
