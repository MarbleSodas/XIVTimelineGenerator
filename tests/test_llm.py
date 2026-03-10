"""Tests for the LLM provider configuration."""

import os
from unittest.mock import patch

from xiv_timeline.llm import get_llm, configure_langsmith


def test_get_llm_returns_instance():
    """get_llm() should return a ChatOpenAI instance."""
    with patch.dict(os.environ, {
        "MINIMAX_API_KEY": "test-key",
        "MINIMAX_BASE_URL": "https://api.minimax.chat/v1",
        "MINIMAX_MODEL": "MiniMax-M2.5",
    }):
        llm = get_llm()
        assert llm is not None
        assert llm.model_name == "MiniMax-M2.5"


def test_get_llm_custom_env():
    """get_llm() should respect custom environment variables."""
    with patch.dict(os.environ, {
        "MINIMAX_API_KEY": "custom-key",
        "MINIMAX_BASE_URL": "https://custom.endpoint.com/v1",
        "MINIMAX_MODEL": "CustomModel",
    }):
        llm = get_llm()
        assert llm.model_name == "CustomModel"


def test_get_llm_defaults():
    """get_llm() should use defaults when env vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        llm = get_llm()
        assert llm.model_name == "MiniMax-M2.5"


def test_configure_langsmith_no_key():
    """configure_langsmith() should be a no-op without API key."""
    with patch.dict(os.environ, {}, clear=True):
        configure_langsmith()
        assert os.environ.get("LANGSMITH_TRACING") is None


def test_configure_langsmith_with_key():
    """configure_langsmith() should set tracing env vars when API key is present."""
    with patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"}, clear=True):
        configure_langsmith()
        assert os.environ.get("LANGSMITH_TRACING") == "true"
        assert os.environ.get("LANGSMITH_PROJECT") == "xiv-timeline-generator"


def test_configure_langsmith_custom_project():
    """configure_langsmith() should respect existing project name."""
    with patch.dict(os.environ, {
        "LANGSMITH_API_KEY": "test-key",
        "LANGSMITH_PROJECT": "my-custom-project",
    }, clear=True):
        configure_langsmith()
        assert os.environ.get("LANGSMITH_PROJECT") == "my-custom-project"
