"""LLM provider configuration for XIV Timeline Generator.

Configures ChatOpenAI to use MiniMax M2.5 via OpenAI-compatible API.
Optionally enables LangSmith tracing for full observability.
"""

import logging
import os

from langchain_openai import ChatOpenAI

logger = logging.getLogger("xiv_timeline.llm")


def configure_langsmith() -> None:
    """
    Enable LangSmith tracing if LANGSMITH_API_KEY is present.

    Set these environment variables to activate:
    - LANGSMITH_API_KEY: Your LangSmith API key
    - LANGSMITH_PROJECT: Project name (default: xiv-timeline-generator)
    - LANGSMITH_TRACING: Set to "true" to enable (auto-enabled if API key is set)

    When enabled, all LangGraph node executions, LLM calls, and state
    transitions are automatically traced and viewable at https://smith.langchain.com.
    """
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        logger.debug("LangSmith tracing disabled (no LANGSMITH_API_KEY set)")
        return

    # LangSmith auto-traces when these env vars are set
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "xiv-timeline-generator")

    project = os.environ["LANGSMITH_PROJECT"]
    logger.info("LangSmith tracing enabled — project=%s", project)


def get_llm() -> ChatOpenAI:
    """
    Create the LLM instance configured for MiniMax M2.5.

    Reads from environment variables:
    - MINIMAX_API_KEY: Your Minimax API key
    - MINIMAX_BASE_URL: Custom endpoint (default: https://api.minimax.io/v1)
    - MINIMAX_MODEL: Model name (default: MiniMax-M2.5)

    Returns:
        Configured ChatOpenAI instance pointing to MiniMax.
    """
    api_key = os.getenv("MINIMAX_API_KEY", "your-api-key-here")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    model_name = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

    logger.debug("Creating LLM — model=%s, base_url=%s", model_name, base_url)

    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        timeout=180.0,
        max_retries=3,
    )
